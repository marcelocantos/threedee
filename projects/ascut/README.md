# As-Cut

A measurement log beside a parametric part. The nominal dovetail is the
15° flank from [Inheritance Machining's dovetail box](https://www.youtube.com/watch?v=uQQH8XzlgVU).
The first article measured 14.25°, and one side was 0.020 in past the
common datum, so the design widened 0.040 in. The mate is rebuilt from
those readings. Export refuses a mate that still cites the nominal where
a reading exists.

The thickness gauge is the same rule on a second fixture. The 1.5 mm
step from [the printed setup gauges](https://www.youtube.com/watch?v=uzqiwq_xQHU)
does not export until a calibration reading is in the log, and the solid
uses that reading rather than the label.

```bash
make ascut-oracle
python projects/ascut/ascut.py --out projects/ascut/export
```

`oracle_expect.py` is the sympy referent and does not import build123d.
`frozen_1425.json` is that referent written down. The oracle reads the
exported STEP back and measures face normals and plane gaps. It does not
ask the generator what angle it used.

The flank angle is the signed angle between the flank plane and the
plane that contains the slide axis and the depth axis. Positive widens
the tip. The flank gap is the clearance normal to the flank. Depth, the
nominal neck, and the clearances are model choices; the video does not
give them.
