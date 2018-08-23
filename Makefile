

VERILATOR=verilator

TOP=GeodeCore

BUILDDIR=build
VGENDIR=$(BUILDDIR)/verilator-gen

CXX=g++
CXXINC= \
	-I$(VERILATOR_ROOT)/include \
	-I$(VGENDIR)

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

default: $(VSIM)

.PHONY: build-dirs clean

build-dirs:
	@mkdir -p $(BUILDDIR)
	@mkdir -p $(VGENDIR)

$(VSIM): $(TBSRC) $(VSRC) | build-dirs
	$(VERILATOR) $(VFLAGS) $(VSRC)
	$(MAKE) -C $(VGENDIR) -f V$(TOP).mk

clean:
	@rm -r build/verilator-gen
	@rm build/geode