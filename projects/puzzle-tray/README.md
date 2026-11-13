# Puzzle tray

A shallow tray that holds a 3 × 3 wooden picture-cube puzzle (Hape, nine
45.1 mm cubes) in place of its cardboard box. Designed with build123d on
3 November 2026; hollow walls added as v4 on 9 November 2026. v4 was printed
in PLA; v5 (10 November 2026) widens the pocket by 1 mm, reshapes the grip
channels so a corner pinch hooks the fingers, and adds an optional
fuzzy-skin modifier for the channels.

- `puzzle_tray.py` — Parametric build123d source; dimensions are in
  millimetres. Cube size, grid, play, wall height and thickness, floor,
  rounding sizes, the grip channels (with an on/off toggle), the hollow
  walls (`hollow_walls`, `skin_thickness`, `corner_solid`, `min_cavity`;
  `--solid` on the command line forces solid walls) and the fuzzy-skin
  modifier are parameters near the top.
- `fuzzy_3mf.py` — Optional: builds a Bambu Studio project with the
  modifier already set to fuzzy skin (needs Bambu Studio installed).
- `export/puzzle-tray.stl`, `export/puzzle-tray.step` — The tray the right
  way up, centred on the Bambu X1 Carbon's 256 × 256 mm bed. No supports
  needed.
- `export/puzzle-tray-grip-modifier.stl` — Four slim modifier volumes, one
  per grip channel, in the same bed coordinates as the tray.
- `export/puzzle-tray-fuzzy-grips.3mf` — Optional Bambu Studio project: tray
  plus the modifier with fuzzy skin set, X1C 0.4 nozzle, 0.20 mm Standard,
  Bambu PLA Basic.

From the repository root, run `make projects/puzzle-tray/export/.stamp` to
build the STL, STEP and modifier STL, or `make` to build all parts. Run
`make projects/puzzle-tray/export/puzzle-tray-fuzzy-grips.3mf` for the
optional Studio project (not part of `make`, since it needs Bambu Studio).
Generated exports are local build outputs and are ignored by Git;
`make clean` removes them.

## Shape

The tray is 152.9 mm square and 20.04 mm tall. One square pocket, 136.9 mm
across, holds the nine cubes with 1.6 mm of slack overall (0.8 mm a side);
v4's 0.6 mm (135.9 mm pocket, 151.9 mm tray) printed a little tight. The
walls are 8 mm thick and rise 18 mm (40% of a cube) above a 2 mm floor. The
outer vertical corners and the outer top edges are rounded with a 5 mm
radius, so the walls roll over into the top; every other edge, including
the pocket rim and the bottom edge, gets a 1 mm round. The pocket's
vertical corners have 1.5 mm round reliefs cut outward into the wall, so the
cubes' corners never ride on a fillet, and the floor meets the walls square
so the cubes sit flat.

## Grip channels

The middle of each outer wall has a vertical channel for a thumb or
fingertip. The intended lift is a one-handed pinch across a corner: thumb
in one channel and forefinger in the channel on an adjacent wall. Each
channel is cut by a 12.5 mm radius cylinder standing just outside the wall,
which gives a channel 20 mm wide at the face (21.4 mm across the blended
opening) and 5 mm deep, leaving 3 mm of wall between it and the pocket. The
channels run the full height, open at the top and the bottom, so they print
without supports. Their edges are rounded 1.5 mm into the wall face and the
top roll-over, and the 1 mm bottom round follows the channel.

Why that shape: a finger bears on the flank of its channel nearest the
other channel and pushes along the line between the two fingers, which runs
at 45° to each wall. Where the flank's surface normal is turned less than
45° from the wall normal, pinching squeezes the finger out of the channel;
past 45° it draws the finger in, so the two flanks hook thumb and finger. The
flank turns furthest just inside the edge blend, at
acos((R − depth + blend) / (R + blend)) from the wall normal. v4 (R14.5,
4 mm deep, 2.5 mm blend) reached only 40.1°, so fingers slipped out. v5
(R12.5, 5 mm deep, 1.5 mm blend) reaches 50.0°, 5° past the pinch line
(53.1° at the unblended edge). The script checks this (`min_hook`, default
4°) and stops if a change brings the hook under the pinch line plus that
margin.

`grip_walls` picks which walls get a channel; `grips = False` gives the plain
tray.

## Hollow walls

With `hollow_walls = True` (the default), each wall holds sealed internal
cavities so the tray is lighter. The outer and inner surfaces are unchanged
from the solid tray. At least `skin_thickness` (default 1.2 mm, three
perimeters on a 0.4 mm nozzle) is left everywhere round each cavity: the
cavities keep clear of each channel by the skin plus `grip_clearance`
(0.15 mm, for the edge blend), and the ridge is lowered by `top_clearance`
(1.05 mm) so it stays a full skin inside the top roll-over. Behind the
deepest part of each channel only 3 mm of wall is left, too little for a
cavity, so the wall is solid there: each wall's cavity stops where it would
narrow below `min_cavity` (1.5 mm), about 5.3 mm either side of the channel
centre, leaving two cavities per wall (eight in all). The cavity roofs are
peaked at 45° from horizontal so they print without supports when the tray
sits on its flat bottom. The four corners stay solid for stiffness
(`corner_solid`, default 14 mm along each wall), and the 2 mm floor stays
solid. Bambu Studio slices the enclosed voids without trouble; the export is
a single valid solid.

At the defaults the solid tray is about 121 cm³ (~150 g of PLA at
1.24 g/cm³); the hollowed tray is about 89 cm³ (~110 g). Bambu Studio's
estimate at 0.20 mm Standard (15% infill) is about 86 g and 2 hours. A
normal sparse infill in the slicer on a solid model would already remove
most of that wall mass; the modelled cavities mainly lock in a thin wall
skin and a support-free roof whatever the slicer settings.

## Fuzzy-skin grips

For a rougher, grippier surface in the channels, use Bambu Studio's fuzzy
skin on the channels only, through the modifier:

1. Load `puzzle-tray.stl` onto the plate as usual.
2. Right-click the tray, choose Add modifier, then Load…, and pick
   `export/puzzle-tray-grip-modifier.stl`. If Studio asks whether to treat
   the file as a single object with multiple parts, say yes. It lines up
   with the tray on its own; if it lands elsewhere, set its position in the
   object list to X 128, Y 128, Z 7.7 (the modifier's centre).
3. Select the modifier in the object list, add the Fuzzy skin settings, and
   set Fuzzy skin to Outer walls (the contour only, not the cavity holes),
   Fuzzy skin thickness 0.3 mm and point distance 0.8 mm. These are
   reasonable PLA starting values; 0.2 mm thickness is gentler, 0.4 mm
   rougher.

The modifier is a 1.2 mm slab hugging each channel and its blends, from
0.4 mm to 15 mm high, so the first layer, the top roll-over and the rim stay
smooth, and it ends 1.8 mm short of the pocket face.
`make projects/puzzle-tray/export/puzzle-tray-fuzzy-grips.3mf` does all of
this automatically and writes a project that opens with the modifier already
set (checked by slicing it with the Studio command line: the channel walls
gain the fuzzy points from 0.4 to 15 mm and nothing else changes). Change the
filament preset to the one loaded before slicing.
