PROJECTS := $(wildcard projects/*.py)
STAMPS   := $(PROJECTS:projects/%.py=export/.%.stamp)

all: $(STAMPS)

export/.%.stamp: projects/%.py | export
	cd export && python ../$<
	@touch $@

export:
	mkdir -p $@

clean:
	rm -rf export

# Port fidelity oracle: OpenSCAD reference vs build123d export (tools/port_oracle.py).
.PHONY: oracle
oracle: all
	python tools/port_oracle.py --threshold 0.01

.PHONY: all clean

# Standing invariants for bullseye_convergence.
.PHONY: bullseye
bullseye: all oracle
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
