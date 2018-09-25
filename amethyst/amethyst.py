from atlas import *
from .support import *

from .frontend.frontend import Frontend
from .cache.cache import Cache, CacheConfig
from .backend.decode import DecodeStage
from .backend.execute import ExecuteStage
from .backend.mem import MemStage
from .backend.writeback import WritebackStage
from .management.forward import ForwardUnit
from .management.hazard import HazardUnit
from .management.branch import BranchUnit

@Module
def Amethyst():
    io = Io({
        'imem': Output(mem_bundle),
        'dmem': Output(mem_bundle)
    })

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

    frontend = Instance(Frontend())
    idecode_stage = Instance(DecodeStage())
    execute_stage = Instance(ExecuteStage())
    mem_stage = Instance(MemStage())
    writeback_stage = Instance(WritebackStage())

    #
    # Pipeline Registers
    #

    if_id_reg = Reg(if_id_bundle, reset_value=if_id_bundle_reset)
    id_ex_reg = Reg(id_ex_bundle, reset_value=id_ex_bundle_reset)
    ex_mem_reg = Reg(ex_mem_bundle, reset_value=ex_mem_bundle_reset)
    mem_wb_reg = Reg(mem_wb_bundle, reset_value=mem_wb_bundle_reset)

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
    # F1, F2, F3: Frontend
    #

    icache.cpu_req <<= frontend.icache.cpu_req
    icache.cpu_stall <<= frontend.icache.cpu_stall
    frontend.icache.miss_stall <<= icache.miss_stall
    frontend.icache.cpu_resp <<= icache.cpu_resp
    frontend.mispred <<= bru.mispred
    frontend.frontend_stall <<= dcache.miss_stall

    with ~dcache.miss_stall:
        if_id_reg <<= frontend.if_id

    #
    # B1: Decode Stage
    #

    idecode_stage.if_id <<= if_id_reg
    idecode_stage.inst <<= frontend.inst

    with bru.mispred.valid:
        id_ex_reg <<= id_ex_bundle_reset
    with otherwise:
        with ~dcache.miss_stall:
            id_ex_reg <<= idecode_stage.id_ex

    idecode_stage.reg_write <<= writeback_stage.reg_write

    #
    # B2: Execute Stage
    #

    execute_stage.id_ex <<= id_ex_reg

    with bru.mispred.valid:
        ex_mem_reg <<= ex_mem_bundle_reset
    with otherwise:
        with ~dcache.miss_stall:
            ex_mem_reg <<= execute_stage.ex_mem

    dcache.cpu_req <<= execute_stage.dcache.cpu_req

    execute_stage.fwd.select1 <<= fwd.fwd1_select
    execute_stage.fwd.select2 <<= fwd.fwd2_select
    execute_stage.fwd.mem_data <<= ex_mem_reg.alu_result
    execute_stage.fwd.wb_data <<= writeback_stage.reg_write.w_data

    #
    # B3: Mem Stage
    #

    mem_stage.ex_mem <<= ex_mem_reg

    with bru.mispred.valid | dcache.miss_stall:
        mem_wb_reg <<= mem_wb_bundle_reset
    with otherwise:
        mem_wb_reg <<= mem_stage.mem_wb

    #
    # B4: Writeback Stage
    #

    writeback_stage.mem_wb <<= mem_wb_reg
    writeback_stage.mem_read_data <<= dcache.cpu_resp.data

    NameSignals(locals())