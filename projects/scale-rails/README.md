# Scale rails

A one-piece, U-shaped cradle that hangs a flat kitchen scale (Soehnle,
220 × 220 × 20 mm) under the pantry shelf. The scale has a thin white top
over a black base whose sides taper inward toward the bottom, so each side
rail has a wide lip that reaches under the base. There is no ceiling: the
scale's top runs 1 mm under the shelf itself, which keeps the stack
shallow. A back wall across the full width joins the two rails and stops the
scale with 5 mm sticking out past the shelf edge, just enough to grip its
edge. Designed with build123d on 1 November 2026. The first version (two
separate rails, 50 mm overhang) was printed and worked; this version cuts
the overhang to 5 mm and joins the rails with the back wall. It has not
been printed yet.

- `scale_rails.py` — Parametric build123d source; dimensions are in
  millimetres. Scale size and profile, clearances, protrusion, lip, wall,
  back wall, screw, lead-in and rounding sizes are parameters near the top.
- `export/scale-rails-plate.stl`, `export/scale-rails-plate.step` — The
  cradle the right way up on the Bambu X1 Carbon's 256 × 256 mm bed, ready
  for the slicer. No supports needed. It sits 12.5 mm back from centre so it
  clears the bed's excluded front-left corner (see below).
- `export/scale-rails-assembly.step` — The cradle and a reference scale in
  their installed positions.
- `export/scale-rails-installed.stl`, `export/scale-ghost.stl` —
  Installed-position meshes for previews.

From the repository root, run `make projects/scale-rails/export/.stamp` to
build this project, or `make` to build all parts. Generated exports are
local build outputs and are ignored by Git; `make clean` removes them.

The cradle is 243 mm across its outer walls, 219 mm deep and 24 mm tall.
Each rail is an 11 mm side wall and a 15 mm by 3 mm lip, with a 5 mm 45°
gusset in the corner that stays clear of the tapered base. The back wall is
4 mm thick and runs the full 24 mm up to the shelf. The scale's profile
(4 mm white top, base sides inset 6 mm at the top and 10.5 mm at the
bottom) is estimated from photos, which leaves the lip 4 mm under the base;
the rubber feet sit about 16 mm in from the sides, inboard of the lip, so
they never ride on it. Fix the rail fronts flush with the shelf's front edge
with three 3.5 × 16 mm countersunk wood screws per rail, 20, 107.5 and
195 mm back from the front, driven up through the wall from below; each
hole is counterbored to 5 mm under the shelf.

The open front has a lead-in: a 3 mm 45° chamfer down each wall's inner
face, where the scale's sides enter, and a 1.5 mm chamfer along each lip top
and gusset, which meet the base's bevel. The lip chamfer's top edge is
blended into a rounded nose with a 1.5 mm fillet, so the base's bottom edge
rides up onto the lip rather than catching. Every other edge gets a 1 mm
fillet except the edges lying in the shelf face, which stay sharp so the top
sits flush (including the rims of the pockets and counterbores), and the
screw holes. That takes in the edges on the bed, the vertical corners of the
U (front and back, outside and in, and the walls' front ends) and the
pockets' corners, which meet the shelf face only at a point; the bed
fillets are added last so that they blend around the rounded corners. Under
the lip's nose the 1.5 mm front face keeps a sliver of flat between the
chamfer's 1 mm lower fillet and the bed fillet; a full bullnose would
undercut the lip's foot. A fillet of 1 mm or less on the first layers prints fine on
the X1 Carbon.

Bambu Studio excludes an 18 × 28 mm corner at the front left of the X1
Carbon's bed, where the filament cutter trips, and warns if a part's convex
hull touches it. Because the cradle's hull is its whole 243 × 219 mm
rectangle, centring it on the bed would overlap that corner, so the plate
puts it at x 6.5–249.5 mm and y 31–250 mm (6.5 mm margin each side, 3 mm
clear of the corner, 6 mm at the back). The build fails if the part gets
too wide or too deep to keep that clearance. Bambu Studio can re-centre a
single STL on import; if it lands at Y 128 rather than 140.5, set its
position to X 128, Y 140.5 (the Move tool, or the object's position fields).

It prints standing on its bottom face: the lips lie flat on the bed, the
walls and back wall rise straight up, and the countersinks are at 45°, so
nothing overhangs beyond the bottom 0.3 mm of the 1 mm bed fillets. To keep
it light, each stretch of wall between the screw bosses has a pocket open on
the shelf face (straight up in the print), floored level with the top of the
gusset. A 2 mm outer skin, a 2 mm strip along the inner face that guides the
white top, 15.6 mm solid bosses around the screws, the front ends behind the
lead-in and the back wall stay solid. That brings the part from about 156
cm³ to 122 cm³; the carve-out sizes are parameters.
