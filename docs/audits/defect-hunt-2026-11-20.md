# Defect hunt, 2026-11-20

Worktree cut from local `master` (`fa26584`). Product code and existing tests
were not changed. Reproductions ran on 2026-11-21 as Pueue task 1048
(`threedee defect repro 2`, group `default`, exit 0) against temporary
directories and fakes. No printer, device, installed copy, or live home-directory
state was touched. `tools/bambu/creds.py` was not opened.

## What this tree does

threedee builds parametric solids with build123d and writes STL and STEP
(gitignored) through `projects/export_part`. The Bambu helpers flatten Studio
presets, upload a file, start a print, and watch the X1 Carbon over MQTT.
Persistence is the ascut measurement log, frozen sympy expectations,
`pieces.json` cabinet documents, and `docs/geometry-baseline.json`. Nothing
in the repo is a long-running daemon.

## Worst silent failure

A generator or a printer profile that exits successfully while the physical
result is the wrong size, or while the toolhead will run with no filament.
That outranks a crash, a traceback, or a cosmetic mesh. It fixed the reading
order: ascut (measure through cut), printer start and preset flatten, then
fit-critical solids (magnet tube, nailgun tip, catflap, baby-gate latch),
then the dissection certificate, then `geometry_record`.

## Confirmed defects

### A flattened fuzzy-grip machine profile never drops the AMS load template

**Severity.** High. The export succeeds and the project looks ready to slice.
The same omission already produced a mixer-stand start sequence with no AMS
load, so the printer ran every move with an empty toolhead
(`tools/bambu/flatten.py` documents that failure).

**Mechanism.** `flatten` copies the named preset and then only the `inherits`
parent. It never reads `include`. On a Bambu X1 Carbon preset the AMS
`machine_start_gcode` (`M620 S[initial_no_support_extruder]A` and the matching
`M621`) lives in an included template, not in the parent. The flattened JSON
is what `--load-settings` hands to Bambu Studio. Sliced gcode is stripped from
the 3MF afterwards, so the stored presets are the incomplete ones. A cycle in
`inherits` is a `RecursionError`, which is loud; a missing `include` is not.

**Where.** `projects/puzzle-tray/fuzzy_3mf.py` lines 47–52.

**Reproduction.**

```python
import ast, json, tempfile
from pathlib import Path

src = Path("projects/puzzle-tray/fuzzy_3mf.py").read_text()
fn = next(n for n in ast.parse(src).body
          if isinstance(n, ast.FunctionDef) and n.name == "flatten")
root = Path(tempfile.mkdtemp())
base = root / "machine" / "base"
base.mkdir(parents=True)
(base / "parent.json").write_text(json.dumps({
    "name": "parent", "machine_start_gcode": "G28\n"}))
(base / "ams.json").write_text(json.dumps({
    "name": "ams-template",
    "machine_start_gcode": "M620 S[initial_no_support_extruder]A\n"}))
(base / "printer.json").write_text(json.dumps({
    "name": "Bambu Lab X1 Carbon 0.4 nozzle",
    "inherits": "parent", "include": ["ams-template"]}))
index = {}
for f in base.glob("*.json"):
    d = json.loads(f.read_text())
    index[("machine", d["name"])] = d
ns = {"index": index}
exec(ast.get_source_segment(src, fn), ns)
start = ns["flatten"]("machine", "Bambu Lab X1 Carbon 0.4 nozzle")["machine_start_gcode"]
assert start == "G28\n" and "M620 S[" not in start
```

The same tree through `tools/bambu/flatten.py` `load_index` + `resolve` keeps
`M620 S[initial_no_support_extruder]A`. Observed: `fuzzy_start='G28\n'`.

**Smallest fix.** Replace this `flatten` with `tools.bambu.flatten.resolve`
(inherits, then include, then own keys, with the cycle set). Keep that
module's refusal to succeed unless `machine_start_gcode` contains `M620 S[`.

### The magnet tube's radial wall equals the named wall thickness

**Severity.** High. The script names `wall = 1` and the export succeeds. The
floor is 1 mm and the side wall is 0.5 mm, so a tube that looks finished
splits in use.

**Mechanism.** `outer_d = inner_d + wall` adds the thickness once to the
diameter. Radial thickness is `(outer_d - inner_d) / 2`. The floor uses the
same `wall` as a Z offset of the cavity, so the two uses of the name disagree.
The flare is a separate radius (`barrier_r + flare / 2` = 12 mm), which is why
the assembled solid is 24 mm across. That bbox does not measure the tube wall.

**Where.** `projects/magnet_tube.py` lines 10–12 and 34.

**Reproduction.**

```python
from build123d import Align, Cylinder, Pos

wall, inner_d, length = 1, 18, 65
outer_d = inner_d + wall
base = (Align.CENTER, Align.CENTER, Align.MIN)
solid = (
    Cylinder(radius=outer_d / 2, height=length, align=base)
    - Pos(0, 0, wall) * Cylinder(radius=inner_d / 2, height=length, align=base)
)
bb = solid.bounding_box()
radial = (bb.size.X - inner_d) / 2
assert abs(bb.size.X - 19) < 1e-6 and abs(radial - 0.5) < 1e-6
assert radial != wall  # floor still uses wall as 1 mm of Z
```

Observed on the reconstructed body: `bbox_x=19.000000 radial=0.500000`.
A 1 mm wall would be 20 mm across. The exported assembly's 24 mm span is the
flare, measured separately (`size_x=24`, `size_z=65`).

**Smallest fix.** `outer_d = inner_d + 2 * wall`.

### The nailgun tip's closed end is as thick as its side walls

**Severity.** High. Export succeeds. The XY wall is named 1.5 mm. The closed
end is 0.75 mm and the opposite end is open by 0.75 mm, so the tip that
reaches the tool is the thin face.

**Mechanism.** The cavity trapezium has the same depth `D` as the outer shell,
then `Pos(0, Txy / 2, Tz1)` shifts it by half a wall. Width is reduced by
`2 * Txy`, so the X walls are `Txy`. The Y shift leaves `Txy / 2` at the
closed end and pushes the cavity past the far face. The floor (`Tz1`) is a
separate, correct Z offset. `upper_cavity` uses the same `Txy / 2` shift.

**Where.** `projects/nailgun_tip.py` lines 13 and 40.

**Reproduction.**

```python
from build123d import BuildPart, BuildSketch, Polygon, Pos, extrude

W1, W2, D, H, Txy, Tz1, Tz2 = 5, 8.5, 8.5, 5, 1.5, 1.2, 1.7

def trap(w1, w2, d, h):
    pts = [(w1 / 2, -d / 2), (w2 / 2, d / 2), (-w2 / 2, d / 2), (-w1 / 2, -d / 2)]
    with BuildPart() as p:
        with BuildSketch():
            Polygon(pts)
        extrude(amount=h)
    return p.part

outer = trap(W1, W2, D, H)
inner = Pos(0, Txy / 2, Tz1) * trap(W1 - 2 * Txy, W2 - 2 * Txy, D, H - Tz1 - Tz2)
closed = inner.bounding_box().min.Y - outer.bounding_box().min.Y
assert abs(closed - Txy / 2) < 1e-6
assert inner.bounding_box().max.Y > outer.bounding_box().max.Y + 0.5
```

Observed: `closed_wall=0.7500`, `inner_y=-3.500..5.000`, `outer_y=-4.250..4.250`.
The exported STEP is `x=±4.250 y=±4.250 z=0..5`, volume 176.99 mm³.

**Smallest fix.** Offset the cavity by `Txy` on Y and shorten its depth by
`Txy`, so one end stays open with a full wall and the other stays closed at
`Txy`. If both ends should be closed, shorten by `2 * Txy` and do not shift.

### The catflap camera bore and square sit where the OpenSCAD port places them

**Severity.** High. The housing exports and the camera features exist, shifted.
A bore 3.5 mm off along its axis, and a square recess moved by half its size,
miss the camera they were cut for.

**Mechanism.** The file is a statement-for-statement port of `catflap-rpi.scad`.
OpenSCAD `cylinder` sits on its base and `cube` grows from a corner. build123d
`Cone` and `Box` are centered on every axis unless `align` says otherwise.
`camera_bore` is `Pos(0, 0, -7.5) * Cone(..., height=7)` with no align, so the
cone is centered on that point and moves by `height / 2`. `camera_sq` is
`Pos(0, 0, -3.5) * Box(9, 9, 1)`, centered, so it straddles the origin instead
of occupying a 9×9×1 corner box. The same file already compensates elsewhere:
USB cuts add half-extents, and the camera screws use `CENTER_MIN`. The bore
and the square do not.

**Where.** `projects/catflap_rpi.py` lines 84–89.

**Reproduction.**

```python
from build123d import Align, Box, Cone, Pos

height = 7
centered = Pos(0, 0, -7.5) * Cone(bottom_radius=10.5 / 2, top_radius=7.7 / 2, height=height)
based = Pos(0, 0, -7.5) * Cone(
    bottom_radius=10.5 / 2, top_radius=7.7 / 2, height=height,
    align=(Align.CENTER, Align.CENTER, Align.MIN),
)
shift = centered.bounding_box().center().Z - based.bounding_box().center().Z
assert abs(abs(shift) - height / 2) < 1e-6  # observed center_shift=-3.500
sq = Pos(0, 0, -3.5) * Box(9, 9, 1)
assert sq.bounding_box().min.X < 0  # observed x=-4.500..4.500, z=-4.000..-3.000
```

A base-aligned cone is `z=-7.500..-0.500`. A corner-aligned square at the same
`Pos` is `x=0..9`, `z=-3.5..-2.5`.

**Smallest fix.** `align=(Align.CENTER, Align.CENTER, Align.MIN)` on the cone.
Give the square the corner align the rest of the port uses for cubes, or add
the half-extents the USB cuts already add.

### A translation is never certified clear while the piece overlaps another

**Severity.** Medium. The published perigal, greek-cross, and rectangle-square
motions did not overlap at 64 intermediate stations, so this is not a puzzle
that currently collides. It is a hole in the proof the tests trust: a sweep
can pass through another piece between the nine samples and still be accepted.

**Mechanism.** `_segment_clear` tests a translation only at `t = k/8` for
`k` in `0..8`. Overlap on the open interval between those stations is invisible.
The existing tests call `_overlaps` on endpoints. Half-turns use a disk test
instead of this sampler.

**Where.** `projects/dissections/cabinet.py` lines 228–233.

**Reproduction.**

```python
import sys
from pathlib import Path
sys.path.insert(0, "projects/dissections")
import cabinet
from sympy import Rational as F

moving0 = ((0, 0), (F(1, 10), 0), (F(1, 10), 1), (0, 1))
moving1 = ((2, 0), (F(21, 10), 0), (F(21, 10), 1), (2, 1))
obstacle = ((F(9, 10), 0), (F(19, 20), 0), (F(19, 20), 1), (F(9, 10), 1))
cabinet._segment_clear(moving0, moving1, 0, [obstacle])  # does not raise
hit = next(
    F(k, 4000) for k in range(4001)
    if cabinet._overlaps([cabinet._lerp(moving0, moving1, F(k, 4000)), obstacle])
)
assert hit == F(1601, 4000)
```

The bar of width 0.1 travelling from x=0 to x=2 overlaps x∈[0.90, 0.95] for
`t` in (0.40, 0.475). Samples land on 0.375 and 0.500. Dense check hits at
1601/4000.

**Smallest fix.** Certify a translation by an exact sweep (separating axis of
the relative motion, or interval overlap of every vertex against every edge),
not by nine stations.

### The print monitor never exits successfully when the job state is FAILED

**Severity.** Medium. A watcher used as a gate reports success for a failed
print. The log line says `terminal state FAILED`, and the process status
says the opposite.

**Mechanism.** `FINISH` and `FAILED` are both terminal. After the hold elapses,
`main` breaks out of the loop and returns 0 for either state. The reproduction
stubbed `creds` and `paho.mqtt.client` (no socket was opened) and delivered
one report, `{"print": {"gcode_state": "FAILED", "mc_percent": 12}}`.

**Where.** `tools/bambu/monitor.py` lines 24 and 136.

**Reproduction.** Stub `sys.modules["creds"]` with a fake access code, IP
`127.0.0.1`, and serial, and stub `paho.mqtt.client.Client` so `loop_start`
calls `on_connect` then `on_message` with that payload. Then:

```python
import monitor
code = monitor.main(["--interval", "0", "--hold", "0", "--max-hours", "0.02"])
assert code == 0  # observed; the log said "terminal state FAILED held; exiting"
```

**Smallest fix.** Return 1 when the held state is `FAILED`, and 0 only for
`FINISH`.

### status never exits successfully when the printer sent no report

**Severity.** Medium. A caller that checks the exit code treats an empty query
as a live printer. Every field is `None` and the process still returns 0.

**Mechanism.** `main` waits until `ams` is present or 25 seconds pass, then
prints `got` and returns 0 either way. With `time.time` advanced by 100
seconds per call and a client that delivers no payload, the wait ends
immediately and the printed dict is all `None`. `creds` and MQTT were stubbed;
nothing was contacted.

**Where.** `tools/bambu/status.py` lines 49–77.

**Reproduction.** Same stubs as the monitor, with `Client.loop_start` not
delivering a payload, and `status.time.time` returning `n * 100`.

```python
import status
assert status.main([]) == 0  # observed, with gcode_state None and no ams
```

**Smallest fix.** Return 1 when `ams` never arrived. Print the partial dict
on stderr if it is useful, and do not return 0.

### The AMS-load check never accepts a different M620 code

**Severity.** Medium-low. A false pass disables the check that refuses to
start a print whose plate gcode has no real AMS load. `M620 S0A` is the load;
`M620 S0AB` is a different command and is accepted.

**Mechanism.** `has_ams_load` strips the comment (so `; M620 S0A` is correctly
rejected) and then tests `"M620 S0A" in code`. Any longer token that starts
with that text matches. The check runs only when the path is a local file.

**Where.** `tools/bambu/send.py` lines 25 and 43–47.

**Reproduction.**

```python
import ast
from pathlib import Path
src = Path("tools/bambu/send.py").read_text()
fn = next(n for n in ast.parse(src).body
          if isinstance(n, ast.FunctionDef) and n.name == "has_ams_load")
ns = {"AMS_LOAD": "M620 S0A"}
exec(ast.get_source_segment(src, fn), ns)
has = ns["has_ams_load"]
assert has("M620 S0AB\n") is True   # observed
assert has("M620 S0A\n") is True
assert has("; M620 S0A\n") is False
```

**Smallest fix.** Match a whole token, for example a line whose code part
matches `^M620 S0A$`.

### Monitor timestamps name the abbreviation the Melbourne clock is actually on

**Severity.** Low. The instant is right and the label is wrong for half the
year. A log from July says AEDT, which is the summer abbreviation.

**Mechanism.** `ts` formats `Australia/Melbourne` and then appends the literal
`AEDT`. In July that zone's `%Z` is `AEST`. The November run of this hunt
printed a correct `AEDT` only because the clock was on daylight time.

**Where.** `tools/bambu/monitor.py` line 28.

**Reproduction.**

```python
from datetime import datetime
from zoneinfo import ZoneInfo
winter = datetime(2026, 7, 15, 12, 0, tzinfo=ZoneInfo("Australia/Melbourne"))
assert winter.strftime("%Z") == "AEST"
```

**Smallest fix.** Use `%Z` (or `tzname()`) instead of the literal suffix.

## Unconfirmed suspicions

1. **Nailgun side slot.** `Pos(0, 1, H / 2) * Box(10, S1, S2)` is centered, so
   the box spans x=−5..5 and opens both side walls of a part that is only
   ±4.25 mm wide. Cut volume against `outer - inner` was 22.165 mm³. A
   MIN-aligned box at the same `Pos` would span x=0..10. `x=0` and `z=H/2`
   also read as a deliberate centre. No drawing says which. Not filed above.

2. **Half-turn clearance on a concave obstacle.** `_strict_outside` is a
   half-plane test, and `_disk_clears` trusts it. Haberdasher pockets are
   convex. Greek-cross pieces can be concave. No concave fixture was run, and
   the published half-turns were not shown to collide.

3. **FTP `STOR` injection.** `tools/bambu/ftp.py` line 58 sends
   `"STOR " + name` with the remote name unsanitized. A name containing
   `\r\n` could inject FTP commands. Not executed. The real printer was not
   contacted.

4. **Monitor after disconnect.** `on_disconnect` logs and does not clear
   `got`, so a later line can repeat the last state. Not simulated.

5. **`got` written from the MQTT thread.** `monitor` and `status` update the
   dict from `on_message` while the main thread reads it. No torn-read demo.

6. **ascut STEP-then-STL.** `export_all` resolves both logs before writing. A
   crash between the STEP write and the STL write leaves a mixed directory.
   Not executed. The process would be non-zero, so this is not a silent success.

7. **Baby-gate `span` margin.** The span is increased by 2 mm (86.5 → 88.5)
   with no drawing in the file. Not shown to miss a fit.

8. **Rotary bearing pin radius.** With no centre hole the formula
   `bearing_od/2 - center_hole_diam/2 - adjust` is about −54 mm. The absolute
   value differs by `2 * adjust` from `center/2 - bearing/2 - adjust`. The
   shipped call has `crosshairs=False`, so the quadrant comment is dead. No
   spec, not measured as a failed part.

9. **Screw-box chamfer.** `Pos(h, r, 0) * Rot(0, 0, 45) * Box(c, c, 4)` is
   centered. Not measured.

10. **Triton lifter hex.** The across-flats expression is about 9.83 mm against
    a nominal 10 mm. The file was not read in full and the solid was not built.

11. **`tools/bambu/light.py` empty ack.** After the wait it always returns 0,
    including when `ack` is still empty (lines 65–72). Same shape as `status`.
    Read, not run, so it is not in the confirmed list.

## Checked, and not defects

- Baby-gate countersunk holes with `Rot(0, 90, 0)` remove 413.51 mm³ from the
  base (a two-shaft estimate is about 318 mm³). `Rot(0, -90, 0)` removes 0.
  The tip cylinder's bbox is Y −0.000..11.500, on the stem, not on −Y. The
  exported STEP contains cylinder radii 2.25 and 5.0.
- Magnet assembly bbox of 24 mm is the flare (radius 12), not evidence against
  the 0.5 mm wall.
- Scale-rails `rail -= A - B` is `rail - (A - B)`. It clears the lip corner.
  It does not add `A`.
- Greek-cross kerf insets stay inside their rings. `tiles_fit` was true and
  the leak list was empty. Both arrangements in `pieces.json` are CCW, as are
  the haberdasher outlines.
- `geometry_record.check` fails a bbox on any delta greater than 0. A 1 mm
  occupancy cell cannot hide a size change that moves the bbox.
- ascut refuses an in-band citation that is not the reading itself. Flank
  faces with `|n.y| < 0.05` or `|n.x| < 0.05` raise, they do not export.
- `send.py` skipping the AMS check for a non-local path is the documented
  remote-name path.
- LED stumps are centered as a pair of equal cylinders. The shape is the tube.
  Slicer placement on the bed is outside the solid.
- `snap.py` returns 1 on timeout, a nonzero ffmpeg status, or an empty file.

## Coverage

Read in full: `projects/ascut/` (`measure.py`, `dovetail.py`, `gauge.py`,
`log.py`, `oracle_expect.py`, `ascut.py`, `section_svg.py`, and
`test_ascut_oracle.py`); `projects/haberdasher/geometry.py`, `haberdasher.py`,
`test_haberdasher.py`; `projects/dissections/cabinet.py`, `tray.py`,
`test_cabinet.py`; `tools/geometry_record.py`; `projects/baby_gate_latch.py`,
`nailgun_tip.py`, `catflap_rpi.py`, `magnet_tube.py`, `led_stumps.py`,
`starlock_holders.py`, `machinist_square_mount.py`, `bosch_adapter.py`,
`rotary_bearing.py`, `screw_box_partitions.py`; `projects/puzzle-tray/fuzzy_3mf.py`;
`projects/scale-rails/scale_rails.py`; `tools/bambu/flatten.py`, `send.py`,
`ftp.py`, `monitor.py`, `status.py`, `light.py`, `snap.py`.

Read in part: `projects/puzzle-tray/puzzle_tray.py` from line 180;
`projects/mixer-stand/mixer_stand.py` through line 180;
`projects/express-1m2-stand/express_1m2_stand.py` through line 120.
`router_bit_rack.py`, `triton_lifter.py`, and `trolley-key/ring_hook.py` were
only grepped. `tools/bambu/creds.py` was left unread on purpose.
