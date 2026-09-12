PROJECTS := $(wildcard projects/*.py)
STAMPS   := $(PROJECTS:projects/%.py=export/.%.stamp)

all: $(STAMPS)

export/.%.stamp: projects/%.py | export
	cd export && uv run --project .. python ../$<
	@touch $@

export:
	mkdir -p $@

clean:
	rm -rf export

.PHONY: all clean
