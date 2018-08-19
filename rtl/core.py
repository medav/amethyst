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

    })

    # ifetch_stage = Instance(ifetch.IFetchStage())
    idecode_stage = Instance(idecode.IDecodeStage())
    execute_stage = Instance(execute.ExecuteStage())

    if_id_reg = Reg(if_id_bundle, reset_value=if_id_bundle_reset)
    # if_id_reg <<= ifetch_stage.out_data

    #
    # IDecode Stage
    #

    idecode_stage.if_id <<= if_id_reg
    id_ex_reg = Reg(id_ex_bundle, reset_value=id_ex_bundle_reset)
    id_ex_reg <<= idecode_stage.id_ex

    #
    # Execute Stage
    #

    execute_stage.id_ex <<= id_ex_reg
    ex_mem_reg = Reg(ex_mem_bundle, reset_value=ex_mem_bundle_reset)
    ex_mem_reg <<= execute_stage.ex_mem

    NameSignals(locals())