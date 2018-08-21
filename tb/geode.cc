#include <iostream>
#include <fstream>

#include <verilated.h>
#include <verilated_vcd_c.h>

#include "VCore.h"

#define MEMSIZE 4096

uint64_t simtime = 0;

double sc_time_stamp() {
    return simtime;
}

void HandleIMem(VCore * top, uint8_t * mem, uint64_t raddr, uint8_t ren) {
    uint64_t addr;

    if (ren) {
        addr = raddr;

        if (addr < MEMSIZE - 4) {
            top->io_imem_r_data =
                ((uint32_t) mem[addr + 3]) << 24 |
                ((uint32_t) mem[addr + 2]) << 16 |
                ((uint32_t) mem[addr + 1]) << 8 |
                ((uint32_t) mem[addr + 0]);
        }
        else {
            printf("Invalid IMem Read: Addr = %lx\n", addr);
            top->io_imem_r_data = 0;
        }
    }
}

void HandleDMem(VCore * top, uint8_t * mem, uint64_t raddr, uint8_t ren, uint64_t waddr, uint64_t wdata, uint8_t wen) {
    uint64_t addr;

    if (ren) {
        addr = raddr;

        if (addr < MEMSIZE - 8) {
            top->io_dmem_r_data =
                ((uint64_t) mem[addr + 7]) << 56 |
                ((uint64_t) mem[addr + 6]) << 48 |
                ((uint64_t) mem[addr + 5]) << 40 |
                ((uint64_t) mem[addr + 4]) << 32 |
                ((uint64_t) mem[addr + 3]) << 24 |
                ((uint64_t) mem[addr + 2]) << 16 |
                ((uint64_t) mem[addr + 1]) << 8 |
                ((uint64_t) mem[addr + 0]);
        }
        else {
            printf("Invalid DMem Read: Addr = %lx\n", addr);
            top->io_imem_r_data = 0;
        }
    }

    if (wen) {
        addr = waddr;

        if (addr < MEMSIZE - 8) {
            mem[addr + 7] = (wdata >> 56) & 0xFF;
            mem[addr + 6] = (wdata >> 48) & 0xFF;
            mem[addr + 5] = (wdata >> 40) & 0xFF;
            mem[addr + 4] = (wdata >> 32) & 0xFF;
            mem[addr + 3] = (wdata >> 24) & 0xFF;
            mem[addr + 2] = (wdata >> 16) & 0xFF;
            mem[addr + 1] = (wdata >> 8) & 0xFF;
            mem[addr + 0] = (wdata) & 0xFF;
        }
        else {
            printf("Invalid DMem Write: Addr = %lx\n", addr);
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

    VCore * top = new VCore;
    VerilatedVcdC * vcd = new VerilatedVcdC;

    top->trace(vcd, 99);
    vcd->open("dump.vcd");

    //
    // Output signals sampled before clock edge
    //
    uint64_t i_raddr;
    uint8_t i_ren;
    uint64_t d_raddr;
    uint8_t d_ren;
    uint64_t d_waddr;
    uint64_t d_wdata;
    uint8_t d_wen;

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

        i_raddr = top->io_imem_r_addr;
        i_ren = top->io_imem_r_en;
        d_raddr = top->io_dmem_r_addr;
        d_ren = top->io_dmem_r_en;
        d_waddr = top->io_dmem_w_addr;
        d_wdata = top->io_dmem_w_data;
        d_wen = top->io_dmem_w_en;

        top->io_clock = 1;
        top->eval();
        HandleIMem(top, mem, i_raddr, i_ren);
        HandleDMem(top, mem, d_raddr, d_ren, d_waddr, d_wdata, d_wen);
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