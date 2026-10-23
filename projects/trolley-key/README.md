# Shopping trolley key

A reusable coin substitute for shopping trolleys, originally saved as the
“ring hook” model. Created with build123d on 14 September 2026 from a photo
of a blue printed widget. The owner printed and accepted the part that day.

- `ring_hook.py` — Parametric build123d source; dimensions are in millimetres.
- `export/ring-hook.stl` — Printable mesh for a slicer.
- `export/ring-hook.step` — Solid CAD model.

From the repository root, run `make projects/trolley-key/export/.stamp`
to build this part, or `make` to build all parts. Generated exports are
local build outputs and are ignored by Git; `make clean` removes them.

The profile has a keyring hole, tapered stem with a triangular opening,
and semicircular foot with a D-shaped cutout. The current plate is 3 mm
thick and the foot has a 10 mm outer radius. Edit the parameters near the
top of the source to change the dimensions.
