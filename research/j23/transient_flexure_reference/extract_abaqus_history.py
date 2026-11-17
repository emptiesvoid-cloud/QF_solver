"""Extract probe displacement and clamp reactions using Abaqus's odbAccess.

Kept compatible with the older Python runtimes commonly bundled with Abaqus.
Run with: abaqus python extract_abaqus_history.py job.odb abaqus_history.csv
"""

from __future__ import print_function

import csv
import sys

from odbAccess import openOdb


def _one_node_value(field, region, node_label, component):
    values = field.getSubset(region=region).values
    matches = [value for value in values if value.nodeLabel == node_label]
    if len(matches) != 1:
        raise RuntimeError("expected one field value for node %d, found %d" % (node_label, len(matches)))
    data = matches[0].data
    return float(data[component])


def _single_node_label(node_set, set_name):
    labels = []
    for entry in node_set.nodes:
        if hasattr(entry, "label"):
            labels.append(entry.label)
        else:
            labels.extend(node.label for node in entry)
    if len(labels) != 1:
        raise RuntimeError("expected one node in %s, found %d" % (set_name, len(labels)))
    return labels[0]


def extract(odb_path, csv_path):
    odb = openOdb(path=odb_path, readOnly=True)
    try:
        if "TRANSIENT" not in odb.steps:
            raise RuntimeError("ODB does not contain the TRANSIENT step")
        assembly = odb.rootAssembly
        instance = assembly.instances["BEAM-1"]
        midspan_nodes = assembly.nodeSets["MIDSPAN_PROBE"]
        tip_nodes = assembly.nodeSets["TIP_PROBE"]
        fixed_nodes = assembly.nodeSets["FIXED_NODES"]
        step = odb.steps["TRANSIENT"]
        coordinates = dict((node.label, node.coordinates) for node in instance.nodes)

        rows = []
        for frame_index, frame in enumerate(step.frames):
            time_s = float(frame.frameValue)
            if time_s <= 0.0:
                continue
            if "U" not in frame.fieldOutputs or "RF" not in frame.fieldOutputs:
                raise RuntimeError("frame %d is missing U or RF field output" % frame_index)
            u_field = frame.fieldOutputs["U"]
            rf_field = frame.fieldOutputs["RF"]
            midspan_label = _single_node_label(midspan_nodes, "MIDSPAN_PROBE")
            tip_label = _single_node_label(tip_nodes, "TIP_PROBE")
            midspan_uz = _one_node_value(u_field, midspan_nodes, midspan_label, 2)
            tip_uz = _one_node_value(u_field, tip_nodes, tip_label, 2)

            reaction_force = [0.0, 0.0, 0.0]
            reaction_moment = [0.0, 0.0, 0.0]
            for value in rf_field.getSubset(region=fixed_nodes).values:
                force = [float(value.data[i]) for i in range(3)]
                position = coordinates[value.nodeLabel]
                moment = (
                    position[1] * force[2] - position[2] * force[1],
                    position[2] * force[0] - position[0] * force[2],
                    position[0] * force[1] - position[1] * force[0],
                )
                for axis in range(3):
                    reaction_force[axis] += force[axis]
                    reaction_moment[axis] += moment[axis]
            rows.append((time_s, midspan_uz, tip_uz) + tuple(reaction_force) + tuple(reaction_moment))

        if not rows:
            raise RuntimeError("ODB contains no positive-time field frames")
        if sys.version_info[0] < 3:
            stream = open(csv_path, "wb")
        else:
            stream = open(csv_path, "w", newline="")
        try:
            writer = csv.writer(stream)
            writer.writerow(("time_s", "midspan_uz_m", "tip_uz_m", "reaction_fx_n", "reaction_fy_n", "reaction_fz_n", "reaction_mx_nm", "reaction_my_nm", "reaction_mz_nm"))
            for row in rows:
                writer.writerow(["%.17g" % value for value in row])
        finally:
            stream.close()
        return len(rows)
    finally:
        odb.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: abaqus python extract_abaqus_history.py job.odb abaqus_history.csv")
    count = extract(sys.argv[1], sys.argv[2])
    print("wrote %d positive-time frames to %s" % (count, sys.argv[2]))
