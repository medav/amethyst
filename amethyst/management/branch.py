from atlas import *
from ..support import *

@Module
def BranchUnit():
    io = Io({
        'mem_pc': Input(Bits(C['paddr-width'])),
        'ex_pc': Input(Bits(C['paddr-width'])),
        'branch': Input({
            'valid': Bits(1),
            'taken': Bits(1),
            'target': Bits(C['paddr-width']),
            'is_return': Bits(1),
        }),
        'mispred': Output(mispred_bundle)
    })

    mispred = Reg(mispred_bundle, reset_value=mispred_bundle_reset)

    mispred.valid <<= False

    with (io.branch.target != io.ex_pc) & io.branch.valid:
        mispred.valid <<= True
        mispred.pc <<= io.mem_pc
        mispred.target <<= io.branch.target
        mispred.taken <<= io.branch.taken
        mispred.is_return <<= io.branch.is_return

    io.mispred <<= mispred

    NameSignals(locals())

