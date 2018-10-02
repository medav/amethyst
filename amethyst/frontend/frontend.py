from atlas import *
from ..support import *

from .bpred import BranchPredictor
from .btb import BranchTargetBuffer
from .ras import ReturnAddressStack

@Module
def Frontend():
    """The frontend (instruction fetch) pipeline for Amethyst

    This stage contains the program counter register for the pipeline and
    produces imem accesses to retrieve instructions.

    This frontend contains 3 pipeline stages - and so there is a 3 cycle latency
    in producing a valid instruction (assuming a cache hit). This frontend will
    stall on a miss, and flush on a misprediction.
    """

    io = Io({
        'if_id': Output(if_id_bundle),
        'inst': Output(Bits(32)),
        'icache': Output({
            'cpu_req': cpu_cache_req,
            'cpu_stall': Bits(1),
            'miss_stall': Flip(Bits(1)),
            'cpu_resp': Flip(cpu_cache_resp)
        }),
        'mispred': Input(mispred_bundle),
        'ras_ctrl': Input(ras_ctrl_bundle),
        'frontend_stall': Input(Bits(1))
    })

    bpred = Instance(BranchPredictor())
    btb = Instance(BranchTargetBuffer())
    ras = Instance(ReturnAddressStack())

    ras.ctrl <<= io.ras_ctrl

    pc = Reg(Bits(C['paddr-width']), reset_value=C['reset-addr'])
    next_pc = Wire(Bits(C['paddr-width']))

    if1_pc = Wire(Bits(C['paddr-width']))

    if2_pc = Reg(Bits(C['paddr-width']), reset_value=0)
    if2_valid = Reg(Bits(1), reset_value=False)

    with ~io.icache.miss_stall & ~io.frontend_stall:
        pc <<= next_pc
        if2_pc <<= if1_pc
        if2_valid <<= ~io.mispred.valid

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
    # Stage IF1: Next PC prediction and selection
    #

    #
    # The predicted next PC comes from either the next sequential PC or the
    # predicted target address in the BTB. Note that pred_pc _can_ be wrong and
    # that's ok because the misspeculation will be caught later in the pipeline.
    #

    if1_pc <<= pc

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

    #
    # Stage IF2: Send icache request
    #

    io.icache.cpu_req.valid <<= ~io.mispred.valid
    io.icache.cpu_req.addr <<= if1_pc
    io.icache.cpu_req.rtype <<= access_rtype.w
    io.icache.cpu_req.read <<= True
    io.icache.cpu_stall <<= io.frontend_stall

    #
    # Stage IF3: icache will latch read data.
    #
    # N.B. The cache latches the output data it generates, which needs to
    # bypass the if_id register to keep from introducing an extra pipeline
    # stage.
    #

    io.if_id.pc <<= if2_pc
    io.if_id.valid <<= if2_valid & ~io.mispred.valid & ~io.icache.miss_stall
    io.inst <<= io.icache.cpu_resp.data(31, 0)

    NameSignals(locals())