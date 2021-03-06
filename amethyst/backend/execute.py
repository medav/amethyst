from dataclasses import dataclass

from atlas import *
from ..support import *
from ..management import forward

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

    and_result = io.op0 & io.op1
    or_result = io.op0 | io.op1
    add_result = io.op0 + io.op1
    sub_result = io.op0 - io.op1
    sll_result = io.op0 << shamt
    srl_result = io.op0 >> shamt

    result = Wire(Bits(C['core-width']))
    io.result <<= result

    result <<= 0

    io.flags.zero <<= (result == 0)
    io.flags.sign <<= result(C['core-width'] - 1, C['core-width'] - 1)
    io.flags.overflow <<= add_result(C['core-width'], C['core-width'])

    #
    # The following essentially produces a mux that selects an output produced
    # by this ALU based on the inst requested.
    #

    with io.alu_inst == AluInsts.AND:
        result <<= and_result

    with io.alu_inst == AluInsts.OR:
        result <<= or_result

    with io.alu_inst == AluInsts.ADD:
        result <<= add_result(C['core-width'] - 1, 0)

    with io.alu_inst == AluInsts.SUB:
        result <<= sub_result

    with io.alu_inst == AluInsts.SLL:
        result <<= sll_result

    with io.alu_inst == AluInsts.SRL:
        result <<= srl_result

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

    for inst_spec in alu_instructions:
        alu_op_match = OptionalMatch(true_w, inst_spec.alu_op, alu_op)
        alu_op0_match = OptionalMatch(true_w, inst_spec.alu_op0, alu_op0)
        alu_op1_match = OptionalMatch(true_w, inst_spec.alu_op1, alu_op1)
        funct3_match = OptionalMatch(true_w, inst_spec.funct3, funct3)
        funct7_match = OptionalMatch(true_w, inst_spec.funct7, funct7)

        with alu_op_match & alu_op0_match & alu_op1_match & funct3_match & funct7_match:
            alu_inst <<= inst_spec.alu_inst

    NameSignals(locals())

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
        'rs1_data': Input(Bits(C['core-width'])),
        'rs2_data': Input(Bits(C['core-width'])),
        'fwd': Input({
            'select1': Bits(forward.fwd.bitwidth),
            'select2': Bits(forward.fwd.bitwidth),
            'mem_data': Bits(C['core-width']),
            'wb_data': Bits(C['core-width'])
        }),
        'mispred': Input(Bits(1)),
        'dcache': Output({
            'cpu_req': cpu_cache_req
        }),
        'ex_mem': Output(ex_mem_bundle)
    })

    io.ex_mem.ctrl <<= io.id_ex.ctrl

    alu = Instance(ArithmeticLogicUnit())

    #
    # Branch Target Generation
    #

    io.ex_mem.branch_target <<= io.id_ex.ctrl.pc + io.id_ex.imm

    with io.id_ex.ctrl.ex.jalr:
        io.ex_mem.branch_target <<= alu.result

    #
    # Forwarding Logic
    #

    rs1_fwd = Wire(Bits(C['core-width']))
    rs2_fwd = Wire(Bits(C['core-width']))

    rs1_fwd <<= io.rs1_data

    with io.fwd.select1 == forward.fwd.mem:
        rs1_fwd <<= io.fwd.mem_data

    with io.fwd.select1 == forward.fwd.wb:
        rs1_fwd <<= io.fwd.wb_data

    rs2_fwd <<= io.rs2_data

    with io.fwd.select2 == forward.fwd.mem:
        rs2_fwd <<= io.fwd.mem_data

    with io.fwd.select2 == forward.fwd.wb:
        rs2_fwd <<= io.fwd.wb_data

    #
    # ALU Source Selection
    #

    alu.op0 <<= rs1_fwd

    with io.id_ex.ctrl.ex.alu_src == AluSrc.RS2:
        alu.op1 <<= rs2_fwd
    with otherwise:
        alu.op1 <<= io.id_ex.imm

    #
    # ALU Instruction Selection
    #

    AluControl(
        alu.alu_inst,
        io.id_ex.ctrl.ex.alu_op,
        io.id_ex.ctrl.ex.funct7,
        io.id_ex.ctrl.ex.funct3)

    #
    # Data Output Connections
    #

    io.ex_mem.rs2_data <<= io.rs2_data

    with io.id_ex.ctrl.ex.lui:
        io.ex_mem.alu_result <<= io.id_ex.imm
    with otherwise:
        io.ex_mem.alu_result <<= alu.result

    io.ex_mem.alu_flags <<= alu.flags

    #
    # The execute stage is responsible for sending the dcache memory requests.
    #

    io.dcache.cpu_req.valid <<= \
        io.id_ex.ctrl.valid & \
        (io.id_ex.ctrl.mem.mem_read | io.id_ex.ctrl.mem.mem_write) & \
        ~io.mispred

    io.dcache.cpu_req.addr <<= alu.result
    io.dcache.cpu_req.rtype <<= access_rtype.d
    io.dcache.cpu_req.read <<= io.id_ex.ctrl.mem.mem_read

    NameSignals(locals())
