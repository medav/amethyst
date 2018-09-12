from atlas import *
from interfaces import *

from config import *

@Module
def MemStage():
    """The mem access stage for Geode.

    This stage consumes the alu result and mem_ctrl signals to produce a
    memory read or write (if required) so that the memory data can be passed on
    to the writeback stage.

    This stage also passes on the original alu_result to be used when the
    current instruction is not a memory access.
    """

    io = Io({
        'ex_mem': Input(ex_mem_bundle),
        'dmem': Output({
            'read_req': mem_read_request,
            'read_resp': mem_read_response,
            'write_req': mem_write_request
        }),
        'branch': Output(Bits(1)),
        'branch_target': Output(Bits(paddr_width)),
        'mem_wb': Output(mem_wb_bundle),
        'read_data': Output(Bits(core_width))
    })

    io.mem_wb.wb_ctrl <<= io.ex_mem.wb_ctrl
    io.mem_wb.inst_data <<= io.ex_mem.inst_data
    io.mem_wb.alu_result <<= io.ex_mem.alu_result

    #
    # If this is a branch instruction, the mem_ctrl.branch signal is set. Pass
    # it along here (it will cause the PC to be updated and preceding
    # instructions to be flushed).
    #

    io.branch <<= io.ex_mem.mem_ctrl.branch
    io.branch_target <<= io.ex_mem.branch_target

    #
    # dmem addresses are produces by the ALU in the ex stage. Write data comes
    # from the second source register (if applicable).
    #

    io.dmem.read.r_addr <<= io.ex_mem.alu_result
    io.dmem.read.r_en <<= io.ex_mem.mem_ctrl.mem_read

    io.dmem.write.w_addr <<= io.ex_mem.alu_result
    io.dmem.write.w_data <<= io.ex_mem.rs2_data
    io.dmem.write.w_en <<= io.ex_mem.mem_ctrl.mem_write

    #
    # Similar to the imem, the dmem is assumed to have an internal latch that
    # captures read data for the next cycle. So likewise, dmem data can't be
    # passed through the mem_wb reg or it will be delayed by a cycle.
    #

    io.read_data <<= io.dmem.read.r_data

    NameSignals(locals())