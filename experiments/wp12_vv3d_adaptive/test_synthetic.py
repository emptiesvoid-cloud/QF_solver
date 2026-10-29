"""Synthetic geometry and analytic-oracle checks; no FEM execution."""
import hashlib
import json
import math
import tempfile
import unittest
from collections import Counter
from itertools import combinations, product
from pathlib import Path

from experiments.wp12_vv3d_adaptive import (
    basis, budget, evidence, field_error_draft, load_assembly_draft, mesh, metrics, model_draft,
    oracle, prepare, quadrature, quality, sampling,
)


class MeshContracts(unittest.TestCase):
    def test_observables_writer_is_create_only_on_fabricated_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/"evidence"
            payload = {"schema":"qf-wp12-vv3d-observables-v1","case_id":"SYNTHETIC-CASE",
                "attempt_id":"SYNTHETIC-ATTEMPT","mesh_sha256":"a"*64,"scientific_fingerprint":"b"*64,
                "controller_fingerprint":"c"*64,"manifest_sha256":"d"*64,
                "observables":{"example":{"value":1.0,"unit":"m"},"missing":{"status":"NOT_EXPOSED"}},
                "criteria":{"example":"NOT_ASSESSED"}}
            receipt=evidence.write_observables(root,"SYNTHETIC-CASE","SYNTHETIC-ATTEMPT",payload)
            path=Path(receipt["path"])
            saved=path.read_bytes()
            self.assertEqual(receipt["sha256"],hashlib.sha256(saved).hexdigest())
            with self.assertRaises(FileExistsError):
                evidence.write_observables(root,"SYNTHETIC-CASE","SYNTHETIC-ATTEMPT",payload)
            self.assertEqual(path.read_bytes(),saved)
            with self.assertRaises(ValueError):
                evidence.write_observables(root,"../unsafe","SYNTHETIC-ATTEMPT",payload)
            payload["observables"]["example"]["value"] = float("nan")
            payload["attempt_id"]="SYNTHETIC-NAN"
            with self.assertRaises(ValueError):
                evidence.write_observables(root,"SYNTHETIC-CASE","SYNTHETIC-NAN",payload)
            self.assertFalse((root/"SYNTHETIC-CASE"/"SYNTHETIC-NAN").exists())

    def test_load_assembly_public_entry_refuses_without_authorization(self):
        with self.assertRaisesRegex(PermissionError, "validated controller permit"):
            load_assembly_draft.assemble_body_load({}, order=8)

    def test_model_templates_remain_explicitly_non_executable(self):
        for family in mesh.FORMULATIONS:
            prepared = mesh.generate(family,2)
            wrapper = model_draft.build_template(prepared)
            self.assertFalse(wrapper["executable"])
            model = wrapper["model_template"]
            self.assertIsNone(model["loads"])
            self.assertEqual(len(model["nodes"]),prepared["summary"]["nodes"])
            self.assertEqual(len(model["elements"]),prepared["summary"]["elements"])
            self.assertEqual(3*len(model["fixed_dofs"]),prepared["summary"]["fixed_dofs"])
            self.assertEqual({item["type"] for item in model["elements"]},{family})
        with self.assertRaises(ValueError):
            model_draft.build_template({"schema":"unexpected"})

    def test_budget_arithmetic_is_conservative_and_does_not_reserve(self):
        budget.check_plan(budget.BudgetSnapshot(23,27600), timeout_seconds=1200, rss_mib=4096, dofs=30000)
        for snap,kwargs in (
            (budget.BudgetSnapshot(24,0), {"timeout_seconds":1,"rss_mib":1,"dofs":1}),
            (budget.BudgetSnapshot(0,27601), {"timeout_seconds":1200,"rss_mib":1,"dofs":1}),
            (budget.BudgetSnapshot(0,0), {"timeout_seconds":1201,"rss_mib":1,"dofs":1}),
            (budget.BudgetSnapshot(0,0), {"timeout_seconds":1,"rss_mib":4097,"dofs":1}),
            (budget.BudgetSnapshot(0,0), {"timeout_seconds":1,"rss_mib":1,"dofs":30001}),
            (budget.BudgetSnapshot(0,float("nan")), {"timeout_seconds":1,"rss_mib":1,"dofs":1}),
        ):
            with self.assertRaises(ValueError):
                budget.check_plan(snap, **kwargs)

    def test_all_12_shapes_budget_and_affine_geometry(self):
        expected = {"TET4": (48, 27), "TET10": (48, 125), "HEX8": (8, 27), "HEX20": (8, 81)}
        for family in mesh.FORMULATIONS:
            for n in mesh.LEVELS:
                with self.subTest(family=family, n=n):
                    m = mesh.generate(family, n)
                    info = m["summary"]
                    self.assertLessEqual(info["dofs"], 30000)
                    self.assertGreater(info["free_dofs"], 0)
                    self.assertGreater(info["affine_jacobian_min_m3"], 0)
                    quality_result = quality.assess(m)
                    self.assertGreater(quality_result["quality_min"],0)
                    self.assertLessEqual(quality_result["quality_max"],1.0+1e-12)
                    self.assertAlmostEqual(quality_result["jacobian_det_min_m3"],info["affine_jacobian_min_m3"])
                    self.assertEqual(info["dofs"], info["fixed_dofs"] + info["free_dofs"])
                    if n == 2:
                        self.assertEqual((info["elements"], info["nodes"]), expected[family])
                    for cell in m["connectivity_zero_based"]:
                        self.assertEqual(len(cell), len(set(cell)))
                        self.assertEqual(len(cell), {"TET4":4,"TET10":10,"HEX8":8,"HEX20":20}[family])
                        corners = cell[:4 if family.startswith("TET") else 8]
                        if family.startswith("TET"):
                            points = [m["nodes_integer"][i] for i in corners]
                            self.assertGreater(mesh._det(*points), 0)
                        if family in ("TET10", "HEX20"):
                            edges = mesh.TET_EDGES if family == "TET10" else mesh.HEX_EDGES
                            for idx,(a,b) in enumerate(edges):
                                pa,pb = m["nodes_integer"][corners[a]],m["nodes_integer"][corners[b]]
                                self.assertEqual(m["nodes_integer"][cell[len(corners)+idx]],
                                                 tuple((pa[q]+pb[q])//2 for q in range(3)))

    def test_tetra_faces_are_conforming_on_small_mesh(self):
        m = mesh.generate("TET10", 2)
        faces = Counter(tuple(sorted(face)) for cell in m["connectivity_zero_based"]
                        for face in combinations(cell[:4], 3))
        self.assertEqual(set(faces.values()), {1,2})
        self.assertEqual(sum(count == 1 for count in faces.values()), 12*2**2)

    def test_quadratic_warp_is_not_mislabeled_affine(self):
        for family in ("TET10","HEX20"):
            prepared = mesh.generate(family,2)
            corner_count = 4 if family == "TET10" else 8
            node = prepared["connectivity_zero_based"][0][corner_count]
            prepared["nodes_integer"][node] = tuple(x+1 for x in prepared["nodes_integer"][node])
            with self.assertRaisesRegex(ValueError,"not affine"):
                quality.assess(prepared)

    def test_outputs_are_hash_bound_and_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)/"prepared"
            cases = prepare.prepare(dest)
            self.assertEqual(len(cases), 12)
            for case in cases:
                self.assertEqual(hashlib.sha256((dest/case["mesh_file"]).read_bytes()).hexdigest(), case["mesh_sha256"])
                self.assertFalse(case["execution_authorized"])
                self.assertTrue(case["do_not_execute"])
                self.assertIsNone(case["nodeid"])
            snapshot = (dest/"MATRIX_NOT_AUTHORIZED.json").read_bytes()
            with self.assertRaises(FileExistsError):
                prepare.prepare(dest)
            self.assertEqual((dest/"MATRIX_NOT_AUTHORIZED.json").read_bytes(),snapshot)
            self.assertEqual(len(json.loads(snapshot)["cases"]),12)

    def test_checked_in_meshes_reproduce_byte_for_byte(self):
        directory = Path(__file__).parent/"prepared_20261029"
        matrix = json.loads((directory/"MATRIX_NOT_AUTHORIZED.json").read_bytes())
        for case in matrix["cases"]:
            raw = (directory/case["mesh_file"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),case["mesh_sha256"])
            self.assertEqual(raw,prepare.encode(mesh.generate(case["formulation"],case["divisions"][0])))

    def test_geometry_report_matches_prepared_meshes(self):
        directory = Path(__file__).parent/"prepared_20261029"
        raw = (directory/"MATRIX_NOT_AUTHORIZED.json").read_bytes()
        matrix = json.loads(raw)
        report = json.loads((Path(__file__).parent/"MESH_QUALITY_REPORT.json").read_bytes())
        self.assertEqual(report["matrix_sha256"],hashlib.sha256(raw).hexdigest())
        self.assertEqual(len(report["results"]),12)
        for case,row in zip(matrix["cases"],report["results"]):
            self.assertEqual(case["case_id"],row["case_id"])
            self.assertEqual(case["mesh_sha256"],row["mesh_sha256"])
            self.assertEqual(quality.assess(json.loads((directory/case["mesh_file"]).read_bytes())),
                             {k:v for k,v in row.items() if k not in {"case_id","mesh_sha256"}})

    def test_adaptive_meshes_are_bounded_and_reproducible(self):
        directory=Path(__file__).parent/"adaptive_meshes_20261029"
        index=json.loads((directory/"ADAPTIVE_MESH_INDEX_NOT_AUTHORIZED.json").read_bytes())
        self.assertEqual(len(index["cases"]),4)
        for item in index["cases"]:
            raw=(directory/item["mesh_file"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),item["mesh_sha256"])
            self.assertEqual(raw,prepare.encode(mesh.generate(item["family"],item["n"])))
            self.assertLessEqual(item["summary"]["dofs"],30000)
            self.assertFalse(item["execution_authorized"])
            self.assertEqual(item["quality"],quality.assess(json.loads(raw)))
            self.assertEqual(item["nested_with_n8"],item["n"] == 16)

    def test_case_binding_draft_matches_the_frozen_mesh_index(self):
        base=Path(__file__).parent
        raw=(base/"prepared_20261029/MATRIX_NOT_AUTHORIZED.json").read_bytes()
        matrix=json.loads(raw)
        binding=json.loads((base/"PREPARED_CASE_BINDINGS_DRAFT.json").read_bytes())
        test_source=base.parents[1]/binding["test_source_path"]
        self.assertEqual(binding["test_source_sha256_provisional"],hashlib.sha256(test_source.read_bytes()).hexdigest())
        self.assertFalse(binding["runner_registered"])
        self.assertEqual(binding["matrix_sha256"],hashlib.sha256(raw).hexdigest())
        self.assertEqual(len(binding["cases"]),12)
        indexed={case["case_id"]:case for case in matrix["cases"]}
        for item in binding["cases"]:
            self.assertEqual(item["mesh_sha256"],indexed[item["case_id"]]["mesh_sha256"])
            self.assertEqual(item["selected_dofs"],indexed[item["case_id"]]["dofs"])
            self.assertEqual(item["nodeid"],indexed[item["case_id"]]["nodeid"])
            self.assertEqual(item["state"],"PREPARED_NOT_AUTHORIZED")
            self.assertEqual(hashlib.sha256((base/item["criteria_path"]).read_bytes()).hexdigest(),
                             item["criteria_sha256_provisional"])

    def test_adaptive_catalog_has_closed_identity_and_mesh_proposals(self):
        base=Path(__file__).parent
        catalog=json.loads((base/"ADAPTIVE_CATALOG_DRAFT.json").read_bytes())
        cases=catalog["candidates"]
        self.assertEqual(len(cases),12)
        self.assertEqual(len({case["candidate_id"] for case in cases}),12)
        self.assertEqual(len({case["nodeid"] for case in cases}),12)
        for case in cases:
            self.assertEqual(case["status"],"PREPARED_NOT_AUTHORIZED")
            self.assertEqual(case["nodeid_status"],"REGISTERED_PREPARED_NOT_AUTHORIZED")
            binding=case["prepared_mesh"]
            self.assertEqual(hashlib.sha256((base/binding["path"]).read_bytes()).hexdigest(),binding["sha256"])
            self.assertLessEqual(binding["selected_dofs"],30000)
            self.assertEqual(hashlib.sha256((base/case["criteria_path"]).read_bytes()).hexdigest(),
                             case["criteria_sha256_provisional"])


class OracleContracts(unittest.TestCase):
    def test_zero_fabricated_field_has_unit_relative_error(self):
        prepared=mesh.generate("HEX8",2)
        nodal=[(0.0,0.0,0.0)]*prepared["summary"]["nodes"]
        result=field_error_draft.integrated_errors(prepared,nodal,order=4)
        for key in ("displacement_relative_l2","energy_error_relative","stress_error_relative","strain_error_relative"):
            self.assertAlmostEqual(result[key],1.0,delta=1e-13)
        self.assertEqual(result["status"],"DIAGNOSTIC_UNQUALIFIED")

    def test_affine_field_sampling_is_exact_for_all_families(self):
        expected_strain=(0.1,-0.3,-0.1,0.2,0.4,0.2)
        lam,mu=oracle.lame()
        expected_stress=tuple(lam*sum(expected_strain[:3])+2*mu*v for v in expected_strain[:3])+tuple(
            mu*v for v in expected_strain[3:]
        )
        for family in mesh.FORMULATIONS:
            for skew in (False,True):
                m=mesh.generate(family,2)
                d=m["integer_coordinate_denominator"]
                points=[(p[0]+p[1],p[1],p[2]) if skew else p for p in m["nodes_integer"]]
                nodal=[]
                for p in points:
                    x,y,z=(v/d for v in p)
                    nodal.append((0.1*x+0.2*y,-0.3*y+0.4*z,0.2*x-0.1*z))
                reference=(0.2,0.2,0.2) if family.startswith("TET") else (0.2,-0.3,0.1)
                sampled=sampling.sample_cell(family,m["connectivity_zero_based"][0],points,d,nodal,reference)
                for actual,expected in zip(sampled["strain"],expected_strain):
                    self.assertAlmostEqual(actual,expected,delta=1e-13)
                for actual,expected in zip(sampled["stress_pa"],expected_stress):
                    self.assertAlmostEqual(actual,expected,delta=1e-7)

    def test_reference_shape_gradients_are_independently_differentiated(self):
        h=1e-6
        for family in mesh.FORMULATIONS:
            point=(0.17,0.21,0.13) if family.startswith("TET") else (0.17,-0.21,0.13)
            gradients=basis.shape_gradients(family,point)
            for axis in range(3):
                self.assertAlmostEqual(sum(g[axis] for g in gradients),0.0,delta=1e-13)
                plus,minus=list(point),list(point)
                plus[axis]+=h
                minus[axis]-=h
                vp,vm=basis.shape_values(family,tuple(plus)),basis.shape_values(family,tuple(minus))
                for i in range(len(vp)):
                    self.assertAlmostEqual(gradients[i][axis],(vp[i]-vm[i])/(2*h),delta=1e-9)

    def test_reference_quadrature_polynomial_moments(self):
        for order in (4,8,12):
            hexa = quadrature.hexahedron_rule(order)
            tetra = quadrature.tetrahedron_duffy_rule(order)
            self.assertAlmostEqual(sum(w for _,_,_,w in hexa),8.0,delta=1e-12)
            self.assertAlmostEqual(sum(w*x*x for x,_,_,w in hexa),8/3,delta=1e-12)
            self.assertAlmostEqual(sum(w for _,_,_,w in tetra),1/6,delta=1e-13)
            for coordinate in range(3):
                self.assertAlmostEqual(sum(row[3]*row[coordinate] for row in tetra),1/24,delta=1e-13)
            self.assertTrue(all(row[3] > 0 for row in tetra))
        for degree in range(24):
            exact=0.0 if degree % 2 else 2/(degree+1)
            self.assertAlmostEqual(sum(w*x**degree for x,w in quadrature._GAUSS[12]),exact,delta=1e-13)

    def test_postprocessing_on_fabricated_fields(self):
        values = metrics.field_errors([2.0], [(1.0,2.0,2.0)], [(0,0,0,0.1,0,0)],
                                      lame_lambda_pa=2.0, shear_mu_pa=3.0)
        self.assertAlmostEqual(values["displacement_l2_m_5_2"], math.sqrt(18.0))
        self.assertAlmostEqual(values["energy_error_norm_sqrt_j"], math.sqrt(2*3*0.1**2))
        self.assertAlmostEqual(metrics.stress_error_l2([2.0],[(0,0,0,1,0,0)]),2.0)
        balance = metrics.force_moment_balance([(1,0,0),(0,1,0)],[(0,0,2),(0,0,0)],[(0,0,0),(0,0,-2)])
        self.assertEqual(balance["force_closure_n"],(0,0,0))
        self.assertEqual(balance["moment_closure_nm"],(-2,-2,0))
        with self.assertRaises(ValueError):
            metrics.field_errors([0],[(0,0,0)],[(0,0,0,0,0,0)],lame_lambda_pa=1,shear_mu_pa=1)

    def test_pairwise_orders_do_not_invent_convergence(self):
        self.assertEqual(metrics.observed_orders([0.5,0.25,0.125],[0.5,0.25,0.125]),(1.0,1.0))
        self.assertEqual(metrics.observed_orders([0.5,0.25,0.125],[0.5,0.0,0.0]),(None,None))
        for sizes,errors in (([0.5,0.25],[1,0.5]),([0.5,0.5,0.25],[1,0.5,0.25]),
                             ([0.5,0.25,0.125],[1,float("nan"),0.25])):
            with self.assertRaises(ValueError):
                metrics.observed_orders(sizes,errors)

    def test_basis_interpolation_and_partition_of_unity(self):
        tet_corners = ((0,0,0),(1,0,0),(0,1,0),(0,0,1))
        hex_corners = tuple(tuple(2*x-1 for x in point) for point in mesh.HEX_CORNERS)
        for family in mesh.FORMULATIONS:
            tet = family.startswith("TET")
            corners = tet_corners if tet else hex_corners
            edges = mesh.TET_EDGES if tet else mesh.HEX_EDGES
            nodes = list(corners)
            if family in {"TET10", "HEX20"}:
                nodes += [tuple((corners[a][i]+corners[b][i])/2 for i in range(3)) for a,b in edges]
            for i,point in enumerate(nodes):
                values = basis.shape_values(family, point)
                self.assertEqual(len(values),len(nodes))
                for j,value in enumerate(values):
                    self.assertAlmostEqual(value, 1.0 if i == j else 0.0, delta=1e-14)
            interior = (0.17,0.21,0.13) if tet else (0.17,-0.21,0.13)
            self.assertAlmostEqual(sum(basis.shape_values(family,interior)),1.0,delta=1e-14)

    def test_zero_dirichlet_on_all_faces(self):
        for axis,side in product(range(3), (0.0,1.0)):
            p = [0.23,0.37,0.61]
            p[axis] = side
            self.assertAlmostEqual(oracle.field(tuple(p))["u_m"][2], 0.0, delta=2e-20)

    def test_body_force_is_negative_stress_divergence(self):
        p = (0.24,0.37,0.63)
        h = 1e-5
        derivatives = []
        for axis in range(3):
            plus, minus = list(p),list(p)
            plus[axis] += h
            minus[axis] -= h
            sp = oracle.field(tuple(plus))["stress_pa"]
            sm = oracle.field(tuple(minus))["stress_pa"]
            derivatives.append([(a-b)/(2*h) for a,b in zip(sp,sm)])
        dx,dy,dz = derivatives
        divergence = (dx[0]+dy[3]+dz[5], dx[3]+dy[1]+dz[4], dx[5]+dy[4]+dz[2])
        body = oracle.field(p)["body_force_n_m3"]
        for a,b in zip(divergence,body):
            self.assertAlmostEqual(a+b, 0.0, delta=1e-5)

    def test_exact_energy_against_independent_product_quadrature(self):
        lam,mu = oracle.lame()
        count=12
        integral=0.0
        for i,j,k in product(range(count+1), repeat=3):
            eps=oracle.field((i/count,j/count,k/count))["strain"]
            wz,wy,wx=eps[2],eps[4],eps[5]
            density=0.5*lam*wz*wz + mu*(wz*wz+0.5*(wx*wx+wy*wy))
            weight=math.prod(0.5 if q in (0,count) else 1.0 for q in (i,j,k))
            integral += weight*density/count**3
        self.assertAlmostEqual(integral,oracle.exact_energy_j(),delta=1e-13)

    def test_global_balance_against_independent_product_quadrature(self):
        count = 20
        force = [0.0, 0.0, 0.0]
        moment = [0.0, 0.0, 0.0]
        for i,j,k in product(range(count+1), repeat=3):
            x,y,z = (i/count,j/count,k/count)
            fx,fy,fz = oracle.field((x,y,z))["body_force_n_m3"]
            weight=math.prod(0.5 if q in (0,count) else 1.0 for q in (i,j,k))/count**3
            for axis,val in enumerate((fx,fy,fz)):
                force[axis] += weight*val
            for axis,val in enumerate((y*fz-z*fy,z*fx-x*fz,x*fy-y*fx)):
                moment[axis] += weight*val
        exact = oracle.exact_global_balance()
        scale = exact["body_force_n"][2]
        for actual,reference in zip(force,exact["body_force_n"]):
            self.assertLessEqual(abs(actual-reference), 0.007*scale)
        for actual,reference in zip(moment,exact["body_moment_origin_nm"]):
            self.assertLessEqual(abs(actual-reference), 0.007*scale)


if __name__ == "__main__":
    unittest.main()
