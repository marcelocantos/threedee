# threedee

Parametric 3D-printable parts, built with [build123d](https://github.com/gumyr/build123d).

The CAD kernel is the pinned `build123d` release in `pyproject.toml`. `uv.lock` pins the rest. `make` runs that interpreter from the worktree `.venv`.

```bash
uv sync     # create .venv and install the lockfile
make        # build the default part set to its export/ directories
make clean  # remove the default build outputs
```

STL and STEP files are gitignored. The default build covers the twelve top-level designs and the trolley key, scale rails, puzzle tray, SSD stand, and mixer stand. The other generators have their own entry points under `projects/ascut/`, `projects/haberdasher/`, and `projects/dissections/`.

Run `make geometry-check` to rebuild the default part set and compare its STEP and STL exports with the pre-refactor baseline. The [independent comparison](docs/geometry-after.json) also covers the separate generators.

Convergence targets live in `bullseye.yaml`. Agent instructions live in `AGENTS.md`.
