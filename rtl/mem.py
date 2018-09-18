from atlas import *
from interfaces import *

from config import *

@Module
def MemStage():
    """The mem access stage for Geode.

    This stage consumes the alu result and ctrl.mem signals to produce a
    memory read or write (if required) so that the memory data can be passed on
    to the writeback stage.

    This stage also passes on the original alu_result to be used when the
    current instruction is not a memory access.
    """

    io = Io({
        'ex_mem': Input(ex_mem_bundle),
        'branch': Output(Bits(1)),
        'branch_target': Output(Bits(C['paddr-width'])),
        'mem_wb': Output(mem_wb_bundle)
    })

    io.mem_wb.ctrl <<= io.ex_mem.ctrl
    io.mem_wb.alu_result <<= io.ex_mem.alu_result

    #
    # If this is a branch instruction, the ctrl.mem.branch signal is set. Pass
    # it along here (it will cause the PC to be updated and preceding
    # instructions to be flushed).
    #

    io.branch <<= io.ex_mem.ctrl.mem.branch
    io.branch_target <<= io.ex_mem.branch_target

    NameSignals(locals())