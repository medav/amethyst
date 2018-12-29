from atlas import *
from ..support import *

from .bpred import BranchPredictor
from .btb import BranchTargetBuffer
from .ras import ReturnAddressStack

@Module
def IFetchStage():
    """IFetch Stage

    TODO: Documentation
    """

    io = Io({
        'pc': Input(Bits(C['core-width'])),
        'mispred': Input(mispred_bundle),
        'ras_ctrl': Input(ras_ctrl_bundle),
        'next_pc': Output(Bits(C['core-width'])),
        'if1_if2': Output(if_bundle)
    })

    bpred = Instance(BranchPredictor())
    btb = Instance(BranchTargetBuffer())
    ras = Instance(ReturnAddressStack())

    ras.ctrl <<= io.ras_ctrl

    next_pc = Wire(Bits(C['paddr-width']))
    if1_pc = Wire(Bits(C['paddr-width']))

    btb.cur_pc <<= next_pc
    bpred.cur_pc <<= next_pc

    #
    # Misprediction Update Handling
    #

    btb.update.valid <<= io.mispred.valid
    btb.update.pc <<= io.mispred.pc
    btb.update.target <<= io.mispred.target
    btb.update.is_return <<= io.mispred.is_return

    bpred.update.valid <<= io.mispred.valid
    bpred.update.pc <<= io.mispred.pc
    bpred.update.taken <<= io.mispred.taken

    #
    # The predicted next PC comes from either the next sequential PC or the
    # predicted target address in the BTB. Note that pred_pc _can_ be wrong and
    # that's ok because the misspeculation will be caught later in the pipeline.
    #

    if1_pc <<= io.pc

    with bpred.pred.taken & btb.pred.valid & ~btb.pred.is_return:
        if1_pc <<= btb.pred.target

    with btb.pred.valid & btb.pred.is_return:
        if1_pc <<= ras.top

    #
    # The actual next PC is either the prediction, a value from the return
    # address stack (RAS) or the correct PC (correction from a misspeculation).
    #

    with io.mispred.valid:
        next_pc <<= io.mispred.target
    with otherwise:
        next_pc <<= if1_pc + 4

    io.next_pc <<= next_pc
    io.if1_if2.valid <<= True
    io.if1_if2.pc <<= if1_pc

    NameSignals(locals())