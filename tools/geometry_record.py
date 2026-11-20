# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0

"""Record geometric identity of every part ``make`` builds.

Runs each part the way the Makefile does, twice by default, and writes
volume, bounding box, centre of mass and face count from the STEP solid,
plus a mesh hash of the STL the script actually wrote. The hash is
SHA-256 of the triangle records sorted by their bytes, so triangle order
does not matter and the STL header does not. A second run measures
kernel noise before any tolerance is claimed.

    uv run --frozen --offline python tools/geometry_record.py --out docs/geometry-baseline.json
    uv run --frozen --offline python tools/geometry_record.py --check docs/geometry-baseline.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Same invocations as the Makefile, in the same order.
PARTS = [
    ("projects/baby_gate_latch.py", []),
    ("projects/bosch_adapter.py", []),
    ("projects/catflap_rpi.py", []),
    ("projects/led_stumps.py", []),
    ("projects/machinist_square_mount.py", []),
    ("projects/magnet_tube.py", []),
    ("projects/nailgun_tip.py", []),
    ("projects/rotary_bearing.py", []),
    ("projects/router_bit_rack.py", []),
    ("projects/screw_box_partitions.py", []),
    ("projects/starlock_holders.py", []),
    ("projects/triton_lifter.py", []),
    ("projects/trolley-key/ring_hook.py", ["--plate", "--no-preview"]),
    ("projects/scale-rails/scale_rails.py", ["--no-preview"]),
    ("projects/puzzle-tray/puzzle_tray.py", ["--no-preview"]),
    ("projects/express-1m2-stand/express_1m2_stand.py", ["--no-preview"]),
    ("projects/mixer-stand/mixer_stand.py", ["--no-preview"]),
]


def num(value: float) -> str:
    """Decimal that round-trips a float64."""
    return format(value, ".17g")


# Vertex-occupancy cell used when an STL hash is not stable across runs.
OCCUPANCY_MM = 1.0


def mesh_identity(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 84:
        raise SystemExit(f"{path} is not an STL ({len(data)} bytes)")
    count = struct.unpack_from("<I", data, 80)[0]
    expect = 84 + count * 50
    if expect != len(data):
        raise SystemExit(f"{path} binary STL length {len(data)} != {expect}")
    records = [data[84 + i * 50 : 84 + (i + 1) * 50] for i in range(count)]
    digest = hashlib.sha256()
    low = [1e300, 1e300, 1e300]
    high = [-1e300, -1e300, -1e300]
    area = 0.0
    cells = set()
    for record in records:
        floats = struct.unpack("<12f", record[:48])
        verts = (floats[3:6], floats[6:9], floats[9:12])
        edge_a = tuple(verts[1][i] - verts[0][i] for i in range(3))
        edge_b = tuple(verts[2][i] - verts[0][i] for i in range(3))
        cross = (
            edge_a[1] * edge_b[2] - edge_a[2] * edge_b[1],
            edge_a[2] * edge_b[0] - edge_a[0] * edge_b[2],
            edge_a[0] * edge_b[1] - edge_a[1] * edge_b[0],
        )
        area += 0.5 * (cross[0] ** 2 + cross[1] ** 2 + cross[2] ** 2) ** 0.5
        for vert in verts:
            for axis in range(3):
                low[axis] = min(low[axis], vert[axis])
                high[axis] = max(high[axis], vert[axis])
            cells.add(tuple(int(round(vert[axis] / OCCUPANCY_MM)) for axis in range(3)))
    for record in sorted(records):
        digest.update(record)
    occupancy = hashlib.sha256()
    for cell in sorted(cells):
        occupancy.update(struct.pack("<3i", *cell))
    return {
        "triangles": count,
        "mesh_sha256": digest.hexdigest(),
        "raw_sha256": hashlib.sha256(data).hexdigest(),
        "occupancy_mm": OCCUPANCY_MM,
        "occupancy_sha256": occupancy.hexdigest(),
        "mesh_bbox_min": [num(v) for v in low],
        "mesh_bbox_max": [num(v) for v in high],
        "mesh_area": num(area),
    }


def step_identity(path: Path) -> dict:
    from build123d import import_step
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps

    shape = import_step(path)
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape.wrapped, props)
    centre = props.CentreOfMass()
    box = shape.bounding_box()
    return {
        "volume": num(shape.volume),
        "bbox_min": [num(box.min.X), num(box.min.Y), num(box.min.Z)],
        "bbox_max": [num(box.max.X), num(box.max.Y), num(box.max.Z)],
        "center_of_mass": [num(centre.X()), num(centre.Y()), num(centre.Z())],
        "face_count": len(shape.faces()),
    }


def run_part(script: str, args: list[str], directory: Path) -> dict:
    command = [
        "uv", "run", "--frozen", "--offline", "--project", str(ROOT),
        "python", str(ROOT / script), *args,
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    completed = subprocess.run(
        command, cwd=directory, capture_output=True, text=True, env=env
    )
    if completed.returncode != 0:
        sys.stderr.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        raise SystemExit(f"{script} exited {completed.returncode}")
    files = {}
    for path in sorted(directory.iterdir()):
        if path.suffix == ".step":
            files[path.name] = step_identity(path)
        elif path.suffix == ".stl":
            files[path.name] = mesh_identity(path)
        elif path.name != ".stamp":
            raise SystemExit(f"{script} wrote unexpected {path.name}")
    if not files:
        raise SystemExit(f"{script} wrote no STL or STEP")
    return files


def measure(runs: int) -> dict:
    import build123d

    parts = {}
    deltas = {}
    for script, args in PARTS:
        print(f"record {script}", flush=True)
        samples = []
        for _ in range(runs):
            directory = Path(tempfile.mkdtemp(prefix="geometry-record-"))
            try:
                samples.append(run_part(script, args, directory))
            finally:
                shutil.rmtree(directory)
        parts[script] = samples[0]
        if runs > 1:
            deltas[script] = compare_files(samples[0], samples[1])
    document = {
        "build123d": build123d.__version__,
        "python": sys.version.split()[0],
        "runs": runs,
        "parts": parts,
    }
    if runs > 1:
        document["noise"] = collect_noise(deltas)
    return document


def compare_files(left: dict, right: dict) -> list[dict]:
    rows = []
    names = sorted(set(left) | set(right))
    for name in names:
        if name not in left or name not in right:
            rows.append({"file": name, "missing": True})
            continue
        a, b = left[name], right[name]
        row = {"file": name}
        if "volume" in a or "volume" in b:
            for key in ("volume",):
                row[key] = abs(float(a[key]) - float(b[key]))
            for key in ("bbox_min", "bbox_max", "center_of_mass"):
                row[key] = max(abs(float(x) - float(y)) for x, y in zip(a[key], b[key]))
            row["face_count"] = 0 if a["face_count"] == b["face_count"] else 1
        if "mesh_sha256" in a or "mesh_sha256" in b:
            row["mesh_sha256"] = 0 if a.get("mesh_sha256") == b.get("mesh_sha256") else 1
            row["raw_sha256"] = 0 if a.get("raw_sha256") == b.get("raw_sha256") else 1
            row["triangles"] = 0 if a.get("triangles") == b.get("triangles") else 1
        rows.append(row)
    return rows


def collect_noise(deltas: dict) -> dict:
    summary = {
        "max_abs_volume": 0.0,
        "max_abs_bbox": 0.0,
        "max_abs_center_of_mass": 0.0,
        "face_count_mismatches": [],
        "mesh_hash_mismatches": [],
        "raw_hash_mismatches": [],
        "missing": [],
    }
    for script, rows in deltas.items():
        for row in rows:
            label = f"{script}:{row['file']}"
            if row.get("missing"):
                summary["missing"].append(label)
                continue
            if "volume" in row:
                summary["max_abs_volume"] = max(summary["max_abs_volume"], row["volume"])
                summary["max_abs_bbox"] = max(
                    summary["max_abs_bbox"], row["bbox_min"], row["bbox_max"]
                )
                summary["max_abs_center_of_mass"] = max(
                    summary["max_abs_center_of_mass"], row["center_of_mass"]
                )
                if row["face_count"]:
                    summary["face_count_mismatches"].append(label)
            if row.get("mesh_sha256"):
                summary["mesh_hash_mismatches"].append(label)
            if row.get("raw_sha256"):
                summary["raw_hash_mismatches"].append(label)
    summary["part_count"] = len(deltas)
    return summary


def check(baseline_path: Path) -> int:
    baseline = json.loads(baseline_path.read_text())
    fresh = measure(1)
    noise = baseline.get("noise") or {}
    volume_tol = float(noise.get("max_abs_volume") or 0.0)
    bbox_tol = float(noise.get("max_abs_bbox") or 0.0)
    com_tol = float(noise.get("max_abs_center_of_mass") or 0.0)
    failures = []
    if fresh["build123d"] != baseline["build123d"]:
        failures.append(
            f"build123d {fresh['build123d']} != baseline {baseline['build123d']}"
        )
    base_parts = baseline["parts"]
    if set(fresh["parts"]) != set(base_parts):
        failures.append(
            f"part set {sorted(fresh['parts'])} != {sorted(base_parts)}"
        )
    for script, files in fresh["parts"].items():
        before = base_parts.get(script, {})
        if set(files) != set(before):
            failures.append(f"{script} files {sorted(files)} != {sorted(before)}")
            continue
        for name, got in files.items():
            exp = before[name]
            if "volume" in exp:
                if abs(float(got["volume"]) - float(exp["volume"])) > volume_tol:
                    failures.append(f"{script}:{name} volume {got['volume']} != {exp['volume']}")
                for key, tol in (
                    ("bbox_min", bbox_tol),
                    ("bbox_max", bbox_tol),
                    ("center_of_mass", com_tol),
                ):
                    delta = max(abs(float(a) - float(b)) for a, b in zip(got[key], exp[key]))
                    if delta > tol:
                        failures.append(f"{script}:{name} {key} delta {delta} > {tol}")
                if got["face_count"] != exp["face_count"]:
                    failures.append(
                        f"{script}:{name} faces {got['face_count']} != {exp['face_count']}"
                    )
            if "mesh_sha256" in exp:
                label = f"{script}:{name}"
                unstable = label in set(noise.get("mesh_hash_mismatches") or [])
                if unstable:
                    if got.get("occupancy_sha256") != exp.get("occupancy_sha256"):
                        failures.append(f"{label} 1 mm occupancy hash changed")
                    span = int((noise.get("mesh_triangle_span") or {}).get(label, 0))
                    if abs(got["triangles"] - exp["triangles"]) > span:
                        failures.append(
                            f"{label} triangles {got['triangles']} vs {exp['triangles']} span {span}"
                        )
                    for key in ("mesh_bbox_min", "mesh_bbox_max"):
                        if key not in exp:
                            continue
                        delta = max(
                            abs(float(a) - float(b)) for a, b in zip(got[key], exp[key])
                        )
                        if delta > 0:
                            failures.append(f"{label} {key} delta {delta}")
                else:
                    if got["mesh_sha256"] != exp["mesh_sha256"]:
                        failures.append(f"{label} mesh hash changed")
                    if got["triangles"] != exp["triangles"]:
                        failures.append(
                            f"{label} triangles {got['triangles']} != {exp['triangles']}"
                        )
    if failures:
        print(f"{len(failures)} geometric mismatch(es):")
        for line in failures:
            print(f"  {line}")
        return 1
    print(
        f"geometric identity holds for {len(fresh['parts'])} parts "
        f"(volume tol {volume_tol}, bbox tol {bbox_tol}, com tol {com_tol})"
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="Write a baseline JSON")
    parser.add_argument("--check", type=Path, help="Rebuild once and compare to this baseline")
    parser.add_argument("--runs", type=int, default=2, help="Builds per part when writing")
    args = parser.parse_args()
    if args.check:
        raise SystemExit(check(args.check))
    if not args.out:
        raise SystemExit("pass --out or --check")
    document = measure(args.runs)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(document, indent=2) + "\n")
    noise = document.get("noise", {})
    print(
        f"wrote {args.out} parts={len(document['parts'])} "
        f"volume_noise={noise.get('max_abs_volume')} "
        f"bbox_noise={noise.get('max_abs_bbox')} "
        f"com_noise={noise.get('max_abs_center_of_mass')} "
        f"mesh_mismatches={noise.get('mesh_hash_mismatches')}"
    )


if __name__ == "__main__":
    main()
