# Mixer stand

An upright stand for a Braun MultiQuick stick-blender **motor body** (no
shaft fitted), stored nose down. Designed with build123d on 13 November
2026. Printed the same day in Bambu PLA Basic Brown via the printer's
local LAN API (about 1 h 57 m, 70 g). The stand is slightly lopsided but
does the job; the project is done.

The coupling tip drops into a 45° funnel that narrows to an open bore
1.5 mm smaller than the tip, so the tip's bottom edge lands on the 45° wall
and centres itself there. Nothing touches the drive socket, and the bore is
open right through, so drips fall out and the funnel wipes clean. Above it a
loose guide sleeve surrounds the wide ring (lock-release buttons included)
with 2 mm clearance a side and a 4 mm 45° lead-in, so the body drops in
easily and only snugs up when the tip meets the cone; the sleeve then stops
it leaning more than about 2.6°. A 45° skirt joins the sleeve to a 140 mm
round base.

- `mixer_stand.py` — Parametric build123d source; dimensions in millimetres.
  The mixer's dimensions (marked `MEASURED` or `ESTIMATE`) and the stand's
  (cone undersize, guide clearance, lead-in, wall, base size, windows,
  underside hollow) are parameters near the top.
- `export/mixer-stand.stl`, `export/mixer-stand.step` — The stand as
  printed, centred on the Bambu X1 Carbon's 256 × 256 mm bed. No supports.
- `export/mixer-standin.stl` — A rough stand-in for the motor body in the
  same coordinates, for clash checks and previews. Not for printing, and not
  the mixer's real shape (`--no-standin` skips it).

From the repository root, run `make projects/mixer-stand/export/.stamp` to
build, or `make` to build all parts. Exports are local build outputs and are
ignored by Git; `make clean` removes them.

## Mixer dimensions

| Parameter | Value | Status |
| --- | --- | --- |
| `ring_diameter` (wide ring incl. buttons) | 61 mm | **measured** |
| `coupling_diameter` (narrowest) | 31.6 mm | **measured** |
| `ring_to_tip` | 36 mm | **measured** (approx.) |
| `body_length` | 235 mm | **measured** |
| `tip_diameter` (lipped tip) | 33 mm | estimate |
| `tip_lip_height` | 3 mm | estimate (stand-in only) |
| `collar_diameter`, `collar_height` | 40, 8 mm | estimate (stand-in only) |
| `ring_core_diameter` (without buttons), `ring_height` | 58, 12 mm | estimate |
| `body_diameter` (above the ring, near the top) | 56, 50 mm | estimate (stand-in only) |
| `body_mass` | 700 g | estimate |
| `cg_fraction` | 45–55 % of the length above the tip | estimate |

The measurement that matters most is the tip's outer diameter (the cone is
sized from it). Next, the ring's height and its diameter without the buttons,
which set how far the sleeve lets the body lean.

## Shape

- **Seat:** open bore 31.5 mm (`tip_diameter` − `cone_undersize`) for the
  bottom 3 mm, then a 45° funnel widening to 65 mm at 19.75 mm up. The
  33 mm tip edge lands 0.75 mm above the bore lip (3.75 mm up). The script
  checks that the stand-in touches the cone when lowered 0.1 mm and clears
  everything when raised 0.05 mm, so the tip seats on the cone and nowhere
  else.
- **Guide:** 65 mm bore, 6 mm wall, straight for 8 mm alongside the ring,
  then a 4 mm 45° lead-in to 73 mm at the top (51.75 mm up). It surrounds
  the ring rather than the coupling: the higher contact means a given
  clearance allows less lean (about 2.6° here, against roughly 7° for a
  guide round the coupling), and the ring is smooth and round, with nothing
  to catch on. The script measures the 2.0 mm gap to the stand-in's
  buttons. Eight diamond windows below the ring show the coupling and let
  it dry.
- **Base:** 140 mm round, 4 mm plate, 18 diamond openings, 6 mm solid rim
  with rounded edges, a 5 mm cove where the 45° skirt meets the plate, and a
  hidden hollow under the funnel and skirt (3.5 mm shells).

Overall 140 × 140 × 51.8 mm; about 115 cm³ solid (~142 g PLA at 100 %;
less at normal infill). With the body's centre of gravity 45–55 % of its
length above the tip and 700 g, it would have to lean 32–37° before it
tipped (28–33° ignoring the stand's own weight).

## Printing

Print it as exported, base flat on the bed. The funnel, the skirt and the
underside hollow's roofs are 45° or steeper and the windows are diamonds, so
no supports are needed. PLA is fine.

The accepted print is Bambu PLA Basic Brown from AMS slot 2 (tray id 1), sent
on 13 November 2026 through the local API. It took about 1 h 57 m and used
70 g. An earlier same-day API job ran all 259 layers with no extrusion,
because the slice had missed the X1C start gcode that loads filament from
the AMS; there was no part and no purge waste. The retry, after flattening
the full X1C profile, printed and was accepted. See `tools/bambu/README.md`.
