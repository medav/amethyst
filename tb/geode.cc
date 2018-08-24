#include <iostream>
#include <fstream>

#include <verilated.h>
#include <verilated_vcd_c.h>

#include "VGeodeCore.h"

#define MEMSIZE 4096

uint64_t simtime = 0;

double sc_time_stamp() {
    return simtime;
}

typedef struct _CaptureSignals {
    uint64_t i_raddr;
    uint8_t i_ren;
    uint64_t d_raddr;
    uint8_t d_ren;
    uint64_t d_waddr;
    uint64_t d_wdata;
    uint8_t d_wen;
} CaptureSignals;

void HandleCapture(VGeodeCore * top, CaptureSignals& signals) {
    signals.i_raddr = top->io_imem_r_addr;
    signals.i_ren = top->io_imem_r_en;
    signals.d_raddr = top->io_dmem_r_addr;
    signals.d_ren = top->io_dmem_r_en;
    signals.d_waddr = top->io_dmem_w_addr;
    signals.d_wdata = top->io_dmem_w_data;
    signals.d_wen = top->io_dmem_w_en;
}

void HandleIMem(VGeodeCore * top, uint8_t * mem, CaptureSignals& signals) {
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

void HandleDMem(VGeodeCore * top, uint8_t * mem, CaptureSignals& signals) {

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

    VGeodeCore * top = new VGeodeCore;
    VerilatedVcdC * vcd = new VerilatedVcdC;

    top->trace(vcd, 99);
    vcd->open("dump.vcd");

    //
    // Output signals sampled before clock edge
    //

    CaptureSignals signals;

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