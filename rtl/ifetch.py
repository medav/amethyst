from atlas import *
from interfaces import *

from config import *

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
            'cpu_req': cpu_cache_req,
            'cpu_stall': Bits(1),
            'miss_stall': Flip(Bits(1)),
            'cpu_resp': Flip(cpu_cache_resp)
        }),
        'misspec': Input({
            'valid': Bits(1),
            'pc': Bits(C['paddr-width']),
            'target': Bits(C['paddr-width']),
            'taken': Bits(1),
            'is_return': Bits(1)
        }),
        'hazard_stall': Input(Bits(1))
    })

    bpred = Instance(BranchPredictor())
    btb = Instance(BranchTargetBuffer())
    ras = Instance(ReturnAddressStack())

    ras.pop.valid <<= False

    pc = Reg(Bits(C['paddr-width']), reset_value=C['reset-addr'])
    pc_valid = Reg(Bits(1), reset_value=True)
    pred_pc = Wire(Bits(C['paddr-width']))
    next_pc = Wire(Bits(C['paddr-width']))

    s2_pc = Reg(Bits(C['paddr-width']), reset_value=0)
    s2_valid = Reg(Bits(1), reset_value=False)

    s3_pc = Reg(Bits(C['paddr-width']), reset_value=0)
    s3_valid = Reg(Bits(1), reset_value=False)

    with ~io.icache.miss_stall & ~io.hazard_stall:
        pc <<= next_pc
        s2_pc <<= pc
        s2_valid <<= pc_valid

        s3_pc <<= pc
        s3_valid <<= s2_valid

    #
    # Stage 1: Next PC prediction and selection
    #

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
    # Stage 2: Send icache request
    #

    io.icache.cpu_req.valid <<= True
    io.icache.cpu_req.addr <<= pc
    io.icache.cpu_req.rtype <<= access_rtype.w
    io.icache.cpu_req.read <<= True
    io.icache.cpu_stall <<= io.hazard_stall

    #
    # Stage 3: Wait for icache
    #

    # Nothing happens here since it's entirely in the cache.

    #
    # Stage 4: Emit instruction to decode stage
    #
    # N.B. This is overlapped with decode
    #

    io.if_id.pc <<= s3_pc
    io.if_id.valid <<= s3_valid & ~io.icache.miss_stall
    io.if_id.inst <<= io.icache.cpu_resp.data

    NameSignals(locals())