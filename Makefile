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

.PHONY: all clean
