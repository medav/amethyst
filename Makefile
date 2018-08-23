

VERILATOR=verilator
PYTHON=python3
CXX=g++

TOP=GeodeCore

BUILDDIR=build
VGENDIR=$(BUILDDIR)/verilator-gen

RTLSRC=$(wildcard rtl/*.py)
VSRC=$(BUILDDIR)/geode.v
TBSRC=tb/geode.cc
VSIM=build/geode

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

default: $(VSIM) app

.PHONY: build-dirs clean app

build-dirs:
	@mkdir -p $(BUILDDIR)
	@mkdir -p $(VGENDIR)

app:
	$(MAKE) -C app/

$(VSRC): $(RTLSRC)
	$(PYTHON) geode.py

$(VSIM): $(TBSRC) $(VSRC) | build-dirs
	$(VERILATOR) $(VFLAGS) $(VSRC)
	$(MAKE) -C $(VGENDIR) -f V$(TOP).mk

clean:
	@rm -rf build