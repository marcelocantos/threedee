PROJECTS := $(wildcard projects/*.py)
STAMPS   := $(PROJECTS:projects/%.py=export/.%.stamp)

all: check

# Exporting is not evidence: a script that produces empty or misplaced
# geometry still exits 0. Every build ends by measuring what it wrote.
check: $(STAMPS)
	python tools/check_geometry.py export expectations.yaml

export/.%.stamp: projects/%.py | export
	cd export && python ../$<
	@touch $@

export:
	mkdir -p $@

clean:
	rm -rf export

.PHONY: all check clean
