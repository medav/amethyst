from atlas import *
from ..support import *

@Module
def WritebackStage():
    """The writeback stage for Geode.

    This stage selects register write data and address and produces signals for
    the reg_write interface that gets routed to the register file.
    """

    io = Io({
        'mem_wb': Input(mem_wb_bundle),
        'mem_read_data': Input(Bits(C['core-width'])),
        'reg_write': Output(reg_write_bundle)
    })

    io.reg_write.w_addr <<= Rd(io.mem_wb.ctrl.inst)

    #
    # Register write data can come from either the result of the ex stage (the
    # alu) or the mem stage (the dmem).
    #

    with io.mem_wb.ctrl.wb.mem_to_reg:
        io.reg_write.w_data <<= io.mem_read_data
    with otherwise:
        io.reg_write.w_data <<= io.mem_wb.alu_result

    #
    # Currently, the register file is set to always write. Instructions that do
    # not update a register simply set their rd to zero (which is ignored).
    #

    io.reg_write.w_en <<= io.mem_wb.ctrl.wb.write_reg & io.mem_wb.ctrl.valid

    NameSignals(locals())