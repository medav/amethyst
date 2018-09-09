from atlas import *
from interfaces import *

from config import config as C

from icache import ICache

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
        'imem': Output({
            'read': mem_read_bundle
        }),
        'branch': Input(Bits(1)),
        'branch_target': Input(Bits(C['paddr-width']))
    })

    icache = Instance(ICache())

    #
    # This is the program counter for Geode. It decides what instruction is
    # next to be executed.
    #

    pc = Reg(Bits(C['paddr-width']), reset_value=C['reset-addr'])

    #
    # The PC defaults to increment by 4 each cycle.
    #

    pc <<= pc + 4
    icache.cpu_req <<= pc

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
    io.if_id.valid <<= ~io.branch & ~icache.cpu_resp.miss
    io.inst <<= icache.cpu_resp.data

    #
    # When a branch is in the mem stage, it will decide whether it is taken or
    # not. If it is, the branch and branch_target signals are used to update the
    # pc to change the control flow.
    #

    with io.branch:
        pc <<= io.branch_target

    NameSignals(locals())