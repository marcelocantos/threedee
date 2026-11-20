ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
# Frozen and offline: resolution happens in `uv sync`, not during a build.
UV   := uv run --frozen --offline --project $(ROOT)
export PYTHONPATH := $(ROOT)

PROJECTS := $(wildcard projects/*.py)
STAMPS   := $(PROJECTS:projects/%.py=export/.%.stamp)

all: $(STAMPS) projects/trolley-key/export/.stamp projects/scale-rails/export/.stamp projects/puzzle-tray/export/.stamp projects/express-1m2-stand/export/.stamp projects/mixer-stand/export/.stamp

projects/trolley-key/export/.stamp: projects/trolley-key/ring_hook.py
	mkdir -p $(@D)
	cd $(@D) && $(UV) python ../ring_hook.py --plate --no-preview
	@touch $@

projects/scale-rails/export/.stamp: projects/scale-rails/scale_rails.py
	mkdir -p $(@D)
	cd $(@D) && $(UV) python ../scale_rails.py --no-preview
	@touch $@

projects/puzzle-tray/export/.stamp: projects/puzzle-tray/puzzle_tray.py
	mkdir -p $(@D)
	cd $(@D) && $(UV) python ../puzzle_tray.py --no-preview
	@touch $@

# Optional (needs Bambu Studio installed): tray + grip modifier with fuzzy skin, as a Studio project.
projects/puzzle-tray/export/puzzle-tray-fuzzy-grips.3mf: projects/puzzle-tray/export/.stamp projects/puzzle-tray/fuzzy_3mf.py
	cd $(@D) && $(UV) python ../fuzzy_3mf.py

projects/express-1m2-stand/export/.stamp: projects/express-1m2-stand/express_1m2_stand.py
	mkdir -p $(@D)
	cd $(@D) && $(UV) python ../express_1m2_stand.py --no-preview
	@touch $@

projects/mixer-stand/export/.stamp: projects/mixer-stand/mixer_stand.py
	mkdir -p $(@D)
	cd $(@D) && $(UV) python ../mixer_stand.py --no-preview
	@touch $@

export/.%.stamp: projects/%.py | export
	cd export && $(UV) python ../$<
	@touch $@

export:
	mkdir -p $@

clean:
	rm -rf export projects/trolley-key/export projects/scale-rails/export projects/puzzle-tray/export projects/express-1m2-stand/export projects/mixer-stand/export

.PHONY: all clean ascut-oracle

# Reimport the as-cut dovetail and gauge and compare them to the frozen referent.
ascut-oracle:
	python -m pytest projects/ascut/test_ascut_oracle.py -q -p no:cacheprovider -p no:asyncio -W ignore


# Standing invariants for bullseye_convergence.
.PHONY: bullseye
bullseye: all
	@dirty=$$(git status --porcelain | grep -vE 'bullseye\.yaml$$' || true); \
	if [ -z "$$dirty" ]; then echo "✓ working tree clean"; \
	else \
	  echo ""; \
	  echo "================================================================"; \
	  echo "⚠  DIRTY WORKING TREE"; \
	  echo ""; \
	  echo "Warning only — invariants still pass (exit 0)."; \
	  echo "Look at the files below before starting a new target."; \
	  echo "Leftover work from a different objective → park it in a commit first."; \
	  echo "This session's WIP on the recommended target → continue."; \
	  echo "================================================================"; \
	  echo "$$dirty"; \
	  echo "================================================================"; \
	  echo ""; \
	fi
