from atlas import *

from interfaces import *

import cache

import ifetch
import idecode
import execute
import mem
import writeback
import forward
import hazard

@Module
def Amethyst():
    io = Io({
        'imem': Output(mem_bundle),
        'dmem': Output(mem_bundle)
    })

    #
    # Instruction and Data Caches
    #

    icache = Instance(cache.Cache(cache.CacheConfig.FromCacheType('icache')))
    io.imem <<= icache.mem

    dcache = Instance(cache.Cache(cache.CacheConfig.FromCacheType('dcache')))
    io.dmem <<= dcache.mem

    #
    # Pipeline Stages
    #

    ifetch_stage = Instance(ifetch.IFetchStage())
    idecode_stage = Instance(idecode.IDecodeStage())
    execute_stage = Instance(execute.ExecuteStage())
    mem_stage = Instance(mem.MemStage())
    writeback_stage = Instance(writeback.WritebackStage())

    #
    # Pipeline Registers
    #

    id_ex_reg = Reg(id_ex_bundle, reset_value=id_ex_bundle_reset)
    ex_mem_reg = Reg(ex_mem_bundle, reset_value=ex_mem_bundle_reset)
    mem_wb_reg = Reg(mem_wb_bundle, reset_value=mem_wb_bundle_reset)

    #
    # Forward Unit
    #

    fwd = Instance(forward.ForwardUnit())
    fwd.ex_rs1 <<= id_ex_reg.ctrl.inst.rs1
    fwd.ex_rs2 <<= id_ex_reg.ctrl.inst.rs2
    fwd.mem_rd <<= ex_mem_reg.ctrl.inst.rd
    fwd.wb_rd <<= mem_wb_reg.ctrl.inst.rd
    fwd.mem_reg_write <<= 1
    fwd.wb_reg_write <<= 1

    #
    # Hazard Unit
    #

    hzd = Instance(hazard.HazardUnit())
    hzd.ex_mem_read <<= id_ex_reg.ctrl.mem.mem_read
    hzd.ex_rd <<= id_ex_reg.ctrl.inst.rd
    hzd.id_rs1 <<= idecode_stage.id_ex.ctrl.inst.rs1
    hzd.id_rs2 <<= idecode_stage.id_ex.ctrl.inst.rs2

    #
    # 1. IFetch Stage
    #

    icache.cpu_req <<= ifetch_stage.icache.cpu_req
    icache.cpu_stall <<= ifetch_stage.icache.cpu_stall
    ifetch_stage.icache.miss_stall <<= icache.miss_stall
    ifetch_stage.icache.cpu_resp <<= icache.cpu_resp

    # ifetch_stage.branch <<= mem_stage.branch
    # ifetch_stage.branch_target <<= mem_stage.branch_target

    #
    # 2. IDecode Stage
    #

    idecode_stage.if_id <<= ifetch_stage.if_id
    id_ex_reg <<= idecode_stage.id_ex

    idecode_stage.reg_write <<= writeback_stage.reg_write

    #
    # 3. Execute Stage
    #

    execute_stage.id_ex <<= id_ex_reg
    ex_mem_reg <<= execute_stage.ex_mem

    dcache.cpu_req <<= execute_stage.dcache.cpu_req

    execute_stage.fwd.select1 <<= fwd.fwd1_select
    execute_stage.fwd.select2 <<= fwd.fwd2_select
    execute_stage.fwd.mem_data <<= ex_mem_reg.alu_result
    execute_stage.fwd.wb_data <<= writeback_stage.reg_write.w_data

    #
    # 4. Mem Stage
    #

    mem_stage.ex_mem <<= ex_mem_reg
    mem_wb_reg <<= mem_stage.mem_wb

    #
    # 5. Writeback Stage
    #

    writeback_stage.mem_wb <<= mem_wb_reg
    writeback_stage.mem_read_data <<= dcache.cpu_resp.data

    NameSignals(locals())