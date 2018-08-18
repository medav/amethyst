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

    ifetch_stage = Instance(ifetch.IFetchStage())
    idecode_stage = Instance(idecode.IDecodeStage())

    ifetch_reg = Reg(ifetch_bundle)
    ifetch_reg <<= ifetch_stage.out_data

    idecode_stage.in_data <<= ifetch_reg

    NameSignals(locals())