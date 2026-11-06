# Copyright 2026 Marcelo Cantos
# SPDX-License-Identifier: Apache-2.0
"""Printable Haberdasher: four kerfed tiles and a tray with both pockets.

Coordinates come from pieces.json, written by geometry.py from Dudeney's
1907 construction. The tiles are inset by `kerf_mm` on every edge, then
extruded. The tray has an equilateral-triangle pocket and a square pocket.
Tiles are laid out beside the tray so the export is one print, not a
fused assembly. Run from this directory's export folder, as the other
threedee projects do:

    mkdir -p export && cd export && python ../haberdasher.py --no-preview
"""

import argparse
import json
from pathlib import Path

from build123d import (
    Align,
    Axis,
    Compound,
    Polygon,
    Pos,
    Rectangle,
    export_step,
    export_stl,
    extrude,
    fillet,
)

from geometry import inset_polygon, tiles_fit

ROOT = Path(__file__).resolve().parent
BED = 256
EXCLUDE_X, EXCLUDE_Y = 18, 28
ORIGIN = (EXCLUDE_X + 6, EXCLUDE_Y + 6)
OUTER_ROUND = 1.2


def load_dissection():
    doc = json.loads((ROOT / "pieces.json").read_text())
    return next(item for item in doc["dissections"] if item["id"] == "haberdasher")


def shift(poly, dx, dy):
    return [(x + dx, y + dy) for x, y in poly]


def bbox(polys):
    xs = [x for poly in polys for x, _ in poly]
    ys = [y for poly in polys for _, y in poly]
    return min(xs), min(ys), max(xs), max(ys)


def scale_ring(ring, side):
    return [(side * x, side * y) for x, y in ring]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-preview", action="store_true")
    parser.add_argument("--kerf", type=float, default=None, help="Override the JSON kerf (mm)")
    args = parser.parse_args()

    dissection = load_dissection()
    spec = dissection["print"]
    side = spec["side_mm"]
    kerf = spec["kerf_mm"] if args.kerf is None else args.kerf
    if not tiles_fit(dissection, kerf, side):
        raise SystemExit(f"kerf {kerf} mm does not leave every tile inside both pockets")

    triangle = scale_ring(
        [dissection["points"][name]["xy"] for name in dissection["triangle"]],
        side,
    )
    square = scale_ring(dissection["square"], side)
    t_minx, t_miny, _, _ = bbox([triangle])
    s_minx, s_miny, s_maxx, s_maxy = bbox([square])
    _, _, t_maxx, t_maxy = bbox([triangle])
    wall = spec["wall_mm"]
    gap = spec["pocket_gap_mm"]

    tri_at = shift(triangle, wall - t_minx, wall - t_miny)
    sq_origin_x = wall - t_minx + (t_maxx - t_minx) + gap
    sq_at = shift(square, sq_origin_x - s_minx, wall - s_miny)
    minx, miny, maxx, maxy = bbox([tri_at, sq_at])
    if minx < wall - 1e-6 or miny < wall - 1e-6:
        raise SystemExit("pocket sits inside the wall margin")
    width = maxx + wall
    height = maxy + wall

    slab = Pos(width / 2, height / 2) * Rectangle(width, height)
    body = extrude(slab, spec["floor_mm"] + spec["pocket_depth_mm"])
    vertical = [
        edge for edge in body.edges()
        if edge.geom_type.name == "LINE" and abs(edge.tangent_at(0).Z) > 0.9
    ]
    body = fillet(vertical, OUTER_ROUND)
    body = fillet(body.edges().group_by(Axis.Z)[-1], OUTER_ROUND)

    depth = spec["pocket_depth_mm"]
    for pocket in (tri_at, sq_at):
        body -= Pos(0, 0, spec["floor_mm"]) * extrude(Polygon(*pocket), depth + 1)

    # Tiles in the triangle arrangement, inset, in a row past the tray.
    tiles = []
    cursor = wall
    tile_y = height + 8
    for piece in dissection["pieces"]:
        raw = scale_ring(piece["triangle"], side)
        inset = inset_polygon(raw, kerf)
        ix0, iy0, ix1, iy1 = bbox([inset])
        placed = shift(inset, cursor - ix0, tile_y - iy0)
        solid = extrude(Polygon(*placed), spec["tile_mm"])
        if solid.volume <= 0 or not solid.is_valid:
            raise SystemExit(f"{piece['id']} tile is not a valid solid")
        tiles.append(solid)
        cursor += (ix1 - ix0) + 6

    assembly = Pos(*ORIGIN, 0) * Compound(children=[body, *tiles])
    bb = assembly.bounding_box()
    if bb.min.X < EXCLUDE_X or bb.min.Y < EXCLUDE_Y:
        raise SystemExit("assembly reaches the printer's excluded corner")
    if bb.max.X > BED or bb.max.Y > BED or bb.min.X < 0 or bb.min.Y < 0:
        raise SystemExit(
            f"assembly {bb.size.X:.1f} x {bb.size.Y:.1f} mm does not fit the {BED} mm bed"
        )
    if not assembly.is_valid:
        raise SystemExit("assembly is not a valid shape")

    export_stl(assembly, "haberdasher.stl")
    export_step(assembly, "haberdasher.step")
    print(
        f"haberdasher {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.2f} mm; "
        f"side {side:g} mm; kerf {kerf:g} mm; "
        f"tiles {spec['tile_mm']:g} mm; pockets {depth:g} mm deep; "
        f"volume {assembly.volume / 1000:.1f} cm^3; "
        f"solids {len(assembly.solids())}"
    )
    write_previews(body, tiles, dissection["pieces"], tri_at, sq_at, kerf, side, dissection)

    if not args.no_preview:
        try:
            from ocp_vscode import show
            show(assembly)
        except ImportError:
            pass


def write_previews(tray, tiles, pieces, tri_at, sq_at, kerf, side, dissection):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    def faces_of(solid):
        verts, tris = solid.tessellate(0.2)
        out = []
        for tri in tris:
            out.append([(verts[i].X, verts[i].Y, verts[i].Z) for i in tri])
        return out

    def draw_solid(ax, solid, color, alpha=1, shade=False):
        faces = faces_of(solid)
        coll = Poly3DCollection(faces, alpha=alpha, linewidths=0)
        if shade:
            import matplotlib.colors as mcolors

            rgb = mcolors.to_rgb(color)
            light = (0.3, 0.45, 0.84)
            colors = []
            for (ax_, ay, az), (bx, by, bz), (cx, cy, cz) in faces:
                ux, uy, uz = bx - ax_, by - ay, bz - az
                vx, vy, vz = cx - ax_, cy - ay, cz - az
                nx = uy * vz - uz * vy
                ny = uz * vx - ux * vz
                nz = ux * vy - uy * vx
                norm = (nx * nx + ny * ny + nz * nz) ** 0.5 or 1.0
                # Quantize so coplanar triangles share a shade. Otherwise
                # the tessellation reads as stripes across a flat floor.
                nx, ny, nz = (round(component / norm, 2) for component in (nx, ny, nz))
                ndot = max(0.0, nx * light[0] + ny * light[1] + nz * light[2])
                scale = 0.42 + 0.58 * ndot
                colors.append(tuple(min(1.0, channel * scale) for channel in rgb))
            coll.set_facecolor(colors)
        else:
            coll.set_facecolor(color)
            coll.set_edgecolor(color)
        ax.add_collection3d(coll)

    def frame(ax, solids, tall=False):
        pts = [p for solid in solids for face in faces_of(solid) for p in face]
        xs, ys, zs = zip(*pts)
        dx = max(xs) - min(xs)
        dy = max(ys) - min(ys)
        dz = max(zs) - min(zs)
        ax.set_xlim(min(xs), max(xs))
        ax.set_ylim(min(ys), max(ys))
        ax.set_zlim(min(zs), max(zs) if dz > 0 else min(zs) + 1)
        # The tray is a few millimetres tall and hundreds wide. Stretch
        # height so the pocket floors are visible; tiles keep true scale.
        ax.set_box_aspect((dx, dy, max(dx, dy) * 0.28 if tall else max(8, dz)))
        ax.view_init(elev=32, azim=-58)
        ax.set_axis_off()

    fig = plt.figure(figsize=(8, 5.5))
    ax = fig.add_subplot(111, projection="3d")
    draw_solid(ax, tray, "#c8c2b4", shade=True)
    frame(ax, [tray], tall=True)
    fig.tight_layout()
    fig.savefig("preview-tray.png", dpi=130)
    plt.close(fig)

    fig = plt.figure(figsize=(8, 4.5))
    ax = fig.add_subplot(111, projection="3d")
    for solid, piece in zip(tiles, pieces):
        draw_solid(ax, solid, piece["color"])
    frame(ax, tiles)
    fig.tight_layout()
    fig.savefig("preview-tiles.png", dpi=130)
    plt.close(fig)

    # Plan of both pockets with the kerfed tiles in place. This is the
    # containment picture: each coloured ring is inside its pocket.
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2))
    for ax, pocket, key, title in (
        (axes[0], tri_at, "triangle", "Triangle pocket"),
        (axes[1], sq_at, "square", "Square pocket"),
    ):
        # Put the pocket back in model millimetres, centred, so both
        # panels show the arrangement rather than the tray offset.
        px, py = zip(*(pocket + [pocket[0]]))
        ax.fill(px, py, facecolor="#f4f1ea", edgecolor="#333", linewidth=1.2)
        raw_pocket = scale_ring(
            [dissection["points"][n]["xy"] for n in dissection["triangle"]] if key == "triangle"
            else dissection["square"],
            side,
        )
        ox = pocket[0][0] - raw_pocket[0][0]
        oy = pocket[0][1] - raw_pocket[0][1]
        for piece in pieces:
            ring = shift(inset_polygon(scale_ring(piece[key], side), kerf), ox, oy)
            xs, ys = zip(*(ring + [ring[0]]))
            ax.fill(xs, ys, facecolor=piece["color"], edgecolor="black", linewidth=0.4)
        ax.set_aspect("equal")
        ax.set_title(title)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.tight_layout()
    fig.savefig("preview-plan.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    main()
