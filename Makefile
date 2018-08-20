

VERILATOR=verilator

BUILD_DIR=build
TOP=Core

AGENDIR=$(BUILD_DIR)/atlas-gen

VSRC=$(AGENDIR)/geode.v
TBSRC=tb/geode.cc
VSIM=build/geode

VFLAGS= \
	--Mdir build/verilator-gen \
	--cc \
	--top-module $(TOP) \
	--clk io_clock \
	--trace \
	--unroll-count 256 \
	-O3 \
	-CFLAGS "-O3" \
	--savable \
	--exe $(abspath ./$(TBSRC)) \
	-o $(abspath ./$(VSIM))

VGENDIR=$(BUILD_DIR)/verilator-gen

CXX=g++
CXXINC= \
	-I$(VERILATOR_ROOT)/include \
	-I$(VGENDIR)

default: $(VSIM)

.PHONY: build-dirs clean

build-dirs:
	@mkdir -p $(AGENDIR)
	@mkdir -p $(VGENDIR)

$(VSIM): $(TBSRC) $(VSRC) | build-dirs
	$(VERILATOR) $(VFLAGS) $(VSRC)
	make -C $(VGENDIR) -j12 -f V$(TOP).mk

clean:
	rm -r build/verilator-gen
	rm build/geode