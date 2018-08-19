from atlas import *

from interfaces import *

import ifetch
import idecode
import execute
import mem
import writeback

@Module
def Core():
    io = Io({
        'imem': Output(imem_bundle),
        'dmem': Output(dmem_bundle)
    })

    # ifetch_stage = Instance(ifetch.IFetchStage())
    idecode_stage = Instance(idecode.IDecodeStage())
    execute_stage = Instance(execute.ExecuteStage())
    mem_stage = Instance(mem.MemStage())
    writeback_stage = Instance(writeback.WritebackStage())

    if_id_reg = Reg(if_id_bundle, reset_value=if_id_bundle_reset)
    # if_id_reg <<= ifetch_stage.out_data

    #
    # IDecode Stage
    #

    idecode_stage.if_id <<= if_id_reg
    id_ex_reg = Reg(id_ex_bundle, reset_value=id_ex_bundle_reset)
    id_ex_reg <<= idecode_stage.id_ex

    idecode_stage.reg_write <<= writeback_stage.reg_write

    #
    # Execute Stage
    #

    execute_stage.id_ex <<= id_ex_reg
    ex_mem_reg = Reg(ex_mem_bundle, reset_value=ex_mem_bundle_reset)
    ex_mem_reg <<= execute_stage.ex_mem

    #
    # Mem Stage
    #

    mem_stage.ex_mem <<= ex_mem_reg
    mem_wb_reg = Reg(mem_wb_bundle, reset_value=mem_wb_bundle_reset)
    mem_wb_reg <<= mem_stage.mem_wb

    #
    # Writeback Stage
    #

    writeback_stage.mem_wb <<= mem_wb_reg


    NameSignals(locals())