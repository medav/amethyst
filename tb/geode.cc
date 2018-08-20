#include <iostream>

#include <verilated.h>
#include <verilated_vcd_c.h>

#include "VCore.h"

VCore * top;
VerilatedVcdC* vcd = nullptr;

uint64_t simtime = 0;

double sc_time_stamp() {
    return simtime;
}

int main(int argc, char **argv) {
    Verilated::traceEverOn(true);

    top = new VCore;
    vcd = new VerilatedVcdC;

    top->trace(vcd, 99);
    vcd->open("dump.vcd");

    top->io_reset = 1;

    while (simtime < 10000) {
        if (simtime > 10) {
            top->io_reset = 0;
        }

        if ((simtime % 10) == 1) {
            top->io_clock = 1;
        }

        if ((simtime % 10) == 6) {
            top->io_clock = 0;
        }

        vcd->dump(simtime);

        top->eval();
        simtime++;
    }

    vcd->close();
    top->final();

    delete vcd;
    delete top;

    return 0;
}