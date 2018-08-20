from dataclasses import dataclass

from atlas import *
from interfaces import *
from common import *

import forward

from config import config as C

class AluInst(object):
    width = 4

    AND = 0b0000
    OR = 0b0001
    ADD = 0b0010
    SUB = 0b0110
    XOR = 0b0101
    SRL = 0b1000
    SLL = 0b1001

class BitOrReduceOperator(AtlasOperator):
    def __init__(self, bits):
        super().__init__('bitsum')
        self.bit_vec = [bits(i, i) for i in range(bits.width)]
        self.RegisterSignal(Signal(Bits(1)))

    def Declare(self):
        VDeclWire(self.result)

    def Synthesize(self):
        add_str = ' | '.join([VName(bit) for bit in self.bit_vec])
        VAssignRaw(VName(self.result), add_str)

def BitOrReduce(bits):
    return BitOrReduceOperator(bits).result

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
    shift_op = Wire(Bits(1))

    op0_ex = Cat([zero, io.op0])
    op1_ex = Cat([zero, io.op1])

    # TODO: Comment here about why this works
    shamt = io.op1(5, 0)

    and_result = op0_ex & op1_ex
    or_result = op0_ex | op1_ex
    add_result = op0_ex + op1_ex
    sub_result = op0_ex - op1_ex
    sll_result = io.op0 << shamt
    srl_result = io.op0 >> shamt

    result = Wire(Bits(C['core-width'] * 2))
    io.result <<= result(C['core-width'] - 1, 0)

    result <<= 0

    io.flags.zero <<= (result == 0)
    io.flags.sign <<= result(result.width - 1, result.width - 1)
    io.flags.overflow <<= BitOrReduce(result(result.width - 1, C['core-width']))

    with io.alu_inst == AluInst.AND:
        result <<= and_result

    with io.alu_inst == AluInst.OR:
        result <<= or_result

    with io.alu_inst == AluInst.ADD:
        result <<= add_result

    with io.alu_inst == AluInst.SUB:
        result <<= sub_result

    with io.alu_inst == AluInst.SLL:
        result <<= Cat([zero, sll_result])

    with io.alu_inst == AluInst.SRL:
        result <<= Cat([zero, srl_result])

    NameSignals(locals())

@dataclass
class AluInstSpec(object):
    # Inputs to match
    alu_op0 : int
    alu_op1 : int
    funct7 : int
    funct3 : int

    # What to set alu_inst to
    alu_inst : int

alu_instructions = [
    AluInstSpec(0, 0, None, None, AluInst.ADD),
    AluInstSpec(None, 0, None, None, AluInst.SUB),

    AluInstSpec(1, None, 0b0000000, 0b000, AluInst.ADD),
    AluInstSpec(1, None, 0b0000000, 0b001, AluInst.SLL),
    AluInstSpec(1, None, 0b0000000, 0b100, AluInst.XOR),
    AluInstSpec(1, None, 0b0000000, 0b101, AluInst.SRL),
    AluInstSpec(1, None, 0b0100000, 0b000, AluInst.SUB),
    AluInstSpec(1, None, 0b0000000, 0b111, AluInst.AND),
    AluInstSpec(1, None, 0b0000000, 0b110, AluInst.OR),
]

def AluControl(alu_inst, alu_op, funct7, funct3):
    alu_op0 = alu_op(0, 0)
    alu_op1 = alu_op(1, 1)

    alu_inst <<= 0

    true_wire = Wire(Bits(1))
    true_wire <<= 1

    for inst_spec in alu_instructions:

        alu_op0_match = true_wire if inst_spec.alu_op0 is None else alu_op0 == inst_spec.alu_op0
        alu_op1_match = true_wire if inst_spec.alu_op1 is None else alu_op1 == inst_spec.alu_op1
        funct3_match = true_wire if inst_spec.funct3 is None else funct3 == inst_spec.funct3
        funct7_match = true_wire if inst_spec.funct7 is None else funct7 == inst_spec.funct7

        with alu_op0_match & alu_op1_match & funct3_match & funct7_match:
            alu_inst <<= inst_spec.alu_inst

    NameSignals(locals())

@Module
def ExecuteStage():
    io = Io({
        'id_ex': Input(id_ex_bundle),
        'fwd1_select': Input(Bits(forward.fwd.bitwidth)),
        'fwd2_select': Input(Bits(forward.fwd.bitwidth)),
        'fwd_mem_data': Input(Bits(C['core-width'])),
        'fwd_wb_data': Input(Bits(C['core-width'])),
        'ex_mem': Output(ex_mem_bundle)
    })

    io.ex_mem.mem_ctrl <<= io.id_ex.mem_ctrl
    io.ex_mem.wb_ctrl <<= io.id_ex.wb_ctrl
    io.ex_mem.inst_data <<= io.id_ex.inst_data

    alu = Instance(ArithmeticLogicUnit())

    #
    # Branch Target Generation
    #

    io.ex_mem.branch_target <<= io.id_ex.inst_data.pc + io.id_ex.imm

    #
    # Forwarding Logic
    #

    rs1_fwd = Wire(Bits(C['core-width']))
    rs2_fwd = Wire(Bits(C['core-width']))

    rs1_fwd <<= io.id_ex.rs1_data

    with io.fwd1_select == forward.fwd.mem:
        rs1_fwd <<= io.fwd_mem_data

    with io.fwd1_select == forward.fwd.wb:
        rs1_fwd <<= io.fwd_wb_data

    rs2_fwd <<= io.id_ex.rs1_data

    with io.fwd2_select == forward.fwd.mem:
        rs2_fwd <<= io.fwd_mem_data

    with io.fwd2_select == forward.fwd.wb:
        rs2_fwd <<= io.fwd_wb_data

    #
    # ALU Source Selection
    #

    alu.op0 <<= rs1_fwd

    with io.id_ex.ex_ctrl.alu_src == AluSrc.RS2:
        alu.op1 <<= rs2_fwd
    with otherwise:
        alu.op1 <<= io.id_ex.imm

    #
    # ALU Instruction Selection
    #

    AluControl(
        alu.alu_inst,
        io.id_ex.ex_ctrl.alu_op,
        io.id_ex.ex_ctrl.funct7,
        io.id_ex.ex_ctrl.funct3)

    #
    # Data Output Connections
    #

    io.ex_mem.rs2_data <<= io.id_ex.rs2_data
    io.ex_mem.alu_result <<= alu.result
    io.ex_mem.alu_flags <<= alu.flags

    NameSignals(locals())