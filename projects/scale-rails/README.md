# Scale rails

A one-piece, U-shaped cradle that hangs a flat kitchen scale (Soehnle,
220 × 220 × 20 mm) under the pantry shelf. The scale has a thin white top
over a black base whose sides taper inward toward the bottom, so each side
rail has a wide lip that reaches under the base. There is no ceiling: the
scale's top runs 1 mm under the shelf itself, which keeps the stack
shallow. A back wall across the full width joins the two rails and stops the
scale with 10 mm sticking out past the shelf edge, enough to grip its edge
with a thumb. Designed with build123d on 1 November 2026. The first version
(two separate rails, 50 mm overhang) was printed and worked. The one-piece
version with a 5 mm overhang was printed in ASA on 2 November; its front
ends curled up off the bed, the scale fitted a shade tight between the
walls, and 5 mm was too little to grip. This version (3 November) widens
the gap by 0.5 mm a side, brings the back wall 5 mm forward, rounds the
lips' front corners and adds brim pads at the front ends. It was printed in ASA on 4 November and
curled up at both the front and the back. This version (v8, 4 November)
adds stress-relief slots across the floor, diamond lattice side and back
walls, and brim pads at the back corners too. The screw holes stay exactly
where they were, as they are already drilled in the shelf. It has not been
printed yet.

- `scale_rails.py` — Parametric build123d source; dimensions are in
  millimetres. Scale size and profile, clearances, protrusion, lip, wall,
  back wall, screw, lead-in and rounding sizes are parameters near the top.
- `export/scale-rails-plate.stl`, `export/scale-rails-plate.step` — The
  cradle the right way up on the Bambu X1 Carbon's 256 × 256 mm bed, ready
  for the slicer, with its brim pads. No supports needed. It lies turned a
  quarter turn, front ends to the right, placed to clear the bed's excluded
  front-left corner (see below).
- `export/scale-rails-assembly.step` — The cradle and a reference scale in
  their installed positions.
- `export/scale-rails-installed.stl`, `export/scale-ghost.stl` —
  Installed-position meshes for previews.

From the repository root, run `make projects/scale-rails/export/.stamp` to
build this project, or `make` to build all parts. Generated exports are
local build outputs and are ignored by Git; `make clean` removes them.

The cradle is 243 mm across its outer walls, 214 mm deep and 24 mm tall.
Each rail is a 10.5 mm side wall and a 15.5 mm by 3 mm lip, with 1 mm
between each wall and the scale's white top, with a 5 mm 45°
gusset in the corner that stays clear of the tapered base. The back wall is
4 mm thick and runs the full 24 mm up to the shelf. The scale's profile
(4 mm white top, base sides inset 6 mm at the top and 10.5 mm at the
bottom) is estimated from photos, which leaves the lip 4 mm under the base;
the rubber feet sit about 16 mm in from the sides, inboard of the lip, so
they never ride on it. Fix the rail fronts flush with the shelf's front edge
with three 3.5 × 16 mm countersunk wood screws per rail, 20, 107.5 and
195 mm back from the front and 5.5 mm in from the wall's outer face,
driven up through the wall from below; each hole is counterbored to 5 mm
under the shelf. These positions are fixed parameters, independent of the
wall and gap sizes.

Seen from below, each lip's front corner is rounded off in a quarter circle
(about 10 mm radius) running from the lip's tip forward to the foot of the
gusset, so the lip's front shrinks back to the wall and gusset; the lip's
lead-in chamfer and nose follow the curve.

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
hull touches it. The plate lies turned a quarter turn, with the rail fronts
towards the bed's right, so the brim pads ahead of them use the bed's
spare length. It sits at x 21–249 mm and y 3.5–252.5 mm, 3 mm clear of the
corner. The build fails if the part gets too big to keep that clearance.
Bambu Studio can re-centre a single STL on import; if it lands at X 128,
set its position to X 135, Y 128 (the Move tool, or the object's position
fields).

ASA warps on long, flat parts like this one. Each rail's front end has a
0.4 mm (two-layer) brim pad on the bed: 8 mm ahead of the front, 8 mm past
the lip's tip, 3 mm past the outer wall (the bed has no more room across)
and 40 mm back along the rail. Since the v7 print also lifted at the back,
each back corner has one too: 6 mm behind the back wall, 3 mm past the
outer wall, 40 mm forward along the rail and 30 mm along the back wall. Where
a pad meets the part it thins to a single 0.2 mm layer for 1.5 mm, so it
peels or snaps off along the part's edge. The pads are part of the plate
model only, so the slicer's own brim can stay off. The slots stay open
through the pads.

Stress-relief slots break up the long runs of solid first layers whose
shrinkage curls the ends up. Each rail has eight 2 mm slots across its
floor, at y ≈ 42, 57, 71, 85, 130, 144, 158 and 173 mm, one under each strut
between the side wall's diamonds and none near the screw bosses or the
front. Each runs from the outer skin to 3 mm short of the lip's tip, right
through the lip, the gusset and the floor under the pocket, so the 26 mm
wide floor becomes short fingers. The 2 mm outer skin, the 3 mm strip along
the lip's tip and the inner skin (a 2 mm bridge over the slot) stay whole,
so the part stays one piece and the lip's bearing edge stays continuous.
The longest unbroken floor is now about 30 mm (at the front end and around
the middle and back bosses) rather than 214 mm. The back wall has seven
2 mm slots up through its foot, 8 mm high with a pointed top, one under
each strut between its diamonds, so its 243 mm foot is broken into short
lengths too. Slot edges are rounded 0.5 mm, bar those on the bed.

The walls are a diamond lattice: square openings on their points, with 45°
sides so they print without supports, their points rounded 1 mm and their
edges rounded 1 mm on the walls' outer and inner faces (the edges inside
the pockets stay sharp, as 2 mm skins have no room for both). Each side
wall has five 11 mm diamonds per pocket, ten a side, through the outer
skin, the pocket and the inner skin, between a 3.5 mm solid band under the
shelf face and the pocket floor; the bosses, the front ends, the floor and
lips, and the back corners stay solid. The back wall has eight 16.5 mm
diamonds, with a strut down the middle, a 3.5 mm top band and a 4 mm foot,
and stays solid for 15 mm beyond each lip's tip. The scale's white top and
back rest on the struts and bands. Slots, lattice and the back corner pads
each have a switch near the top of the script.

For ASA:

- Heat-soak: close the door and the top lid, run the bed at 100–110 °C and
  let the chamber warm for 15–20 minutes before starting (a preheat in
  Studio, or start the print after the soak).
- Keep part cooling low, about 10–20 %, with
  no auxiliary fan, and keep the door and lid shut for the whole print.
- Glue stick on the textured or smooth PEI plate, a thin even coat.
- Leave Studio's brim off; the pads are built in.
- Let the part cool in the closed chamber before taking it off the plate.

It prints standing on its bottom face: the lips lie flat on the bed, the
walls and back wall rise straight up, and the countersinks are at 45°, so
nothing overhangs beyond the bottom 0.3 mm of the 1 mm bed fillets. To keep
it light, each stretch of wall between the screw bosses has a pocket open on
the shelf face (straight up in the print), floored level with the top of the
gusset. A 2 mm outer skin, a 2 mm strip along the inner face that guides the
white top, 15.6 mm solid bosses around the screws, the front ends behind the
lead-in stay solid. That brings the part from about 148 cm³ to 118 cm³,
and the lattice and slots to 104 cm³ (105 cm³ on the plate with the pads);
the carve-out sizes are parameters.
