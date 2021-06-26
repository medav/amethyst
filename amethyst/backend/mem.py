from atlas import *
from ..support import *

branch_types = [
    BranchType.EQ,
    BranchType.NEQ,
    BranchType.LT,
    BranchType.GEQ,
    BranchType.LTU,
    BranchType.GEQU
]

branch_resolve_table = {
    BranchType.EQ: lambda flags: flags.zero,
    BranchType.NEQ: lambda flags: ~flags.zero,
    BranchType.LT: lambda flags: flags.sign,
    BranchType.GEQ: lambda flags: ~flags.sign,
    BranchType.LTU: lambda flags: flags.overflow,
    BranchType.GEQU: lambda flags: ~flags.overflow,
}

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
        'branch': Output({
            'valid': Bits(1),
            'taken': Bits(1),
            'target': Bits(C['paddr-width']),
            'is_return': Bits(1),
        }),
        'mem_wb': Output(mem_wb_bundle)
    })

    io.mem_wb.ctrl <<= io.ex_mem.ctrl
    io.mem_wb.alu_result <<= io.ex_mem.alu_result

    #
    # If this is a branch instruction, the ctrl.mem.branch signal is set. Pass
    # it along here (it will cause the PC to be updated and preceding
    # instructions to be flushed).
    #

    is_ctrl_change = io.ex_mem.ctrl.mem.branch | io.ex_mem.ctrl.mem.jal
    io.branch.valid <<= io.ex_mem.ctrl.valid & is_ctrl_change

    taken = Wire(Bits(1))
    taken <<= False
    io.branch.taken <<= taken | io.ex_mem.ctrl.mem.jal

    for ty in branch_types:
        with io.ex_mem.ctrl.mem.branch_type == ty:
            taken <<= branch_resolve_table[ty](
                io.ex_mem.alu_flags)

    with (io.ex_mem.ctrl.mem.branch & taken) | io.ex_mem.ctrl.mem.jal:
        io.branch.target <<= io.ex_mem.branch_target
    with otherwise:
        io.branch.target <<= io.ex_mem.ctrl.pc + 4

    io.branch.is_return <<= False

    NameSignals(locals())