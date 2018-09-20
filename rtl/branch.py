from atlas import *
from interfaces import *

from config import *

@Module
def BranchUnit():
    io = Io({
        'mem_pc': Input(Bits(C['paddr-width'])),
        'ex_pc': Input(Bits(C['paddr-width'])),
        'branch': Input({
            'taken': Bits(1),
            'target': Bits(C['paddr-width']),
            'is_return': Bits(1),
        }),
        'misspec': Output(misspec_bundle)
    })

    misspec = Reg(misspec_bundle, reset_value=misspec_bundle_reset)

    misspec.valid <<= False

    with io.branch.target != io.ex_pc:
        misspec.valid <<= True
        misspec.pc <<= io.mem_pc
        misspec.target <<= io.branch.target
        misspec.taken <<= io.branch.taken
        misspec.is_return <<= io.branch.is_return

    NameSignals(locals())

