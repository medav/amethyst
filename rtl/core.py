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
    # execute_stage = Instance(execute.ExecuteState())

    if_id_reg = Reg(if_id_bundle, reset_value=if_id_bundle_reset)
    # if_id_reg <<= ifetch_stage.out_data

    #
    # IDecode Stage
    #

    idecode_stage.in_data <<= if_id_reg
    id_ex_reg = Reg(id_ex_bundle, reset_value=id_ex_bundle_reset)
    id_ex_reg <<= idecode_stage.out_data

    NameSignals(locals())