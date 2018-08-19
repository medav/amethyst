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

class BitSumOperator(AtlasOperator):
    def __init__(self, bits):
        super().__init__('bitsum')
        self.bit_vec = [bits(i, i) for i in range(bits.width)]
        self.RegisterSignal(Signal(Bits(Log2Ceil(bits.width))))

    def Declare(self):
        VDeclWire(self.result)

    def Synthesize(self):
        add_str = ' + '.join([VName(bit) for bit in self.bit_vec])
        VAssignRaw(VName(self.result), add_str)

def BitSum(bits):
    return BitSumOperator(bits).result

@Module
def ArithmeticLogicUnit():
    io = Io({
        'op0': Input(Bits(C['core-width'])),
        'op1': Input(Bits(C['core-width'])),
        'alu_inst': Input(Bits(AluInst.width)),
        'result': Output(Bits(C['core-width'])),
        'flags': Output(alu_flags)
    })

    zero = Wire(Bits(C['core-width']))

    op0_ex = Cat([zero, io.op0])
    op1_ex = Cat([zero, io.op1])

    and_result = op0_ex & op1_ex
    or_result = op0_ex | op1_ex
    add_result = op0_ex + op1_ex
    sub_result = op0_ex - op1_ex


    result = Wire(Bits(C['core-width'] * 2))
    io.result <<= result(C['core-width'] - 1, 0)

    result <<= 0

    io.flags.zero <<= (result == 0)
    io.flags.sign <<= result(result.width - 1, result.width - 1)
    io.flags.overflow <<= BitSum(result(result.width - 1, C['core-width'])) != 0

    with io.alu_inst == AluInst.AND:
        result <<= and_result

    with io.alu_inst == AluInst.OR:
        result <<= or_result

    with io.alu_inst == AluInst.ADD:
        result <<= add_result

    with io.alu_inst == AluInst.SUB:
        result <<= sub_result

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

    io.ex_mem.rs2_data <<= io.id_ex.rs2_data
    io.ex_mem.alu_result <<= alu.result
    io.ex_mem.alu_flags <<= alu.flags

    NameSignals(locals())