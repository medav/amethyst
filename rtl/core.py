from atlas import *

from interfaces import *

import ifetch
import idecode
import execute
import mem
import writeback
import forward
import hazard

@Module
def Core():
    io = Io({
        'imem': Output(imem_bundle),
        'dmem': Output(dmem_bundle)
    })

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

    if_id_reg = Reg(if_id_bundle, reset_value=if_id_bundle_reset)
    id_ex_reg = Reg(id_ex_bundle, reset_value=id_ex_bundle_reset)
    ex_mem_reg = Reg(ex_mem_bundle, reset_value=ex_mem_bundle_reset)
    mem_wb_reg = Reg(mem_wb_bundle, reset_value=mem_wb_bundle_reset)

    #
    # Forward Unit
    #

    fwd = Instance(forward.ForwardUnit())
    fwd.ex_rs1 <<= id_ex_reg.inst_data.rs1
    fwd.ex_rs2 <<= id_ex_reg.inst_data.rs2
    fwd.mem_rd <<= ex_mem_reg.inst_data.rd
    fwd.wb_rd <<= mem_wb_reg.inst_data.rd

    #
    # Hazard Unit
    #

    hzd = Instance(hazard.HazardUnit())
    hzd.ex_mem_read <<= id_ex_reg.mem_ctrl.mem_read
    hzd.ex_rd <<= id_ex_reg.inst_data.rd
    hzd.id_rs1 <<= idecode_stage.id_ex.inst_data.rs1
    hzd.id_rs2 <<= idecode_stage.id_ex.inst_data.rs2

    #
    # IFetch Stage
    #

    io.imem.r_addr <<= ifetch_stage.imem.r_addr
    io.imem.r_en <<= ifetch_stage.imem.r_en
    ifetch_stage.imem.r_data <<= io.imem.r_data

    with ~hzd.data_hazard:
        if_id_reg <<= ifetch_stage.if_id

    #
    # IDecode Stage
    #

    idecode_stage.if_id <<= if_id_reg
    idecode_stage.inst <<= ifetch_stage.inst

    with hzd.data_hazard:
        id_ex_reg.ex_ctrl <<= execute_ctrl_bundle_reset
        id_ex_reg.mem_ctrl <<= mem_ctrl_bundle_reset
        id_ex_reg.wb_ctrl <<= writeback_ctrl_bundle_reset

    with otherwise:
        id_ex_reg <<= idecode_stage.id_ex

    idecode_stage.reg_write <<= writeback_stage.reg_write

    #
    # Execute Stage
    #

    execute_stage.id_ex <<= id_ex_reg
    ex_mem_reg <<= execute_stage.ex_mem

    execute_stage.fwd1_select <<= fwd.fwd1_select
    execute_stage.fwd2_select <<= fwd.fwd2_select
    execute_stage.fwd_mem_data <<= ex_mem_reg.alu_result
    execute_stage.fwd_wb_data <<= mem_stage.read_data

    #
    # Mem Stage
    #

    io.dmem.r_addr <<= mem_stage.dmem.r_addr
    io.dmem.r_en <<= mem_stage.dmem.r_en
    mem_stage.dmem.r_data <<= io.dmem.r_data

    io.dmem.w_addr <<= mem_stage.dmem.w_addr
    io.dmem.w_en <<= mem_stage.dmem.w_en
    io.dmem.w_addr <<= mem_stage.dmem.w_addr

    mem_stage.ex_mem <<= ex_mem_reg
    mem_wb_reg <<= mem_stage.mem_wb

    #
    # Writeback Stage
    #

    writeback_stage.mem_wb <<= mem_wb_reg
    writeback_stage.mem_read_data <<= mem_stage.read_data

    NameSignals(locals())