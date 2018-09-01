from dataclasses import dataclass

from atlas import *
from interfaces import *
from instructions import *

import forward

from config import config as C

class BitOrReduceOperator(Operator):
    """Operator that reduces a bits signal via logic OR."""

    #
    # N.B. This is a good example of how extendable Atlas/Python is. It enables
    # user code to create new synthesizable operations that generate custom
    # Verilog code.
    #
    # Since Atlas doesn't currently have a good way of producing an OR reduction
    # tree, we can just make our own, here!
    #

    def __init__(self, bits):
        super().__init__('bitsum')
        self.bit_vec = [FilterFrontend(bits(i, i)) for i in range(bits.width)]
        self.result = CreateSignal(
            Bits(1),
            name='result',
            parent=self,
            frontend=False)

    def Declare(self):
        VDeclWire(self.result)

    def Synthesize(self):
        add_str = ' | '.join([VName(bit) for bit in self.bit_vec])
        VAssignRaw(VName(self.result), add_str)

@OpGen(default='result')
def BitOrReduce(bits):
    return BitOrReduceOperator(bits)

@Module
def ArithmeticLogicUnit():
    """The primary arithmetic/logic unit for Geode."""

    io = Io({
        'op0': Input(Bits(C['core-width'])),
        'op1': Input(Bits(C['core-width'])),
        'alu_inst': Input(Bits(AluInsts.width)),
        'result': Output(Bits(C['core-width'])),
        'flags': Output(alu_flags)
    })

    zero = Wire(Bits(C['core-width']))
    shift_op = Wire(Bits(1))

    #
    # To make checking for overflow easy, all arithmetic operations are
    # performed on 2 x core-width (sign extended) data.
    #

    op0_ex = Cat([zero, io.op0])
    op1_ex = Cat([zero, io.op1])

    #
    # N.B. For all RV32I instructions, the shamt is actually only 5 bits. For
    # 64 bit instructions, it's 6 bits. It's safe to always extract a 6-bit
    # shamt because 32 bit instructions all coincidentally leave io.op1(6)
    # set to zero, anyway.
    #

    shamt = io.op1(5, 0)

    #
    # For a real ALU, add / sub operations would likely be combined to only use
    # a single adder, negating the second operand for subtractions.
    #

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

    #
    # The following essentially produces a mux that selects an output produced
    # by this ALU based on the inst requested.
    #

    with io.alu_inst == AluInsts.AND:
        result <<= and_result

    with io.alu_inst == AluInsts.OR:
        result <<= or_result

    with io.alu_inst == AluInsts.ADD:
        result <<= add_result

    with io.alu_inst == AluInsts.SUB:
        result <<= sub_result

    with io.alu_inst == AluInsts.SLL:
        result <<= Cat([zero, sll_result])

    with io.alu_inst == AluInsts.SRL:
        result <<= Cat([zero, srl_result])

    NameSignals(locals())

def OptionalMatch(default, pattern, signal):
    if pattern is None:
        return default
    else:
        return signal == pattern

def AluControl(alu_inst, alu_op, funct7, funct3):
    """Produce an appropriate alu_inst for the given op, funct3 and funct7.

    N.B. This function is very similar to how the idecode control works.
    """

    alu_op0 = alu_op(0, 0)
    alu_op1 = alu_op(1, 1)

    alu_inst <<= 0

    #
    # N.B. Atlas doesn't currently support reflected operations with constant
    # values (e.g. `1 & some_wire`). Because of this, the constant value 1
    # needs to be set to a wire to be used in the loop below.
    #

    true_w = Wire(Bits(1))
    true_w <<= 1

    NameSignals(locals())

    for inst_spec in alu_instructions:

        alu_op0_match = OptionalMatch(true_w, inst_spec.alu_op0, alu_op0)
        alu_op1_match = OptionalMatch(true_w, inst_spec.alu_op1, alu_op1)
        funct3_match = OptionalMatch(true_w, inst_spec.funct3, funct3)
        funct7_match = OptionalMatch(true_w, inst_spec.funct7, funct7)

        with alu_op0_match & alu_op1_match & funct3_match & funct7_match:
            alu_inst <<= inst_spec.alu_inst



@Module
def ExecuteStage():
    """The execute stage for Geode.

    This stage contains the primary ALU for Geode. It takes in register values
    produced in the previous stage (or forwarded values when necessary) to
    perform operations on.

    Additionally, it produces the branch target for branch instructions.
    """

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