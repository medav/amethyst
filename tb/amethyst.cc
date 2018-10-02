#include <iostream>
#include <fstream>
#include <queue>

#include <verilated.h>
#include <verilated_vcd_c.h>

#include "VAmethyst.h"

#define MEMSIZE (uint64_t)0x20000

#define ASSERT(condition) \
    if (!(condition)) { \
        fprintf(stderr, "[%s:%d] Assertion failure: " # condition "\n", __FILE__, __LINE__); \
        return; \
    }

uint64_t simtime = 0;

double sc_time_stamp() {
    return simtime;
}

typedef struct _ReadResponse {
    uint64_t addr;
    uint32_t data[16];
} ReadResponse;

std::queue<ReadResponse> iqueue;
std::queue<ReadResponse> dqueue;

void HandleIMem(VAmethyst * top, uint8_t * mem) {
    top->io_imem_read_ready = true;

    if (top->io_imem_read_valid) {
        ReadResponse resp;
        resp.addr = top->io_imem_read_addr;

        ASSERT(resp.addr < (MEMSIZE - 64))
        // ASSERT(resp.addr & 0x3F == 0)

        memcpy(resp.data, mem + resp.addr, 64);
        iqueue.push(resp);
    }

    top->io_imem_resp_valid = false;

    if (top->io_imem_resp_ready && !iqueue.empty()) {
        const ReadResponse& resp = iqueue.front();
        top->io_imem_resp_valid = true;
        top->io_imem_resp_addr = resp.addr;
        memcpy(top->io_imem_resp_data, resp.data, 64);
        iqueue.pop();
    }

    top->io_imem_write_ready = false;
}

void HandleDMem(VAmethyst * top, uint8_t * mem) {
    top->io_dmem_read_ready = true;

    if (top->io_dmem_read_valid) {
        ReadResponse resp;
        resp.addr = top->io_dmem_read_addr;

        std::cerr << std::hex << resp.addr << std::dec << std::endl;

        ASSERT(resp.addr < (MEMSIZE - 64))
        // ASSERT(resp.addr & 0x3F == 0)

        memcpy(resp.data, mem + resp.addr, 64);
        dqueue.push(resp);
    }

    top->io_dmem_resp_valid = false;

    if (top->io_dmem_resp_ready && !dqueue.empty()) {
        const ReadResponse& resp = dqueue.front();
        top->io_dmem_resp_valid = true;
        top->io_dmem_resp_addr = resp.addr;
        memcpy(top->io_dmem_resp_data, resp.data, 64);
        dqueue.pop();
    }

    top->io_dmem_write_ready = true;

    if (top->io_dmem_write_valid) {
        memcpy(mem + top->io_dmem_write_addr, top->io_dmem_write_data, 64);
    }
}

void HandlePcLog(VAmethyst * top) {
    if (top->io_debug_pc_trigger) {
        printf("0x%08lx 0x%08x DASM(0x%08x)\n", top->io_debug_pc_trace, top->io_debug_pc_inst, top->io_debug_pc_inst);
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

    top->io_reset = 1;

    for (int i = 0; i < 10; i++) {
        top->io_clock = 0;

        top->eval();
        vcd->dump(simtime++);

        top->io_clock = 1;

        top->eval();
        vcd->dump(simtime++);
    }

    top->io_reset = 0;

    while (simtime < 1000) {
        top->io_clock = 0;
        HandleIMem(top, mem);
        HandleDMem(top, mem);

        top->eval();
        vcd->dump(simtime++);

        HandlePcLog(top);

        top->io_clock = 1;

        top->eval();
        vcd->dump(simtime++);
    }

    vcd->close();
    top->final();

    delete vcd;
    delete top;

    return 0;
}
