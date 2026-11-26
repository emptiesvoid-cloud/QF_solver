"""Supervise a supplemental exact residual check in a spawned process."""
import hashlib
import math
import multiprocessing as mp
import time

import numpy as np
try:
    import psutil
except ImportError:
    psutil = None
from scipy.sparse import csr_matrix

from solveur.experimental.eas_residual.exact_residual import exact_check
from solveur.core.errors import NumericalConvergenceError
from solveur.core.solvers.linear import LinearSystemSolver


def identity(arrays, shape, threshold):
    h = hashlib.sha256()
    h.update(repr((tuple(shape), float(threshold).hex())).encode("ascii"))
    for a in arrays:
        a = np.asarray(a)
        h.update(repr((a.dtype.str, a.shape)).encode("ascii"))
        h.update(np.ascontiguousarray(a).tobytes())
    return h.hexdigest()


def _worker(pipe, arrays, shape, threshold, request_id):
    try:
        if identity(arrays, shape, threshold) != request_id:
            raise ValueError("identity mismatch")
        result = exact_check(*arrays[:3], shape, arrays[3], arrays[4], threshold, max_nnz=100000)
        pipe.send({"identity": request_id, "decision": result["decision"]})
    except Exception:
        pipe.send({"identity": request_id, "decision": "INCONCLUSIVE"})
    finally:
        pipe.close()


def _verified_message(message, request_id):
    if not isinstance(message, dict) or set(message) != {"identity", "decision"}:
        return "INCONCLUSIVE"
    identity_value, decision = message["identity"], message["decision"]
    if (type(identity_value) is not str or identity_value != request_id
            or type(decision) is not str or decision not in {"PASS", "FAIL"}):
        return "INCONCLUSIVE"
    return decision


def supervise(data, indices, indptr, shape, rhs, candidate, threshold,
              *, timeout=10.0, rss_limit=256 * 2**20, input_limit=8 * 2**20):
    """A sampled RSS limit and watchdog bound a single child; never modify the guard."""
    result = {"historical_decision": "NOT_RUN", "supplemental": "INCONCLUSIVE"}
    if psutil is None:
        return {**result, "reason": "PSUTIL_UNAVAILABLE"}
    try:
        inputs = (data, indices, indptr, rhs, candidate)
        if not all(isinstance(a, np.ndarray) for a in inputs):
            return {**result, "reason": "INVALID_ARRAY_TYPE"}
        if (type(input_limit) is not int or input_limit <= 0
                or type(rss_limit) is not int or rss_limit <= 0
                or type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0
                or sum(a.nbytes for a in inputs) > input_limit):
            return {**result, "reason": "INVALID_LIMIT_OR_INPUT_SIZE"}
        arrays = tuple(a.copy() for a in inputs)
        if threshold != 1e-7 or not isinstance(threshold, float):
            return {**result, "reason": "INVALID_THRESHOLD"}
        d, ix, ptr, b, x = arrays
        if (len(shape) != 2 or shape[0] != shape[1] or shape[0] < 1 or
            d.dtype != np.float64 or b.dtype != np.float64 or x.dtype != np.float64 or
            ix.dtype.kind not in "iu" or ptr.dtype.kind not in "iu" or
            d.ndim != 1 or ix.shape != d.shape or ptr.shape != (shape[0]+1,) or
            b.shape != (shape[0],) or x.shape != (shape[0],) or
            ptr[0] != 0 or ptr[-1] != d.size or np.any(ptr[1:] < ptr[:-1]) or
            np.any(ix < 0) or np.any(ix >= shape[0]) or
            not all(np.all(np.isfinite(v)) for v in (d, b, x))):
            return {**result, "reason": "INVALID_SYSTEM"}
        for row in range(shape[0]):
            indices_row = ix[ptr[row]:ptr[row+1]]
            if np.any(indices_row[1:] <= indices_row[:-1]):
                return {**result, "reason": "INVALID_CSR"}
        request_id = identity(arrays, shape, threshold)
        matrix = csr_matrix((d, ix, ptr), shape=shape, copy=True)
        try:
            LinearSystemSolver._validated_residual_metrics(matrix, b, x, "direct", {"residual_failure_tolerance": threshold})
            result["historical_decision"] = "ACCEPTED"
        except NumericalConvergenceError:
            result["historical_decision"] = "REJECTED"
        if identity(arrays, shape, threshold) != request_id:
            return {**result, "reason": "INPUT_MUTATED_DURING_GUARD"}
        message, monitor = _spawn_monitored(_worker, (arrays, shape, threshold, request_id), timeout, rss_limit)
        verified = _verified_message(message, request_id)
        if verified != "INCONCLUSIVE":
            result["supplemental"] = verified
            monitor["reason"] = "COMPLETE"
        return {**result, **monitor, "identity": request_id}
    except (OSError, ValueError, TypeError, EOFError, OverflowError, psutil.Error, KeyboardInterrupt):
        return {**result, "reason": "SUPERVISOR_ERROR_OR_INTERRUPTED"}


def _spawn_monitored(target, args, timeout, rss_limit):
    """Run one trusted worker with a small pipe reply and sampled RSS."""
    if psutil is None:
        return None, {"reason": "PSUTIL_UNAVAILABLE"}
    process = parent = child = None
    try:
        ctx = mp.get_context("spawn")
        parent, child = ctx.Pipe(duplex=False)
        process = ctx.Process(target=target, args=(child, *args))
        started = time.monotonic()
        process.start()
        child.close()
        peak = 0
        reason = "CHILD_EXIT"
        while process.is_alive():
            if time.monotonic() - started >= timeout:
                reason = "TIMEOUT"
                break
            try:
                peak = max(peak, psutil.Process(process.pid).memory_info().rss)
            except psutil.NoSuchProcess:
                process.join(0.1)
                reason = "CHILD_EXIT" if not process.is_alive() else "MONITOR_ERROR"
                break
            except psutil.Error:
                reason = "MONITOR_ERROR"
                break
            if peak > rss_limit:
                reason = "SAMPLED_RSS_LIMIT"
                break
            time.sleep(0.01)
        if process.is_alive():
            process.terminate()
        process.join(2.0)
        if process.is_alive():
            process.kill()
            process.join(2.0)
        if reason == "CHILD_EXIT" and time.monotonic() - started >= timeout:
            reason = "TIMEOUT"
        message = None
        if reason == "CHILD_EXIT" and process.exitcode == 0 and parent.poll():
            message = parent.recv()
        return message, {"reason": reason, "seconds": time.monotonic()-started,
                         "sampled_peak_rss_bytes": peak, "child_exitcode": process.exitcode}
    except (OSError, ValueError, TypeError, EOFError, OverflowError, psutil.Error, KeyboardInterrupt):
        if process is not None and process.pid is not None:
            if process.is_alive():
                process.terminate()
            process.join(2.0)
            if process.is_alive():
                process.kill()
                process.join(2.0)
        return None, {"reason": "SUPERVISOR_ERROR_OR_INTERRUPTED"}
    finally:
        if child is not None:
            child.close()
        if parent is not None:
            parent.close()
