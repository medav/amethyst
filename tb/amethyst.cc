#include <iostream>
#include <fstream>

#include <verilated.h>
#include <verilated_vcd_c.h>

#include "VAmethyst.h"

#define MEMSIZE 4096

uint64_t simtime = 0;

double sc_time_stamp() {
    return simtime;
}

typedef struct _CaptureSignals {
    uint64_t i_raddr;
    uint64_t d_raddr;
    uint64_t d_waddr;
    uint64_t d_wdata[8];
    uint8_t d_wen;
} CaptureSignals;

// VL_IN8(io_clock,0,0);
// VL_IN8(io_reset,0,0);

// VL_OUT8(io_imem_read_valid,0,0);
// VL_IN8(io_imem_read_ready,0,0);
// VL_OUT64(io_imem_read_addr,63,0);

// VL_IN8(io_imem_resp_valid,0,0);
// VL_OUT8(io_imem_resp_ready,0,0);
// VL_OUTW(io_imem_resp_data,511,0,16);
// VL_OUT64(io_imem_resp_addr,63,0);

// VL_OUT8(io_imem_write_valid,0,0);
// VL_IN8(io_imem_write_ready,0,0);
// VL_OUTW(io_imem_write_data,511,0,16);
// VL_OUT64(io_imem_write_addr,63,0);

// VL_OUT8(io_dmem_read_valid,0,0);
// VL_IN8(io_dmem_read_ready,0,0);
// VL_OUT64(io_dmem_read_addr,63,0);

// VL_IN8(io_dmem_resp_valid,0,0);
// VL_OUT8(io_dmem_resp_ready,0,0);
// VL_OUTW(io_dmem_resp_data,511,0,16);
// VL_OUT64(io_dmem_resp_addr,63,0);

// VL_OUT8(io_dmem_write_valid,0,0);
// VL_IN8(io_dmem_write_ready,0,0);
// VL_OUTW(io_dmem_write_data,511,0,16);
// VL_OUT64(io_dmem_write_addr,63,0);

void HandleCapture(VAmethyst * top, CaptureSignals& signals) {
    signals.i_raddr = top->io_imem_r_addr;
    signals.d_raddr = top->io_dmem_r_addr;
    signals.d_waddr = top->io_dmem_w_addr;
    signals.d_wdata = top->io_dmem_w_data;
    signals.d_wen = top->io_dmem_w_en;
}

void HandleIMem(VAmethyst * top, uint8_t * mem, CaptureSignals& signals) {
    if (signals.i_ren) {
        if (signals.i_raddr < MEMSIZE - 4) {
            top->io_imem_r_data = *((uint32_t *)(mem + signals.i_raddr));
        }
        else {
            printf("Invalid IMem Read: Addr = %lx\n", signals.i_raddr);
            top->io_imem_r_data = 0;
        }
    }
}

void HandleDMem(VAmethyst * top, uint8_t * mem, CaptureSignals& signals) {

    if (signals.d_ren) {
        if (signals.d_raddr < MEMSIZE - 8) {
            top->io_dmem_r_data = *((uint64_t *)(mem + signals.d_raddr));
        }
        else {
            printf("Invalid DMem Read: Addr = %lx\n", signals.d_raddr);
            top->io_imem_r_data = 0;
        }
    }

    if (signals.d_wen) {
        if (signals.d_waddr < MEMSIZE - 8) {
            *((uint64_t *)(mem + signals.d_waddr)) = signals.d_wdata;
        }
        else {
            printf("Invalid DMem Write: Addr = %lx\n", signals.d_waddr);
            top->io_imem_r_data = 0;
        }
    }
}

int main(int argc, char **argv) {
    Verilated::traceEverOn(true);

    uint8_t * mem = new uint8_t[MEMSIZE];

    std::ifstream ifs(argv[1], std::ios::binary);
    ifs.read((char *)mem, MEMSIZE);
    ifs.close();

    VAmethyst * top = new VAmethyst;
    VerilatedVcdC * vcd = new VerilatedVcdC;

    top->trace(vcd, 99);
    vcd->open("dump.vcd");

    //
    // Output signals sampled before clock edge
    //

    CaptureSignals signals;

    top->io_imem_read_ready = 1;
    top->io_dmem_read_ready = 1;

    top->io_reset = 1;
    for (int i = 0; i < 10; i++) {
        top->io_clock = 0;
        top->eval();
        vcd->dump(simtime++);
        top->eval();
        vcd->dump(simtime++);
        top->io_clock = 1;
        top->eval();
        vcd->dump(simtime++);
        top->eval();
        vcd->dump(simtime++);
    }
    top->io_reset = 0;

    while (simtime < 1000) {
        top->io_clock = 0;

        top->eval();
        vcd->dump(simtime++);

        top->eval();
        vcd->dump(simtime++);

        HandleCapture(top, signals);

        top->io_clock = 1;

        top->eval();
        HandleIMem(top, mem, signals);
        HandleDMem(top, mem, signals);
        vcd->dump(simtime++);

        top->eval();
        vcd->dump(simtime++);
    }

    vcd->close();
    top->final();

    delete vcd;
    delete top;

    return 0;
}