# Haberdasher

Dudeney's four-piece dissection of an equilateral triangle into a square, as a tray and four tiles. The coordinates are the compass construction in *The Canterbury Puzzles* (1907), puzzle 26, proved in `geometry.py` and written to `pieces.json`. The same file drives the demo at `marcelocantos.github.io/demos/haberdasher/`.

`print.kerf_mm` insets every tile edge. The fit check is containment in both pockets, not a zero gap.

```bash
python geometry.py          # exact proof
python -m unittest test_haberdasher.py
mkdir -p export && cd export && python ../haberdasher.py --no-preview
```

Exports land in `export/` (gitignored): `haberdasher.stl`, `haberdasher.step`, and the preview PNGs.
