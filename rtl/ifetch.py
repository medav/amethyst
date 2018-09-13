from atlas import *
from interfaces import *

from config import *

from icache import ICache
from bpred import BranchPredictor
from btb import BranchTargetBuffer
from ras import ReturnAddressStack

@Module
def IFetchStage():
    """The instruction fetch stage for Geode.

    This stage contains the program counter register for the pipeline and
    produces imem accesses to retrieve instructions.

    branch and branch_target also signal when the PC needs to be altered due to
    a branch instructions.
    """

    io = Io({
        'if_id': Output(if_id_bundle),
        'inst': Output(Bits(32)),
        'icache': Output({
            'cpu_req': Bits(paddr_width),
            'cpu_resp': Flip({
                'miss': Bits(1),
                'data': Bits(32)
            })
        }),
        'misspec': Input({
            'valid': Bits(1),
            'pc': Bits(paddr_width),
            'target': Bits(paddr_width),
            'taken': Bits(1),
            'is_return': Bits(1)
        }),
        'branch': Input(Bits(1)),
        'branch_target': Input(Bits(paddr_width))
    })

    bpred = Instance(BranchPredictor())
    btb = Instance(BranchTargetBuffer())
    ras = Instance(ReturnAddressStack())

    ras.pop.valid <<= False

    #
    # Hook up the icache to the imem ports
    #

    io.imem <<= icache.imem

    #
    # This is the program counter for Geode. It decides what instruction is
    # next to be executed.
    #

    pc = Reg(Bits(paddr_width), reset_value=C['reset-addr'])
    pred_pc = Wire(Bits(paddr_width))
    next_pc = Wire(Bits(paddr_width))

    with ~icache.cpu_resp.miss:
        pc <<= next_pc

    bpred.cur_pc <<= pc
    btb.cur_pc <<= pc
    icache.cpu_req <<= pc

    #
    # The predicted next PC comes from either the next sequential PC or the
    # predicted target address in the BTB. Note that pred_pc _can_ be wrong and
    # that's ok because the misspeculation will be caught later in the pipeline.
    #

    pred_pc <<= pc + 4
    with bpred.pred.taken & btb.pred.valid & ~btb.pred.is_return:
        pred_pc <<= btb.pred.target

    #
    # The actual next PC is either the prediction, a value from the return
    # address stack (RAS) or the correct PC (correction from a misspeculation).
    #

    with io.misspec.valid:
        next_pc <<= io.misspec.target
    with otherwise:
        with btb.pred.valid & btb.pred.is_return:
            next_pc <<= ras.pop.address
            ras.pop.valid <<= True

        with otherwise:
            next_pc <<= pred_pc

    #
    # It is assumed that the imem contains an internal latch that captures read
    # data on the rising edge. This means the read data can't be included in the
    # if_id register or it will be delayed by one cycle. Instead, the imem acts
    # as part of the if_id register and bypasses it to the idecode stage.
    #
    # In addition to this, a valid flag is passed to the if_id register to tell
    # the decode stage if the incoming instruction is valid. This is set to
    # false when a branch is taken (because the next instruction to be read is
    # to be discarded).
    #

    io.if_id.pc <<= pc
    io.if_id.valid <<= ~io.branch & ~io.icache.cpu_resp.miss
    io.if_id.inst <<= io.icache.cpu_resp.data

    NameSignals(locals())