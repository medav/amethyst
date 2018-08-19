from atlas import *
from interfaces import *
from common import *

from config import config as C

class AluInst(object):
    width = 4

    AND = 0b0000
    OR = 0b0001
    ADD = 0b0010
    SUB = 0b0110


@Module
def ArithmeticLogicUnit():
    io = Io({
        'op0': Input(Bits(C['core-width'])),
        'op1': Input(Bits(C['core-width'])),
        'alu_inst': Input(Bits(AluInst.width)),
        'result': Output(Bits(C['core-width']))
    })

    and_result = io.op0 & io.op1
    or_result = io.op0 | io.op1
    add_result = io.op0 + io.op1
    sub_result = io.op0 - io.op1

    io.result <<= 0

    with io.alu_inst == AluInst.AND:
        io.result <<= and_result

    with io.alu_inst == AluInst.OR:
        io.result <<= or_result

    with io.alu_inst == AluInst.ADD:
        io.result <<= add_result

    with io.alu_inst == AluInst.SUB:
        io.result <<= sub_result

    NameSignals(locals())

@Module
def ExecuteStage():
    io = Io({
        'id_ex': Input(id_ex_bundle),
        'ex_mem': Output(ex_mem_bundle)
    })

    io.ex_mem.mem_ctrl <<= io.id_ex.mem_ctrl
    io.ex_mem.wb_ctrl <<= io.id_ex.wb_ctrl

    alu = Instance(ArithmeticLogicUnit())

    alu.op0 <<= io.id_ex.rs1_data
    alu.op1 <<= io.id_ex.rs2_data
    alu.alu_inst <<= AluInst.ADD

    io.ex_mem.alu_result <<= alu.result

    NameSignals(locals())