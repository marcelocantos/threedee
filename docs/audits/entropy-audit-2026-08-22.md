# Entropy audit — threedee

Date: 2026-08-22
Mode: full (entropy + hygiene)

## Executive summary

- **Snapshot:** `/Users/marcelo/work/github.com/marcelocantos/threedee`, branch `master`, commit `467a5c3f7a5bd01005396d384d91590627fffb6f` (`push/move targets yaml to bullseye yaml remove targets  (#1)`).
- **Initial dirty state:** clean. `git status --porcelain=v1 -b` was `## master...origin/master` with no staged, unstaged, or untracked (non-ignored) files. Ignored working-tree residue includes `export/`, root `*.stl`/`*.step`/`*.3mf`, `.DS_Store`, and `.vscode/launch.json`.
- **Scope:** tracked source (`projects/*.py`, root `*.scad`, `Makefile`, `CLAUDE.md`, `bullseye.yaml`, `.gitignore`). Gitignored print/build artifacts were inspected only as evidence of the live print path, not as source.
- **Headline mechanism:** the repo declares a build123d Python workflow (`projects/` → `make` → `export/`) while still tracking a complete OpenSCAD tree that the on-disk print jobs still name as “OpenSCAD Model”. The Python ports mix builder mode with discarded algebra locations and OpenSCAD-incompatible default alignment, so several declared-source parts do not reproduce the printable originals. Nothing in CI or tests would notice.
- **Highest-consequence findings:** ENT-001 (two CAD sources of truth), ENT-002 (BuildPart + discarded `Pos * Shape` collapses rails/ribs/holes), ENT-003 (magnet-tube barrier not on the tube), ENT-004 (catflap double camera offset), ENT-005 (undeclared, unpinned CAD kernel).
- **Unverified residue:** live boolean rebuild of every part against OpenSCAD; manifold/printability; whether Bambu `.3mf` meshes still match current `.scad`; `make` itself was not run (it writes `export/`).

## Scope and exclusions

Included:

- 12 Python part scripts under `projects/`
- 13 tracked OpenSCAD files (12 parts + vendored `gears.scad`)
- `Makefile`, `CLAUDE.md`, `bullseye.yaml`, `.gitignore`
- Git history on `master` and the leftover local branch `push/move-targets-yaml-to-bullseye-yaml-remove-targets-` (pre-squash migration commits)

Named exclusions (not silent omissions):

- `export/` — gitignored Makefile output (stamps dated 2026-04-06; treated as stale auxiliary artifacts)
- Root `*.3mf`, `*.gcode.3mf`, `*.stl`, `*.step` — gitignored slicer/print meshes
- `gears.scad` (1350 lines, third-party involute library) — license and redundancy only, not style
- No `.github/`, no tests, no `pyproject.toml`, no `LICENSE`, no `README`, no `AGENTS.md`, no `hygiene.yaml`, no `docs/targets.md`, no `docs/TODO.md`

Languages analyzed: Python (companion `python.md` read), Makefile/shell (`bash.md` read). OpenSCAD has no companion file. Go, C++, Rust, SQL, web, and journeys do not apply.

## Commands run

| Command | Version / result | Path | Limitations |
|---|---|---|---|
| `git status --porcelain=v1 -b`; `git rev-parse HEAD`; `git log`; `git ls-files` | git 2.55.0; HEAD `467a5c3f`; clean `master` tracking `origin/master` | shipped meta | None for snapshot identity |
| `gh repo view`; `gh pr view 1`; `gh api …/.github` | gh 2.97.0; public repo, `licenseInfo: null`, PR #1 squash-merged 2026-07-11; `.github` 404 | remote meta | Auth’d `gh` only |
| `python3 -m py_compile projects/*.py` | Python 3.13.0 (`~/.py`); exit 0 | auxiliary syntax | Does not execute CAD or export |
| Live `build123d` probes of port snippets (no file writes) | build123d `0.10.1.dev310+ge8cae0660`; py_gearworks `0.0.18` | auxiliary | Re-ran the same constructors as source; not `make` |
| Binary STL bbox of `export/*.stl` and root `baby-gate-latch.stl` | used only where it matched live probes | auxiliary / stale | Export stamps older than current `.py` mtimes; baby-gate export bbox does **not** match current source |
| `zipfile` listing of gitignored `*.3mf` | BambuStudio and “OpenSCAD Model” metadata | print-path evidence | Meshes not geometrically compared |
| `openscad --version` | OpenSCAD 2021.01 present | unused | SCAD was not rebuilt |
| `make --version` | GNU Make 3.81 | unused | **`make` not executed** (writes `export/`) |
| `uv --version` | uv 0.6.14 | n/a | Repo does not invoke uv |
| `/Users/marcelo/.claude/skills/hygiene/hygiene_check.py` | exit 1, `FileNotFoundError: …/hygiene.yaml` | hygiene | No posture file; not initialized |

No clone detector, linter, or type checker is configured. None were installed.

## Observed architecture

```
declared:  projects/*.py  --make-->  export/{name}.stl,.step
observed:  *.scad  (+ BOSL2, gears.scad)  -->  root *.3mf (Bambu/OpenSCAD)
           projects/*.py  (build123d, py_gearworks, optional ocp_vscode)
```

**Entry points.** Each `projects/*.py` is a script: construct a solid, `export_stl` / `export_step`, optionally `ocp_vscode.show`. `Makefile` discovers `projects/*.py` and runs `cd export && python ../$<`. There is no package, no shared library, no CLI, no tests.

**Declared rules** (`CLAUDE.md`) that match observation:

- One Python file per part; hyphenated export names; no epsilon in Python; optional VS Code preview.

**Declared rules contradicted or omitted:**

- Structure lists `projects/`, `export/`, and `docs/targets.md`. Tracked CAD also includes 13 `.scad` files at repo root. `docs/targets.md` and `docs/TODO.md` do not exist; targets live in `bullseye.yaml`.
- Convention: “Use build123d's algebra API (`+`, `-`, `&`)”. Several ports use `BuildPart` and then write `Pos(...) * Shape(...)` without `add()`, which does not locate the solid (ENT-002).
- Delivery “Merged to master” matches GitHub default branch.

**Inferred (from code and history, not docs):**

- Intent of PR #1 (squash of local commits `68c2d3c`…`341d342`) was to migrate OpenSCAD → build123d. Bullseye T1.2–T1.4 context says the ports are “Complete”. The OpenSCAD tree was not removed.
- Print workflow on this machine is still OpenSCAD/Bambu: `baby-gate-latch.3mf`, `machinist-square-mount.3mf`, `nailgun-tip.3mf` embed object name `OpenSCAD Model`; `catflap-rpi.3mf`, `magnet-tube.3mf`, `screw-box-partitions.3mf` are BambuStudio projects.

**Unknown intent (owner judgment):** whether `.scad` is frozen reference, still the printable source, or leftover. `CLAUDE.md` does not say.

Dependency direction: each Python script → `build123d` (undeclared); `triton_lifter.py` additionally → `py_gearworks` (undeclared). No intra-repo imports; no cycles. OpenSCAD parts `include <BOSL2/std.scad>` (unvendored) or `include <gears.scad>` (vendored CC-BY-NC-SA).

## Dimension vector

| Dimension | State | Evidence summary | Change from baseline |
|---|---|---|---|
| Architecture topology | concern | Declared Python/Makefile tree; observed dual CAD trees; mixed builder/algebra against a written algebra-only convention | n/a (first audit) |
| Redundancy / sources of truth | critical | 12 parts exist as `.scad` + `.py`; print `.3mf` still named OpenSCAD; `gears.scad` vs `py_gearworks`; CLAUDE vs `bullseye.yaml` | n/a |
| Change amplification | concern | A dimension change must be edited in two languages or the trees drift (already have); export/preview copied 12 times | n/a |
| Local code quality | concern | Discarded `Pos * Shape` inside `BuildPart`; dead `box_part`; unused `sqrt`; comments that do not match code | n/a |
| Correctness / verification | critical | `py_compile` only; no tests/CI; live probes show unprintable ports (starlock, screw-box, router lattice, magnet barrier, catflap offset) | n/a |
| Security / dependencies | concern | No lockfile; CAD kernel is a git-describe build; public repo; Apache headers vs CC-BY-NC-SA `gears.scad`; GitHub `licenseInfo: null` | n/a |
| Build / release / operations | concern | `make` is the shipped path but uses unpinned `python`; no CI; `make` not re-run this audit | n/a |
| Documentation / governance | concern | Stale `CLAUDE.md` paths; bullseye items `identified` + `acceptance: TODO` while context claims complete; no README/LICENSE/AGENTS.md | n/a |

Do not aggregate these into a score.

## Findings

### ENT-001: OpenSCAD and build123d are both live sources of truth

- **Priority:** P1
- **Dimensions:** Redundancy / sources of truth; Architecture topology; Change amplification
- **Status:** observed fact (two tracked trees); inference (print path still OpenSCAD)
- **Evidence:**
  - Tracked: 13 `*.scad` (12 parts + `gears.scad`) and 12 `projects/*.py` (`git ls-files`).
  - `CLAUDE.md:7-10` documents only `projects/`, `export/`, and `docs/targets.md`.
  - Gitignored `baby-gate-latch.3mf` object name `OpenSCAD Model`; same string in `machinist-square-mount.3mf`, `nailgun-tip.3mf`, and `screw-box-partitions.3mf` plate JSON. `catflap-rpi.3mf` / `magnet-tube.3mf` are BambuStudio 02.01.01.52 projects.
  - Root `baby-gate-latch.stl` bbox span x=113.50 matches current Python **and** OpenSCAD (live `baby_gate_latch(86.5)` + translated span-100 compound size `(113.5, 100, 10)`). That is the OpenSCAD-era mesh sitting beside `export/baby-gate-latch.stl` (span x=51.71, **not** current Python).
  - History: `.scad` last touched 2025-06-05 … 2025-07-23; all Python added in squash `467a5c3` (2026-07-11). No commit deletes SCAD.
- **Mechanism:** a fit dimension (hole, span, tooth) can be changed in one language and not the other. Print jobs consume the OpenSCAD-named meshes; `make` consumes Python. The two outputs are already different (ENT-002–004).
- **Blast radius:** every part; any future edit; anyone cloning the repo and running `make` instead of opening `.scad`.
- **Counterevidence checked:** bullseye T1.2–T1.4 context calls the ports “Complete”, which would justify deleting or quarantining SCAD — it was not done. Independent parts (no shared Python module) are a healthy exception, not a reason to keep two CAD languages.
- **Smallest coherent remediation:** pick one printable source. If Python: move `.scad` to `legacy/` or delete after golden comparison. If SCAD: stop documenting Python as the structure. Record the choice in `CLAUDE.md`.
- **Verification:** a check that either (a) no tracked `*.scad` remain outside a named legacy path, or (b) docs explicitly freeze SCAD and CI builds Python against golden bboxes.
- **Ratchet candidate:** file rule `*.scad` absent at repo root, or a documented `legacy/` exception in hygiene.

### ENT-002: `Pos * Shape` inside `BuildPart` drops the location — rails, ribs, and holes collapse

- **Priority:** P1
- **Dimensions:** Correctness / verification; Local code quality; Architecture topology
- **Status:** observed fact (live constructors + volume/bbox)
- **Evidence:**
  - Convention `CLAUDE.md:21-22` requires the algebra API. These files mix `with BuildPart()` and un-`add`ed `Pos * Shape`:
    - `projects/starlock_holders.py:23-45` — `Pos(x, 0, -rail_h / 2) * Cone(..., mode=Mode.SUBTRACT)` for holes; nested `BuildPart` + `Pos(x, 0, 0) * Cylinder(...)` for stems; `Pos(x, 0, tab_h / 2) * Box(...)` for tabs. Live holder bbox z `(-12.5, 29.2)` (centered tab at origin). Stems/holes do not walk `stem_spacing`.
    - `projects/screw_box_partitions.py:24-49` — `Pos * Rot * Cylinder` rib, `Pos * Rot * Box(..., mode=Mode.SUBTRACT)` chamfers, `Pos * Cylinder(..., mode=Mode.SUBTRACT)` drain grid. Live bbox size `(40, 49, 49)`: cylinder extruded along **Z** for height `w=49` instead of along Y.
    - `projects/router_bit_rack.py:58-103` — `Pos * Box` for every rib/beam (no `add`); `add(Pos * Rot * cyl)` only for slots. Ribs-only live volume **6228** vs ~7e4 expected for a 10×10 lattice; bbox is a full-width × full-height slab because unlocated bars already have size `(grid_width, grid_height, strut_height)`.
  - Auxiliary probe: `Pos(0, 10, 0) * Box(...)` then `Pos(0, 50, 0) * Box(...)` inside `BuildPart` yields **one** box at the origin, volume 200. `Pos * Cone(..., mode=Mode.SUBTRACT)` matches an unlocated origin cone, not the `Pos`.
  - `projects/starlock_holders.py:41` comment claims a fillet/sphere-cap approximation; there is no `fillet` or minkowski sphere (SCAD `starlock-holders.scad:33-36` uses both).
- **Mechanism:** in builder context, `Shape()` registers an unlocated solid; the `Location * Shape` result is discarded unless passed to `add()`. Every loop iteration stacks another copy at the origin. The part still “builds”, so `make` is green.
- **Blast radius:** starlock holders, screw-box partitions, router-bit rack — three of twelve parts, all mechanical fixtures. Pattern can recur in any new `BuildPart` port.
- **Counterevidence checked:** `projects/bosch_adapter.py:57-80` uses `add(located_shape)` and `align=Align.MIN` and does not show this failure mode. `projects/router_bit_rack.py:75,94-100` correctly `add()`s the slot cylinders — only the beam lattice is wrong. Assignment `cyl = Cylinder(...)` before `add(Pos * cyl)` is the safe half of that file.
- **Smallest coherent remediation:** rewrite those three in algebra-only (as `CLAUDE.md` already requires), or wrap every located solid in `add(..., mode=...)`. Do not “fix” with more builder sugar.
- **Verification:** bbox/volume golden tests vs current OpenSCAD (or vs measured hardware). Starlock z-span must not be 41.7 from a centered origin tab; screw-box z-span must be ~1.4 not 49; router lattice volume must be lattice-scale, not 9e3.
- **Ratchet candidate:** a unit test per part with frozen bbox min/max/volume; optionally a ruff/semgrep rule forbidding `Pos *` whose result is unused inside `BuildPart`.

### ENT-003: Magnet-tube barrier is not on the tube (default `Cylinder` is centered)

- **Priority:** P1
- **Dimensions:** Correctness / verification
- **Status:** observed fact
- **Evidence:**
  - OpenSCAD `magnet-tube.scad:9-27`: `cylinder(h=L, d=OD)` is z=0…65; barrier `translate([0,0,50])`.
  - Python `projects/magnet_tube.py:15-31`: `Cylinder(...)` with default alignment. Probe `Cylinder(1, 10)` bbox z=-5…5. Tube therefore occupies z=-32.5…32.5; barrier is placed at z=50…61, **17.5 mm above the tube**.
  - Live magnet bbox z=-32.5, size z=93 (tube 65 + floating barrier to 60.5). Cavity `Pos(0, 0, wall) * Cylinder(...)` is also centered, so the bore is not the SCAD bore.
  - `projects/led_stumps.py:15` uses the same default centering, which **matches** `led-stumps.scad:9` (`center=true`). The magnet port needed `align=Align.MIN` and did not get it.
- **Mechanism:** OpenSCAD `cylinder(h=)` is min-aligned; build123d `Cylinder` is centered. Copying SCAD numeric `z=50` without copying alignment disconnects a feature that must sit on the wall.
- **Blast radius:** magnet-tube only as written; any future port of a non-centered SCAD cylinder.
- **Counterevidence checked:** `projects/bosch_adapter.py:51-55` and `projects/nailgun_tip.py` helpers set `Align.MIN` or extrude from a sketch at z=0. Magnet-tube is algebra-only (good) but still wrong.
- **Smallest coherent remediation:** `align=Align.MIN` on tube, cavity, and barrier cylinders/cones (or `Pos(0,0,length/2)` with documented centering).
- **Verification:** bbox z=0…66 (tube+barrier), and a section at z=50 that intersects the tube wall.
- **Ratchet candidate:** golden bbox for `magnet-tube` (z min ≥ -0.1, z max ≈ 66).

### ENT-004: Catflap outer shell is shifted twice by `cam`

- **Priority:** P1
- **Dimensions:** Correctness / verification; Local code quality
- **Status:** observed fact (outer shell); inference (port cutouts relative to Pi)
- **Evidence:**
  - SCAD `catflap-rpi.scad:26-30`: `translate([-cam, 0, 0])` once, `cam = 26`.
  - Python `projects/catflap_rpi.py:31-37` builds `box_part` and never uses it.
  - `projects/catflap_rpi.py:39-43` places `RectangleRounded` at Locations x = `-cam/2 + (box_l-0.5)/2 - (box_l-0.5+cam)/2` = `-cam`.
  - `projects/catflap_rpi.py:54` then `outer = Pos(-cam, 0, 0) * box_outer.part`.
  - Live outer bbox min x=**-110.05**, size x=116.1. SCAD expected x ≈ -26.4 … 90.5 (span ~116.9). Same span, origin wrong by one camera width plus centering.
- **Mechanism:** leftover rewrite: first attempt (`box_part`) abandoned; second attempt encoded `-cam` in the sketch and again on the part. USB/RJ45 cuts in `projects/catflap_rpi.py:102-114` are positioned in the unshifted box frame, so ports will not line up with the shell.
- **Blast radius:** one enclosure (RPi + camera). A printed Python export would not fit the Pi/camera layout that the SCAD 3mf was sliced for.
- **Counterevidence checked:** subsequent features (standoffs, camera bores) use the same coordinate mix; not a single unused helper. Dead `box_part` is the trail of the double offset.
- **Smallest coherent remediation:** delete `box_part`; apply `Pos(-cam, 0, 0)` **or** Locations, not both; align cuts to the same origin as SCAD (`translate([-cam,…])` then min-aligned cubes).
- **Verification:** bbox min x ≈ -26.4; standoff centers at SCAD `inset`/`right`/`top` in that frame.
- **Ratchet candidate:** golden bbox + four standoff-hole point samples.

### ENT-005: CAD toolchain is undeclared and unpinned

- **Priority:** P1
- **Dimensions:** Build / release / operations; Security / dependencies
- **Status:** observed fact
- **Evidence:**
  - No `pyproject.toml`, `requirements.txt`, `uv.lock`, or `Pipfile` (`ls` / `git ls-files`).
  - `Makefile:7` runs `python ../$<`, not `uv run`. Global `python.md` requires uv as the sole Python manager.
  - Import graph: every script `from build123d import *`; `projects/triton_lifter.py:9-11` `from py_gearworks import BevelGear`. Optional `ocp_vscode`.
  - This machine: build123d **`0.10.1.dev310+ge8cae0660`** (git-describe, not a release), py_gearworks `0.0.18`, Python 3.13.0 from `~/.py`.
  - GitHub: no `.github/workflows`; `gh api repos/marcelocantos/threedee/contents/.github` → 404.
- **Mechanism:** `make` succeeds only if the operator’s global interpreter happens to have the same in-development CAD kernel. A rebuild in CI or on another Mac cannot reproduce ENT-002–004 fixes or current geometry. `python` on stock macOS is not even guaranteed to be 3.x.
- **Blast radius:** all twelve parts; any clone; any future `py_gearworks` API break on triton-lifter.
- **Counterevidence checked:** `py_compile` is green here because the packages are installed globally — that is not a repo contract. `ocp_vscode` is correctly optional (`try/except ImportError` in each script).
- **Smallest coherent remediation:** `pyproject.toml` with pinned `build123d` **release** and `py_gearworks`; Makefile `uv run --project . python ../$<` (or a small `uv run` wrapper). Do not invent TOML beyond the standard Python project file.
- **Verification:** clean `uv sync` in an empty venv, then `make` produces twelve STL files.
- **Ratchet candidate:** `command: uv run python -c "import build123d, py_gearworks"` and a CI job that runs `make`.

### ENT-006: Public repo publishes mixed licenses with no LICENSE file

- **Priority:** P2
- **Dimensions:** Security / dependencies; Documentation / governance
- **Status:** observed fact
- **Evidence:**
  - All 12 Python files: `SPDX-License-Identifier: Apache-2.0` (e.g. `projects/magnet_tube.py:1-2`).
  - `gears.scad:45`: “Creative Commons - Attribution, Non Commercial, Share Alike” (Dr Jörg Janssen, v2.2). Still tracked; `triton-lifter.scad:1` `include <gears.scad>`.
  - No root `LICENSE`. `gh repo view --json licenseInfo` → `null`. Repo is public (`isPrivate: false`).
- **Mechanism:** GitHub will not classify the repo; Apache-2.0 headers cannot describe `gears.scad`. CC-BY-NC-SA is not OSI-open and is copyleft-NC. Anyone redistributing the GitHub zip gets NC code plus Apache claims.
- **Blast radius:** the public GitHub tree; downstream if parts are shared. Triton’s Python path uses `py_gearworks` (separate dependency), so the NC library is not required for the declared Python build — it is still shipped.
- **Counterevidence checked:** Python ports do not copy `gears.scad` tooth math; they call `BevelGear`. That removes a derivation concern for the `.py` files; it does not remove the vendored file from the repo.
- **Smallest coherent remediation:** add `LICENSE` matching the intended Python license; delete or `legacy/`-isolate `gears.scad` with its CC notice if SCAD is retired (ENT-001, ENT-009).
- **Verification:** GitHub license detection; `git ls-files '*.scad'` no longer includes the CC-BY-NC-SA library, or a `NOTICE` lists it.
- **Ratchet candidate:** `file: LICENSE` plus hygiene `docs.license`.

### ENT-007: Instruction and bullseye records describe a tree that does not exist

- **Priority:** P2
- **Dimensions:** Documentation / governance
- **Status:** observed fact
- **Evidence:**
  - `CLAUDE.md:10` — `docs/targets.md`. File absent; targets are `bullseye.yaml`.
  - `CLAUDE.md:30-32` — `docs/TODO.md`. File and `docs/` were absent at audit start.
  - No `AGENTS.md` (project instructions exist only as `CLAUDE.md`).
  - No `README`.
  - `bullseye.yaml`: T1.1–T1.4 all `status: identified`, `acceptance: ['TODO']` (`bullseye.yaml:3-8`, `13-18`, `23-28`, `33-38`).
  - `bullseye.yaml:39` still says triton-lifter “simplified bevel gear … box-cut gaps rather than true involute”. Code `projects/triton_lifter.py:5-11` and squash commit `59c0536` (`use py_gearworks for proper involute bevel gears`) contradict that sentence. Status remains `identified`.
- **Mechanism:** agents and humans following `CLAUDE.md` look for files that are gone. Bullseye cannot ratchet: everything is still `identified` after a merge that claimed the ports complete.
- **Blast radius:** future agent sessions; target hygiene; anyone cloning without tribal knowledge of `make` + global `~/.py`.
- **Counterevidence checked:** PR #1 body lists “Move targets.yaml to bullseye.yaml, remove targets.md” — the move happened; `CLAUDE.md` was not updated in the same squash (`git show 467a5c3:CLAUDE.md` still has `docs/targets.md`).
- **Smallest coherent remediation:** point `CLAUDE.md` at `bullseye.yaml`; drop or create `docs/TODO.md`; set T1.2–T1.4 acceptance to machine-checkable geometry (or achieve them once ENT-002–004 are fixed); rewrite T1.4 context to `py_gearworks`.
- **Verification:** `test -f docs/targets.md` fails (stale pointer gone); `bullseye` validate with non-TODO acceptance.
- **Ratchet candidate:** file-match `CLAUDE.md` must not contain `docs/targets.md`; bullseye items with `acceptance: TODO` forbidden.

### ENT-008: No oracle that a part is the part

- **Priority:** P1
- **Dimensions:** Correctness / verification; Build / release / operations
- **Status:** observed fact
- **Evidence:**
  - `find` for `*test*` (excluding `.git`/`export`): none.
  - No CI (ENT-005).
  - Shipped path `Makefile:1-8` stamps on process exit, not on STL content, manifoldness, or bbox.
  - `python3 -m py_compile` exit 0 on all twelve scripts — syntax only.
  - `make` was not run this audit. Existing `export/.*.stamp` timestamps (21:10–21:11) are older than current `projects/*.py` mtimes (21:39); export meshes cannot decide current source.
  - ENT-002–004 exist in source **today** and would pass `make` if `python` and build123d import.
- **Mechanism:** the only gate is “the interpreter did not throw”. CAD defects are silent. Export stamps then hide rebuilds until the `.py` is newer than the stamp, and even then they do not compare geometry.
- **Blast radius:** all parts; ENT-002–004 specifically survived the migration squash.
- **Counterevidence checked:** live preview via `ocp_vscode` is operator-eyeball, optional, and not an oracle. OpenSCAD is installed (2021.01) but unused as a reference mesh generator.
- **Smallest coherent remediation:** per-part bbox/volume tests against numbers taken from current OpenSCAD (or from caliper measurements of printed-good parts). Run them in CI after ENT-005.
- **Verification:** a test that fails on the current `starlock_holders.py` z-span and on magnet-tube z-min=-32.5.
- **Ratchet candidate:** CI `make` + `pytest` golden bboxes; hygiene `correctness.tests`.

### ENT-009: Vendored `gears.scad` and unvendored BOSL2 remain after the Python port

- **Priority:** P2
- **Dimensions:** Redundancy / sources of truth; Security / dependencies
- **Status:** observed fact
- **Evidence:**
  - `gears.scad` 1350 lines; only consumer `triton-lifter.scad:1`.
  - `projects/triton_lifter.py:11` uses `py_gearworks.BevelGear`.
  - `starlock-holders.scad:1`, `screw-box-partitions.scad:1`, `machinist-square-mount.scad:1`: `include <BOSL2/std.scad>` — BOSL2 is not in the repo. Those three Python ports no longer need it.
- **Mechanism:** dead third-party CAD plus an undeclared system include. Rebuilding SCAD triton/starlock/screw-box/machinist requires libraries the Makefile never mentions. License overlap with ENT-006.
- **Blast radius:** SCAD rebuild of four parts; repo license story.
- **Counterevidence checked:** if ENT-001 keeps SCAD as frozen reference, `gears.scad` is required to regenerate `triton-lifter`. That is a reason to isolate, not to leave it unlabeled at repo root.
- **Smallest coherent remediation:** with ENT-001, delete `gears.scad` when SCAD is retired; or move it to `legacy/` with the CC notice. Document BOSL2 only if SCAD stays.
- **Verification:** `git grep BOSL2` / `gears.scad` empty in the live tree, or confined to `legacy/`.
- **Ratchet candidate:** file-absent `gears.scad` at root.

### ENT-010: Export-and-preview block copied twelve times

- **Priority:** P3
- **Dimensions:** Change amplification; Local code quality
- **Status:** observed fact
- **Evidence:** every `projects/*.py` ends with `export_stl` / `export_step` plus `try: from ocp_vscode import show` (e.g. `projects/magnet_tube.py:33-40`, `projects/led_stumps.py:24-30`). `projects/baby_gate_latch.py:7` imports `sqrt` and never uses it.
- **Mechanism:** changing export naming, STEP yes/no, or preview policy is a 12-file edit. Independent parts are otherwise a good boundary (`CLAUDE.md:21` standalone scripts) — a five-line helper would not couple geometry.
- **Blast radius:** cosmetic/tooling only; does not move metal.
- **Counterevidence checked:** keeping scripts standalone avoids a premature `common.py`. The duplication is real but cheap. Unused `sqrt` is not load-bearing.
- **Smallest coherent remediation:** optional tiny `export_part(shape, slug)` used by all scripts; delete unused `sqrt`.
- **Verification:** grep for `export_stl` finds one definition plus calls, or still twelve if the standalone rule is kept (accepted).
- **Ratchet candidate:** none unless a helper is adopted.

## Redundancy and competing-source-of-truth inventory

| Fact | Authorities | Drift already visible |
|---|---|---|
| Part geometry | `*.scad` vs `projects/*.py` vs gitignored `.3mf` meshes vs `export/*.stl` | Yes (ENT-002–004); baby-gate root STL vs `export/` bbox |
| Bevel gears | `gears.scad` vs `py_gearworks` vs bullseye T1.4 text | T1.4 text stale vs `triton_lifter.py` |
| Convergence targets | `CLAUDE.md` → `docs/targets.md` vs `bullseye.yaml` | `docs/targets.md` missing |
| License | SPDX Apache-2.0 vs `gears.scad` CC-BY-NC-SA vs GitHub `licenseInfo: null` | Yes |
| Build output dir | `Makefile` `export/` vs OpenSCAD cwd (root `*.stl`) | Root `baby-gate-latch.stl/.step` leftover |

Deliberate / healthy duplication: twelve independent part scripts (no false shared “Part” abstraction). Optional `ocp_vscode` try/except repeated (ENT-010) is tooling, not domain state.

## Healthy structure worth retaining

- **One script per part, no import graph.** `git grep -n '^from \|^import ' projects/` is only `build123d`, `math`, `py_gearworks`, `ocp_vscode`. No cycles, no god module. Matches `CLAUDE.md:21`.
- **Makefile discovery.** `Makefile:1-8` wildcard + stamp pattern is the right size for this repo. `clean` is `rm -rf export`.
- **Algebra-only ports that live-eval cleanly:** `projects/baby_gate_latch.py` compound bbox `(113.5, 100, 10)` matches OpenSCAD spans 86.5 and 100; `projects/nailgun_tip.py` uses a helper `BuildPart` that **returns** a part, then algebra; `projects/bosch_adapter.py` uses `add(located)` + `Align.MIN`; `projects/led_stumps.py` centering matches SCAD `center=true`.
- **`.gitignore`** covers `export/`, `*.stl`, `*.step`, `*.3mf`, `__pycache__/` — print meshes are not accidentally committed.
- **Optional preview.** `ImportError` guard keeps `make` from requiring VS Code.
- **No epsilon in Python**, as declared. SCAD still uses `e = 0.001`; that is isolated to the legacy tree.
- **`py_compile` exit 0** on all twelve files under Python 3.13.

## Hygiene posture

**Hygiene posture not declared.** There is no `hygiene.yaml`. It was not initialized.

Validator run from repo root:

```
/Users/marcelo/.claude/skills/hygiene/hygiene_check.py
```

Exit 1. Traceback: `FileNotFoundError: …/threedee/hygiene.yaml` (validator `check_repo` → `doc_path.read_text()`).

No per-dimension floors or held tiers exist to report. Overlap with entropy: ENT-005/008/006/007 are the items a later `hygiene.yaml` would declare (`build.make`, `correctness.tests`, `docs.license`, `docs.readme`, `governance.ci`). Ratchet candidates are listed on those findings; `hygiene.yaml` should not be written unless the owner onboards the skill.

## Oracle coverage and residue

| Property | Decided by | Notes |
|---|---|---|
| Python syntax | auxiliary: `py_compile` exit 0 | Not geometry |
| `make` produces STL/STEP | **not run** (would write `export/`) | Shipped path unevaluated this snapshot |
| Part matches OpenSCAD original | nothing | Live probes on snippets only (ENT-002–004) |
| Part is manifold / printable | nothing | |
| Dependency install is reproducible | nothing | ENT-005 |
| License identity | nothing | ENT-006 |
| Bullseye acceptance | nothing (TODO strings) | ENT-007 |
| Secrets / SCA | nothing | No network service; residual risk is supply chain of CAD libs |
| Hygiene floors | n/a | Undeclared |

Failed/skipped checks: `hygiene_check.py` (missing yaml); `make` skipped; OpenSCAD rebuild skipped; no jscpd/ruff/mypy configured.

**Owner residue (intent only):**

1. Is OpenSCAD frozen reference, still the print source, or delete-on-sight?
2. Accept CC-BY-NC-SA `gears.scad` in a public tree, or drop it with the SCAD retirement?
3. Pin a **released** build123d, or keep the git-describe kernel that this machine has?
4. Standalone scripts vs a shared `export_part` helper (ENT-010) — taste.

Mechanical work (bbox goldens, pyproject, CLAUDE pointers, BuildPart rewrites) is not residue.

## Remediation sequence

1. **Oracle seam.** Add `pyproject.toml` + pinned deps; change `Makefile` to `uv run`; add bbox/volume tests that **fail on current** starlock z-span, screw-box z=49, magnet z-min=-32.5, catflap min-x=-110 (ENT-005, ENT-008).
2. **Source of truth.** Decide ENT-001. If Python: quarantine `.scad`/`gears.scad`. If SCAD: stop telling agents that `projects/` is the structure.
3. **Fix the Python geometry** with algebra-only rewrites: ENT-002 (starlock, screw-box, router), ENT-003 (magnet align), ENT-004 (catflap offset). Re-run goldens against OpenSCAD meshes generated once into `tests/golden/`.
4. **Converge docs and license.** CLAUDE paths, bullseye acceptance, `LICENSE`, delete or isolate `gears.scad` (ENT-006, ENT-007, ENT-009).
5. **Ratchet** in CI (`make` + pytest). Onboard `hygiene.yaml` only after those jobs exist, with floors that match reality.
6. Re-run this audit on the same dimension definitions.

No architectural rewrite is required: the one-script-per-part Makefile topology is the right shape once a single CAD language owns it.
