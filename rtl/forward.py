from atlas import *
from interfaces import *
from common import *

from config import config as C

fwd = Enum(['none', 'mem', 'wb'])

def ForwardReg(rs, mem_reg_write, mem_rd, wb_reg_write, wb_rd, fwd_select):
    fwd_select <<= fwd.none

    wb_match = wb_reg_write & (wb_rd != 0) & (wb_rd == rs)
    mem_match = mem_reg_write & (mem_rd != 0) & (mem_rd == rs)

    with mem_match:
        fwd_select <<= fwd.mem

    with otherwise:
        with wb_match:
            fwd_select <<= fwd.wb

@Module
def ForwardUnit():
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

    ForwardReg(io.ex_rs1, io.mem_reg_write, io.mem_rd, io.wb_reg_write, io.wb_rd, io.fwd1_select)
    ForwardReg(io.ex_rs2, io.mem_reg_write, io.mem_rd, io.wb_reg_write, io.wb_rd, io.fwd2_select)

    NameSignals(locals())