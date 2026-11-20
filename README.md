# threedee

Parametric 3D-printable parts, built with [build123d](https://github.com/gumyr/build123d).

The CAD kernel is the pinned `build123d` release in `pyproject.toml`. `uv.lock` pins the rest. `make` runs that interpreter from the worktree `.venv`.

```bash
uv sync     # create .venv and install the lockfile
make        # build every part to export/
make clean  # remove export/
```

STL and STEP files are gitignored. Each part is a standalone script under `projects/`. Shared STL, STEP and viewer calls live in `export_part.py`. Convergence targets live in `bullseye.yaml`. Agent instructions live in `AGENTS.md`.
