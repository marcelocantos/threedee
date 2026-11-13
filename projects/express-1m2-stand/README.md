# Express 1M2 stand

An open lattice stand that holds an OWC Express 1M2 external SSD upright on
its long edge, 10 mm off the table, with the extruded cooling-fin channels
vertical so warm air rises straight through them. Designed with build123d on
12 November 2026. v1 used the published size (132 × 71.1 × 22.8 mm); v2
uses the drive's **measured** size, 133 × 72 × 24 mm (1 mm over the spec on
every dimension). v2.1 tightens the fit clearance from 0.6 mm to 0.2 mm a
side for a snug fit. v2.2 makes the base lattice continuous under the fins
(earlier versions cut an open window there, which split the lattice and
weakened the base). Fin depth, the solid block, the edge strip, the rubber feet
and the edge rounding are still **estimates**.

- `express_1m2_stand.py` — Parametric build123d source; dimensions are in
  millimetres. The drive's dimensions (marked `MEASURED` or `ESTIMATE`) and
  the stand's (fit clearance, bottom gap, upright height, end-stop heights,
  lattice sizes, base footprint) are parameters near the top.
- `export/express-1m2-stand.stl`, `export/express-1m2-stand.step` — The
  stand as printed, centred on the Bambu X1 Carbon's 256 × 256 mm bed. No
  supports needed.
- `export/express-1m2-standin.stl` — A rough block-and-fins stand-in for the
  drive, in the same coordinates, used for clash checks and previews. Not
  for printing, and not the drive's real shape (`--no-standin` skips it).

From the repository root, run `make projects/express-1m2-stand/export/.stamp`
to build, or `make` to build all parts. Exports are local build outputs and
are ignored by Git; `make clean` removes them.

## Drive dimensions

| Parameter | Value | Status |
| --- | --- | --- |
| `drive_length` (along the table) | 133 mm | **measured** (spec 132) |
| `drive_height` (standing up) | 72 mm | **measured** (spec 71.1) |
| `drive_thickness` (incl. fins) | 24 mm | **measured** (spec 22.8) |
| `fin_height` (fin depth) | 8 mm | estimate; solid body is 16 mm |
| `block_length` (unfinned block) | 18 mm | guessed from photos |
| `block_end` | `"port"` | guessed — which end the solid block is at |
| `fin_edge` (solid strip at the other end) | 2 mm | guessed |
| `corner_radius` (long edges) | 2 mm | guessed |
| Rubber feet: `foot_diameter`, `foot_height`, `foot_inset`, `foot_up` | 12, 1.5, 22 from each end, mid-height | guessed |
| `drive_mass` | ~300 g design load | ~260 g measured |

The measurements still worth taking: the fin depth (body thickness), which end the solid block is at and how long it is, whether there is
a solid strip at the other end of the finned face, and where the rubber feet
are on the smooth face.

## Shape

The drive stands on its long edge: 133 mm along the table, 72 mm tall, 24 mm
thick, with the smooth face on one side and the finned face on the
other. It drops into a 24.4 mm slot (0.2 mm `fit_clearance` each side, for a snug
fit; v1 and v2 had 0.6 mm) and
rests on two 2 mm lattice rails under its solid (assumed 16 mm) body, 2.5
mm in from the smooth face and 3 mm short of the fins, 10 mm (`bottom_gap`)
above the table. Nothing touches the fin tips: nothing stands between the
3 mm base plate and the fins, or above them, so air rises from the table
through the base's diamond openings and straight up the fin channels. The
base lattice is continuous under the fins (from v2.2). The script checks
that the fin air channel is clear from the base plate up, that the base is
one piece, and that the stand does not clash with the stand-in.

Side legs 3 mm thick rise 35 mm up the faces (`upright_height`): on the
smooth face, 10 mm at each end, clear of the rubber feet, plus a 3 mm lip
along the bottom edge; on the finned face, the length of the solid block at
one end and the 2 mm edge strip at the other. The inner top edges have a
1.8 mm 45° lead-in chamfer for dropping the drive in.

An end trestle at each end ties the legs together and splays out at 45°
into a 146.2 × 96 mm lattice base (3 mm plate, diamond lattice, 5 mm rim,
6 mm corner radius). At the LED end, 3 mm corner stops reach round onto the
end face to 22 mm up and the middle is open, so the LED stays visible. At
the USB-C end the stops are only 6 mm high, so the port and the cable are
clear; the cable leaves straight out of that end.

Overall 146.2 × 96 × 45 mm; about 34.0 cm³ (~42 g PLA). With the drive's
centre of gravity about 46 mm up, it would have to lean about 46° sideways
before it tipped.

## Printing

Print it as exported, base flat on the bed. Every opening has a 45° roof or
is open on top, and the legs are vertical, so no supports are needed. PLA is
fine.
