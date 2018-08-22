from atlas import *
from interfaces import *
from common import *

from config import config as C


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
        'dmem': Output(dmem_bundle),
        'branch': Output(Bits(1)),
        'branch_target': Output(Bits(C['paddr-width'])),
        'mem_wb': Output(mem_wb_bundle),
        'read_data': Output(Bits(C['core-width']))
    })

    io.mem_wb.wb_ctrl <<= io.ex_mem.wb_ctrl
    io.mem_wb.inst_data <<= io.ex_mem.inst_data
    io.mem_wb.alu_result <<= io.ex_mem.alu_result

    io.branch <<= io.ex_mem.mem_ctrl.branch
    io.branch_target <<= io.ex_mem.branch_target

    io.dmem.r_addr <<= io.ex_mem.alu_result
    io.dmem.r_en <<= io.ex_mem.mem_ctrl.mem_read

    io.dmem.w_addr <<= io.ex_mem.alu_result
    io.dmem.w_data <<= io.ex_mem.rs2_data
    io.dmem.w_en <<= io.ex_mem.mem_ctrl.mem_write

    io.read_data <<= io.dmem.r_data

    NameSignals(locals())