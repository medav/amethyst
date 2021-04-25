from dataclasses import dataclass

from atlas import *
from .support import *

from .frontend.ifetch import IFetchStage
from .cache.cache import Cache, CacheConfig
from .backend.decode import DecodeStage
from .backend.execute import ExecuteStage
from .backend.mem import MemStage
from .backend.writeback import WritebackStage
from .management.forward import ForwardUnit
from .management.hazard import HazardUnit
from .management.branch import BranchUnit

def PipelineUpdate(pipe_reg, next_value, flush_signal, reset_value, stall_signal):
    def HandleStall(pipe_reg):
        if stall_signal is not None:
            with ~stall_signal:
                pipe_reg <<= next_value

        else:
            pipe_reg <<= next_value

    if flush_signal is not None:
        with flush_signal:
            pipe_reg <<= reset_value
        with otherwise:
            HandleStall(pipe_reg)

    else:
        HandleStall(pipe_reg)

@Module
def Amethyst():
    io = Io({
        'imem': Output(mem_bundle),
        'dmem': Output(mem_bundle),
        'debug': Output(debug_bundle)
    })

    pc = Reg(Bits(C['paddr-width']), reset_value=C['reset-addr'])

    #
    # Instruction and Data Caches
    #

    icache = Instance(Cache(CacheConfig.FromCacheType('icache')))
    io.imem <<= icache.mem

    dcache = Instance(Cache(CacheConfig.FromCacheType('dcache')))
    io.dmem <<= dcache.mem

    #
    # Pipeline Stages
    #

    ifetch_stage = Instance(IFetchStage())
    idecode_stage = Instance(DecodeStage())
    execute_stage = Instance(ExecuteStage())
    mem_stage = Instance(MemStage())
    writeback_stage = Instance(WritebackStage())

    #
    # Pipeline Registers
    #

    if1_if2_reg = Reg(if_bundle, reset_value=if_bundle_reset)
    if2_if3_reg = Reg(if_bundle, reset_value=if_bundle_reset)
    if_id_reg = Reg(if_bundle, reset_value=if_bundle_reset)
    id_ex_reg = Reg(id_ex_bundle, reset_value=id_ex_bundle_reset)
    ex_mem_reg = Reg(ex_mem_bundle, reset_value=ex_mem_bundle_reset)
    mem_wb_reg = Reg(mem_wb_bundle, reset_value=mem_wb_bundle_reset)

    #
    # Probes
    #

    Probe(pc, 'if1_pc')

    Probe(if1_if2_reg.valid, 'if2_valid')
    Probe(if1_if2_reg.pc, 'if2_pc')

    Probe(if2_if3_reg.valid, 'if3_valid')
    Probe(if2_if3_reg.pc, 'if3_pc')

    Probe(if_id_reg.valid, 'id_valid')
    Probe(if_id_reg.pc, 'id_pc')
    Probe(icache.cpu_resp.data(31, 0), 'id_inst')

    Probe(id_ex_reg.ctrl.valid, 'ex_valid')
    Probe(id_ex_reg.ctrl.pc, 'ex_pc')
    Probe(id_ex_reg.ctrl.inst, 'ex_inst')
    Probe(id_ex_reg.ctrl.mem.mem_read, "ex_mem_rd")
    Probe(id_ex_reg.ctrl.mem.mem_write, "ex_mem_wr")

    Probe(ex_mem_reg.ctrl.valid, 'mem_valid')
    Probe(ex_mem_reg.ctrl.pc, 'mem_pc')
    Probe(ex_mem_reg.ctrl.inst, 'mem_inst')

    Probe(mem_wb_reg.ctrl.valid, 'wb_valid')
    Probe(mem_wb_reg.ctrl.pc, 'wb_pc')
    Probe(mem_wb_reg.ctrl.inst, 'wb_inst')

    Probe(icache.miss_stall, 'icache_stall')
    Probe(dcache.miss_stall, 'dcache_stall')

    #
    # Forward, Hazard, and Branch Units
    #

    fwd = Instance(ForwardUnit())
    fwd.ex_rs1 <<= Rs1(id_ex_reg.ctrl.inst)
    fwd.ex_rs2 <<= Rs2(id_ex_reg.ctrl.inst)
    fwd.mem_rd <<= Rd(ex_mem_reg.ctrl.inst)
    fwd.wb_rd <<= Rd(mem_wb_reg.ctrl.inst)
    fwd.mem_reg_write <<= 1
    fwd.wb_reg_write <<= 1

    hzd = Instance(HazardUnit())
    hzd.ex_mem_read <<= id_ex_reg.ctrl.mem.mem_read
    hzd.ex_rd <<= Rd(id_ex_reg.ctrl.inst)
    hzd.id_rs1 <<= Rs1(idecode_stage.id_ex.ctrl.inst)
    hzd.id_rs2 <<= Rs2(idecode_stage.id_ex.ctrl.inst)

    bru = Instance(BranchUnit())
    bru.ex_pc <<= id_ex_reg.ctrl.pc
    bru.mem_pc <<= ex_mem_reg.ctrl.pc
    bru.branch <<= mem_stage.branch

    #
    # IF1: IFetch 1
    #

    ifetch_stage.pc <<= pc
    ifetch_stage.mispred <<= bru.mispred

    PipelineUpdate(
        pipe_reg=if1_if2_reg,
        next_value=ifetch_stage.if1_if2,
        flush_signal=bru.mispred.valid,
        reset_value=if_bundle_reset,
        stall_signal=dcache.miss_stall | icache.miss_stall)

    PipelineUpdate(
        pipe_reg=pc,
        next_value=ifetch_stage.next_pc,
        flush_signal=None,
        reset_value=None,
        stall_signal=dcache.miss_stall | icache.miss_stall)

    #
    # IF2: IFetch 2
    #

    icache.cpu_stall <<= dcache.miss_stall

    icache.cpu_req <<= {
        'valid': if1_if2_reg.valid,
        'addr': if1_if2_reg.pc,
        'rtype': access_rtype.w,
        'read': True
    }

    next_if2_if3 = {
        'valid': if1_if2_reg.valid & ~icache.miss_stall,
        'pc': if1_if2_reg.pc
    }

    PipelineUpdate(
        pipe_reg=if2_if3_reg,
        next_value=next_if2_if3,
        flush_signal=bru.mispred.valid,
        reset_value=if_bundle_reset,
        stall_signal=dcache.miss_stall | icache.miss_stall)

    #
    # IF3: IFetch 3
    #

    next_if_id = {
        'valid': if2_if3_reg.valid & ~icache.miss_stall,
        'pc': if2_if3_reg.pc
    }

    PipelineUpdate(
        pipe_reg=if_id_reg,
        next_value=next_if_id,
        flush_signal=bru.mispred.valid,
        reset_value=if_bundle_reset,
        stall_signal=dcache.miss_stall)

    #
    # B1: Decode Stage
    #

    idecode_stage.if_id <<= if_id_reg
    idecode_stage.inst <<= icache.cpu_resp.data(31, 0)
    idecode_stage.reg_write <<= writeback_stage.reg_write
    idecode_stage.stall <<= dcache.miss_stall

    Probe(writeback_stage.reg_write.w_en, 'reg_w_en')
    Probe(writeback_stage.reg_write.w_addr, 'reg_w_addr')
    Probe(writeback_stage.reg_write.w_data, 'reg_w_data')

    PipelineUpdate(
        pipe_reg=id_ex_reg,
        next_value=idecode_stage.id_ex,
        flush_signal=bru.mispred.valid,
        reset_value=id_ex_bundle_reset,
        stall_signal=dcache.miss_stall)

    #
    # B2: Execute Stage
    #

    execute_stage.id_ex <<= id_ex_reg
    execute_stage.rs1_data <<= idecode_stage.rs1_data
    execute_stage.rs2_data <<= idecode_stage.rs2_data
    execute_stage.fwd.select1 <<= fwd.fwd1_select
    execute_stage.fwd.select2 <<= fwd.fwd2_select
    execute_stage.fwd.mem_data <<= ex_mem_reg.alu_result
    execute_stage.fwd.wb_data <<= writeback_stage.reg_write.w_data

    dcache.cpu_req <<= execute_stage.dcache.cpu_req
    Probe(execute_stage.dcache.cpu_req.valid, 'dcache_cpu_req_valid')
    Probe(execute_stage.dcache.cpu_req.addr, 'dcache_cpu_req_addr')
    Probe(execute_stage.dcache.cpu_req.read, 'dcache_cpu_req_read')

    PipelineUpdate(
        pipe_reg=ex_mem_reg,
        next_value=execute_stage.ex_mem,
        flush_signal=bru.mispred.valid,
        reset_value=ex_mem_bundle_reset,
        stall_signal=dcache.miss_stall)

    #
    # B3: Mem Stage
    #

    mem_stage.ex_mem <<= ex_mem_reg

    next_mem_wb = Wire(mem_wb_bundle)

    with dcache.miss_stall:
        next_mem_wb <<= mem_wb_bundle_reset
    with otherwise:
        next_mem_wb <<= mem_stage.mem_wb

    PipelineUpdate(
        pipe_reg=mem_wb_reg,
        next_value=next_mem_wb,
        flush_signal=bru.mispred.valid | dcache.miss_stall,
        reset_value=mem_wb_bundle_reset,
        stall_signal=None)

    #
    # B4: Writeback Stage
    #

    writeback_stage.mem_wb <<= mem_wb_reg
    writeback_stage.mem_read_data <<= dcache.cpu_resp.data

    #
    # Debug Signals
    #

    io.debug.pc_trigger <<= mem_wb_reg.ctrl.valid
    io.debug.pc_trace <<= mem_wb_reg.ctrl.pc
    io.debug.pc_inst <<= mem_wb_reg.ctrl.inst

    NameSignals(locals())
