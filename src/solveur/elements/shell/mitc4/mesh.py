"""Mesh generation helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class QuadMesh:
    nodes: np.ndarray
    quads: np.ndarray


class MeshFactory:
    """Small deterministic meshes used by benchmarks and verification tests."""

    @staticmethod
    def scordelis_lo(nx: int, ny: int) -> QuadMesh:
        R = 25.0
        L = 50.0
        angle = math.radians(80.0)
        nodes = []
        for i in range(nx + 1):
            x = i * L / nx
            for j in range(ny + 1):
                theta = -0.5 * angle + j * angle / ny
                nodes.append([x, R * math.sin(theta), R * math.cos(theta)])

        quads = []
        for i in range(nx):
            for j in range(ny):
                n0 = i * (ny + 1) + j
                n1 = (i + 1) * (ny + 1) + j
                quads.append([n0, n1, n1 + 1, n0 + 1])
        return QuadMesh(np.asarray(nodes, dtype=float), np.asarray(quads, dtype=int))

    @staticmethod
    def rectangular_plate(nx: int, ny: int, length: float, width: float) -> QuadMesh:
        xs = np.linspace(0.0, length, nx + 1)
        ys = np.linspace(-0.5 * width, 0.5 * width, ny + 1)
        nodes = np.array([[x, y, 0.0] for x in xs for y in ys], dtype=float)
        quads = []
        for i in range(nx):
            for j in range(ny):
                n0 = i * (ny + 1) + j
                n1 = (i + 1) * (ny + 1) + j
                quads.append([n0, n1, n1 + 1, n0 + 1])
        return QuadMesh(nodes, np.asarray(quads, dtype=int))

    @staticmethod
    def distorted_patch_2x2() -> QuadMesh:
        nodes = np.array(
            [
                [0.0, 0.0, 0.0],
                [0.48, -0.03, 0.0],
                [1.0, 0.0, 0.0],
                [-0.03, 0.55, 0.0],
                [0.52, 0.50, 0.0],
                [1.05, 0.48, 0.0],
                [0.02, 1.0, 0.0],
                [0.49, 1.04, 0.0],
                [1.0, 1.0, 0.0],
            ],
            dtype=float,
        )
        quads = np.array([[0, 1, 4, 3], [1, 2, 5, 4], [3, 4, 7, 6], [4, 5, 8, 7]], dtype=int)
        return QuadMesh(nodes, quads)

