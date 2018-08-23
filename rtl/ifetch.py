from atlas import *
from interfaces import *

from config import config as C

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
        'imem': Output(imem_bundle),
        'branch': Input(Bits(1)),
        'branch_target': Input(Bits(C['paddr-width']))
    })

    #
    # This is the program counter for Geode. It decides what instruction is
    # next to be executed.
    #

    pc = Reg(Bits(C['paddr-width']), reset_value=C['reset-addr'])

    #
    # The PC defaults to increment by 4 each cycle.
    #

    pc <<= pc + 4

    io.imem.r_addr <<= pc
    io.imem.r_en <<= 1

    #
    # It is assumed that the imem contains an internal latch that captures read
    # data on the rising edge. This means the read data can't be included in the
    # if_id register or it will be delayed by one cycle. Instead, the imem acts
    # as part of the if_id register and bypasses it to the idecode stage.
    #

    io.if_id.pc <<= pc
    io.inst <<= io.imem.r_data

    #
    # When a branch is in the mem stage, it will decide whether it is taken or
    # not. If it is, the branch and branch_target signals are used to update the
    # pc to change the control flow.
    #

    with io.branch:
        pc <<= io.branch_target

    NameSignals(locals())