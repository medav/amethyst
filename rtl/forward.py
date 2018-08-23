from atlas import *
from interfaces import *

from config import config as C

fwd = Enum(['none', 'mem', 'wb'])

def ForwardReg(rs, mem_reg_write, mem_rd, wb_reg_write, wb_rd, fwd_select):
    """Forward logic for a source register."""

    fwd_select <<= fwd.none

    #
    # Detect whether the mem or wb stages are producing a new value for the
    # source register specified by "rs".
    #

    mem_match = mem_reg_write & (mem_rd != 0) & (mem_rd == rs)
    wb_match = wb_reg_write & (wb_rd != 0) & (wb_rd == rs)

    #
    # The logic here is carefully crafted. A match with mem_stage needs to take
    # precedence over a match with the writeback stage to ensure the most
    # recent version of the register's value.
    #

    with mem_match:
        fwd_select <<= fwd.mem

    with otherwise:
        with wb_match:
            fwd_select <<= fwd.wb

@Module
def ForwardUnit():
    """Forwarding unit for Geode.

    This module consumes information from the pipeline to decide when data
    forwarding is necessary to maintain correct execution.
    """

    io = Io({
        'ex_rs1': Input(Bits(Log2Ceil(C['reg-count']))),
        'ex_rs2': Input(Bits(Log2Ceil(C['reg-count']))),
        'mem_reg_write': Input(Bits(1)),
        'mem_rd': Input(Bits(Log2Ceil(C['reg-count']))),
        'wb_reg_write': Input(Bits(1)),
        'wb_rd': Input(Bits(Log2Ceil(C['reg-count']))),
        'fwd1_select': Output(Bits(fwd.bitwidth)),
        'fwd2_select': Output(Bits(fwd.bitwidth)),
    })

    #
    # Here's a good example of metaprogramming in Atlas/Python. Since the logic
    # for forwarding registers for rs1 and rs2 is essentially the same, the
    # logic can be collapsed into one (Python) function that generates this
    # logic.
    #

    ForwardReg(
        io.ex_rs1,
        io.mem_reg_write,
        io.mem_rd,
        io.wb_reg_write,
        io.wb_rd,
        io.fwd1_select
    )

    ForwardReg(
        io.ex_rs2,
        io.mem_reg_write,
        io.mem_rd,
        io.wb_reg_write,
        io.wb_rd,
        io.fwd2_select
    )

    NameSignals(locals())