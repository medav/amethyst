#include <iostream>
#include <fstream>
#include <queue>

#include <verilated.h>
#include <verilated_vcd_c.h>

#include "VAmethyst.h"
#include "VAmethyst_Amethyst.h"

#define MEMSIZE (uint64_t)0x20000

#define ASSERT(condition) \
    if (!(condition)) { \
        fprintf(stderr, "[%s:%d] Assertion failure: " # condition "\n", __FILE__, __LINE__); \
        exit(-1); \
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
        resp.addr = top->io_imem_read_addr & ~0x3F;

        ASSERT(resp.addr < (MEMSIZE - 64))

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
        resp.addr = top->io_dmem_read_addr & ~0x3F;

        ASSERT(resp.addr < (MEMSIZE - 64))

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

void Separator() {
    printf("|");
}

void PrintStage(uint8_t valid, uint64_t pc, uint64_t inst) {
    if (valid) {
        printf(" %04x(%08x) ", (uint32_t)pc, (uint32_t)inst);
    }
    else {
        printf(" -------------- ");
    }
}

void PrintIf(uint8_t valid, char ch) {
    if (valid) {
        printf("%c", ch);
    }
    else {
        printf(" ");
    }
}

void HandleProbes(VAmethyst * top) {
    // cycle, if1, if2, if3, id, ex, mem, wb
    printf("%04llu ", simtime / 2);
    Separator();
    PrintStage(1, top->Amethyst->probe_if1_pc, 0);
    Separator();
    PrintStage(
        top->Amethyst->probe_if2_valid,
        top->Amethyst->probe_if2_pc,
        0);
    Separator();
    PrintStage(
        top->Amethyst->probe_if3_valid,
        top->Amethyst->probe_if3_pc,
        0);
    Separator();
    PrintStage(
        top->Amethyst->probe_id_valid,
        top->Amethyst->probe_id_pc,
        top->Amethyst->probe_id_inst);
    Separator();
    PrintStage(
        top->Amethyst->probe_ex_valid,
        top->Amethyst->probe_ex_pc,
        top->Amethyst->probe_ex_inst);
    Separator();
    PrintStage(
        top->Amethyst->probe_mem_valid,
        top->Amethyst->probe_mem_pc,
        top->Amethyst->probe_mem_inst);
    Separator();
    PrintStage(
        top->Amethyst->probe_wb_valid,
        top->Amethyst->probe_wb_pc,
        top->Amethyst->probe_wb_inst);
    Separator();
    printf(" ");
    PrintIf(top->Amethyst->probe_icache_stall, 'I');
    PrintIf(top->Amethyst->probe_dcache_stall, 'D');
    PrintIf(top->Amethyst->probe_ex_mem_rd, 'R');
    PrintIf(top->Amethyst->probe_ex_mem_wr, 'W');
    printf(" ");
    if (top->Amethyst->probe_reg_w_en) {
        printf(
            "[WB: Reg: r%02d, Data: 0x%lx]",
            top->Amethyst->probe_reg_w_addr,
            top->Amethyst->probe_reg_w_data);
    }
    printf(" ");
    if (top->Amethyst->probe_dcache_cpu_req_valid) {
        printf(
            "[$: Addr: 0x%lx, Read: 0x%lx]",
            top->Amethyst->probe_dcache_cpu_req_addr,
            top->Amethyst->probe_dcache_cpu_req_read);
    }
    printf("\n");
}

int main(int argc, char **argv) {
    Verilated::traceEverOn(true);

    printf(" cyc | ifetch1        | ifetch2        | ifetch3        |  decode        | execute        |   mem          |    wb          |\n");

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
        vcd->dump((vluint64_t)simtime++);

        top->io_clock = 1;

        top->eval();
        vcd->dump((vluint64_t)simtime++);
    }

    top->io_reset = 0;

    while (simtime < 1000) {
        top->io_clock = 0;
        HandleIMem(top, mem);
        HandleDMem(top, mem);

        top->eval();
        vcd->dump((vluint64_t)simtime++);

        HandleProbes(top);

        top->io_clock = 1;

        top->eval();
        vcd->dump((vluint64_t)simtime++);
    }

    vcd->close();
    top->final();

    delete vcd;
    delete top;

    return 0;
}
