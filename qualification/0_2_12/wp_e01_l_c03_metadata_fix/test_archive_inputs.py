"""Offline algebra and provenance tests for archive_inputs.py; no solver imports."""
from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest

from archive_inputs import (
    HEX_SIGNS, coefficient_intervals, grad_u, gradients, iadd, imul, iv,
    canonical_state, q, rat, safe_inventory, sha256, small_strain, sqrt_interval,
)


def _disp(nodes, M, t):
    values = [0.0] * (3 * len(nodes))
    for n, xyz in enumerate(nodes):
        for i in range(3):
            values[3*n+i] = float(t[i] + sum(M[i][j] * q(xyz[j]) for j in range(3)))
    return values


class ArchiveInputTests(unittest.TestCase):
  def assert_interval_contains(self, actual, expected: Fraction):
    self.assertLessEqual(actual[0], expected)
    self.assertLessEqual(expected, actual[1])


  def test_interval_accumulation_is_addition_not_tuple_concatenation(self):
    a = iv(Fraction(1, 3), Fraction(2, 3))
    b = iv(Fraction(1, 5), Fraction(1, 2))
    result = iadd(imul(a, b), imul(a, b))
    self.assertEqual(result, (Fraction(2, 15), Fraction(2, 3)))


  def test_tet4_affine_displacement_recovers_symmetric_gradient_and_geometry(self):
    nodes = [[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]
    M = [[Fraction(2),Fraction(3),Fraction(-1)],
         [Fraction(5),Fraction(-2),Fraction(4)],
         [Fraction(7),Fraction(8),Fraction(6)]]
    t = [Fraction(11),Fraction(-13),Fraction(17)]
    u = _disp(nodes,M,t)
    g=gradients([0,1,2,3],nodes,"TET4")
    gu=grad_u([0,1,2,3],g,u)
    for i in range(3):
        for j in range(3): self.assert_interval_contains(gu[i][j],M[i][j])
    strain=small_strain([0,1,2,3],g,u)
    for i in range(3):
        for j in range(3):
            self.assert_interval_contains(strain[i][j],(M[i][j]+M[j][i])/2)
    # For this unit tetrahedron the exact shape gradients are N0=(-1,-1,-1),
    # N1=(1,0,0), N2=(0,1,0), N3=(0,0,1), and det(J)=1.
    self.assertEqual([[entry[0] for entry in row] for row in g], [
        [Fraction(-1)]*3,[Fraction(1),Fraction(0),Fraction(0)],
        [Fraction(0),Fraction(1),Fraction(0)],[Fraction(0),Fraction(0),Fraction(1)]])


  def test_hex8_affine_displacement_recovers_strain_at_all_reference_points(self):
    xyz=[(0.,0.,0.),(.5,0.,0.),(.5,.5,0.),(0.,.5,0.),
         (0.,0.,.5),(.5,0.,.5),(.5,.5,.5),(0.,.5,.5)]
    nodes=[list(p) for p in xyz]
    M=[[Fraction(2),Fraction(3),Fraction(-1)],
       [Fraction(5),Fraction(-2),Fraction(4)],
       [Fraction(7),Fraction(8),Fraction(6)]]
    u=_disp(nodes,M,[Fraction(1),Fraction(2),Fraction(3)])
    # The historical oracle uses product((-1,1), repeat=3): last axis varies fastest.
    points=[(x,y,z) for x in (-1,1) for y in (-1,1) for z in (-1,1)]
    self.assertEqual(points[1], (-1,-1,1))
    self.assertEqual(points[4], (1,-1,-1))
    self.assertEqual(HEX_SIGNS, ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                         (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))
    )
    for signs in points:
        g=gradients(list(range(8)),nodes,"HEX8",signs)
        gu=grad_u(list(range(8)),g,u)
        for i in range(3):
            for j in range(3): self.assert_interval_contains(gu[i][j],M[i][j])
        strain=small_strain(list(range(8)),g,u)
        for i in range(3):
            for j in range(3): self.assert_interval_contains(strain[i][j],(M[i][j]+M[j][i])/2)


  def test_exact_binary64_roundtrip_and_certified_sqrt_interval(self):
    x=0.1
    encoded=json.dumps({"x":x},separators=(",",":"),allow_nan=False)
    decoded=json.loads(encoded)["x"]
    self.assertEqual(q(decoded),q(x))
    root=sqrt_interval(Fraction(1,3))
    self.assertLessEqual(root[0]*root[0], Fraction(1,3))
    self.assertLessEqual(Fraction(1,3), root[1]*root[1])


  def test_digest_canonicalization_restores_integer_map_keys_and_float_hex(self):
    state={"0":[{"elastic":False,"x":0.1}],"1":[]}
    canonical=canonical_state(state)
    entries=canonical["entries"]
    self.assertEqual(entries[0][0],{"type":"int","value":"0"})
    self.assertEqual(entries[0][1],{"type":"list","items":[{"type":"mapping","entries":[
        ({"type":"str","value":"elastic"},{"type":"bool","value":False}),
        ({"type":"str","value":"x"},{"type":"float","value":float(0.1).hex()}),
    ]}]})


  def test_inventory_rejects_tampered_archive_file(self):
    with tempfile.TemporaryDirectory() as temporary:
      tmp_path = Path(temporary)
      self._assert_tampered_archive(tmp_path)

  def _assert_tampered_archive(self, tmp_path: Path):
    payload=tmp_path/"raw.json"
    payload.write_text('{"frozen":1}\n',encoding="utf-8")
    expected=hashlib.sha256(payload.read_bytes()).hexdigest()
    manifest={"file_count_excluding_this_manifest":1,"files_excluding_this_manifest":[
        {"path":"raw.json","size_bytes":payload.stat().st_size,"sha256":expected}]}
    (tmp_path/"archive_integrity.json").write_text(json.dumps(manifest),encoding="utf-8")
    self.assertEqual(safe_inventory(tmp_path,"archive_integrity.json"),{"raw.json":expected})
    payload.write_text('{"frozen":2}\n',encoding="utf-8")
    with self.assertRaisesRegex(ValueError,"archive hash mismatch"):
        safe_inventory(tmp_path,"archive_integrity.json")


  def test_coefficient_intervals_keep_nonnegative_quadratic_terms(self):
    base=[iv(Fraction(2)),iv(Fraction(-2))]
    direction=[iv(Fraction(3)),iv(Fraction(3))]
    A,B,C=coefficient_intervals(base,direction)
    self.assertEqual(A,(Fraction(12),Fraction(12)))
    self.assertEqual(B,(Fraction(0),Fraction(0)))
    self.assertEqual(C,(Fraction(27),Fraction(27)))


if __name__ == "__main__":
    unittest.main()
