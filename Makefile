

VERILATOR=verilator
PYTHON=python3
CXX=g++

TOP=Amethyst

BUILDDIR=build
VGENDIR=$(BUILDDIR)/verilator-gen

RTLSRC=$(shell find amethyst -path '*.py')
VSRC=$(BUILDDIR)/amethyst.v
TBSRC=tb/amethyst.cc
VSIM=build/amethyst

VFLAGS= \
	--Mdir build/verilator-gen \
	--cc \
	--top-module $(TOP) \
	--trace \
	--output-split 24 \
	--unroll-count 256 \
	-Wno-STMTDLY \
	--x-assign unique \
	-O3 \
	-CFLAGS "-O3" \
	--savable \
	--exe $(abspath ./$(TBSRC)) \
	-o $(abspath ./$(VSIM))

default: $(VSIM) apps

.PHONY: build-dirs clean apps

build-dirs:
	@mkdir -p $(BUILDDIR)
	@mkdir -p $(VGENDIR)

apps:
	$(MAKE) -C apps/

$(VSRC): $(RTLSRC) | build-dirs
	$(PYTHON) build.py

$(VSIM): $(TBSRC) $(VSRC) | build-dirs
	$(VERILATOR) $(VFLAGS) $(VSRC)
	$(MAKE) -C $(VGENDIR) -f V$(TOP).mk

clean:
	@rm -rf build
