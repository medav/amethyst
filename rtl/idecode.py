from dataclasses import dataclass
from contextlib import contextmanager

from atlas import *
from interfaces import *
from common import *

class Opcodes(object):
    LOAD = 0b0000011
    STORE = 0b0100011
    MADD = 0b1000011
    BRANCH = 0b1100011
    LOADFP = 0b0000111
    STOREFP = 0b0100111
    MSUB = 0b1000111
    JALR = 0b1100111
    CUSTOM0 = 0b0001011
    CUSTOM1 = 0b0101011
    NMSUB = 0b1001011
    MISCMEM = 0b0001111
    AMO = 0b0101111
    NMADD = 0b1001111
    JAL = 0b1101111
    OPIMM = 0b0010011
    OP = 0b0110011
    OPFP = 0b1010011
    SYSTEM = 0b1110011
    AUIPC = 0b0010111
    LUI = 0b0110111
    OPIMM32 = 0b0011011
    OP32 = 0b0111011
    CUSTOM2 = 0b1011011
    CUSTOM3 = 0b1111011

@dataclass
class Inst(object):
    # Data to match against
    opcode : int
    funct3 : int
    funct7 : int

    # Output control signals
    itype : int

    # EX control signals
    alu_src : int
    alu_op : int

    # MEM control signals
    branch : bool
    mem_write : bool
    mem_read : bool

    # WB control signals
    mem_to_reg : bool

instructions = {

    #
    # R-Type Instructions
    #

    'add': Inst(Opcodes.OP, 0b000, 0b0000000, ITypes.R, AluSrc.RS2, 0b10, False, False, False, False),
    'sub': Inst(Opcodes.OP, 0b000, 0b0100000, ITypes.R, AluSrc.RS2, 0b10, False, False, False, False),
    'sll': Inst(Opcodes.OP, 0b001, 0b0000000, ITypes.R, AluSrc.RS2, 0b10, False, False, False, False),
    'xor': Inst(Opcodes.OP, 0b100, 0b0000000, ITypes.R, AluSrc.RS2, 0b10, False, False, False, False),
    'srl': Inst(Opcodes.OP, 0b101, 0b0000000, ITypes.R, AluSrc.RS2, 0b10, False, False, False, False),
    'or': Inst(Opcodes.OP, 0b110, 0b0000000, ITypes.R, AluSrc.RS2, 0b10, False, False, False, False),
    'and': Inst(Opcodes.OP, 0b111, 0b0000000, ITypes.R, AluSrc.RS2, 0b10, False, False, False, False),
    # 'lr.d': Inst(Opcodes.OP, 0b011, 0b0001000, ITypes.R, AluSrc.RS2, 0b10, False, False, False, False),
    # 'sc.d': Inst(Opcodes.OP, 0b011, 0b0001100, ITypes.R, AluSrc.RS2, 0b10, False, False, False, False),

    #
    # I-Type Instructions
    #

    'lb': Inst(Opcodes.LOAD, 0b000, None, ITypes.I, AluSrc.RS2, 0b00, False, False, True, True),
    'lh': Inst(Opcodes.LOAD, 0b001, None, ITypes.I, AluSrc.RS2, 0b00, False, False, True, True),
    'lw': Inst(Opcodes.LOAD, 0b010, None, ITypes.I, AluSrc.RS2, 0b00, False, False, True, True),
    'ld': Inst(Opcodes.LOAD, 0b011, None, ITypes.I, AluSrc.RS2, 0b00, False, False, True, True),
    'lbu': Inst(Opcodes.LOAD, 0b100, None, ITypes.I, AluSrc.RS2, 0b00, False, False, True, True),
    'lhu': Inst(Opcodes.LOAD, 0b101, None, ITypes.I, AluSrc.RS2, 0b00, False, False, True, True),
    'lwu': Inst(Opcodes.LOAD, 0b110, None, ITypes.I, AluSrc.RS2, 0b00, False, False, True, True),
    'addi': Inst(Opcodes.OPIMM, 0b000, None, ITypes.I, AluSrc.IMM, 0b00, False, False, False, False),
    'slli': Inst(Opcodes.OPIMM, 0b001, 0b0000000, ITypes.I, AluSrc.IMM, 0b00, False, False, False, False),
    'xori': Inst(Opcodes.OPIMM, 0b100, None, ITypes.I, AluSrc.IMM, 0b00, False, False, False, False),
    'srli': Inst(Opcodes.OPIMM, 0b101, 0b0000000, ITypes.I, AluSrc.IMM, 0b00, False, False, False, False),
    'srai': Inst(Opcodes.OPIMM, 0b101, 0b0100000, ITypes.I, AluSrc.IMM, 0b00, False, False, False, False),
    'ori': Inst(Opcodes.OPIMM, 0b110, None, ITypes.I, AluSrc.IMM, 0b00, False, False, False, False),
    'andi': Inst(Opcodes.OPIMM, 0b111, None, ITypes.I, AluSrc.IMM, 0b00, False, False, False, False),
    'jalr': Inst(Opcodes.JALR, 0b000, None, ITypes.I, AluSrc.RS2, 0b00, False, False, False, False),

    #
    # S-Type Instructions
    #

    'sb': Inst(Opcodes.STORE, 0b000, None, ITypes.S, AluSrc.RS2, 0b00, False, True, False, False),
    'sh': Inst(Opcodes.STORE, 0b001, None, ITypes.S, AluSrc.RS2, 0b00, False, True, False, False),
    'sw': Inst(Opcodes.STORE, 0b010, None, ITypes.S, AluSrc.RS2, 0b00, False, True, False, False),
    'sd': Inst(Opcodes.STORE, 0b111, None, ITypes.S, AluSrc.RS2, 0b00, False, True, False, False),

    #
    # B-Type Instructions
    #

    'beq': Inst(Opcodes.BRANCH, 0b000, None, ITypes.B, AluSrc.RS2, 0b01, True, False, False, False),
    'bne': Inst(Opcodes.BRANCH, 0b001, None, ITypes.B, AluSrc.RS2, 0b01, True, False, False, False),
    'blt': Inst(Opcodes.BRANCH, 0b100, None, ITypes.B, AluSrc.RS2, 0b01, True, False, False, False),
    'bge': Inst(Opcodes.BRANCH, 0b101, None, ITypes.B, AluSrc.RS2, 0b01, True, False, False, False),
    'bltu': Inst(Opcodes.BRANCH, 0b110, None, ITypes.B, AluSrc.RS2, 0b01, True, False, False, False),
    'bgeu': Inst(Opcodes.BRANCH, 0b111, None, ITypes.B, AluSrc.RS2, 0b01, True, False, False, False),

    #
    # U-Type Instructions
    #

    'lui': Inst(Opcodes.LUI, None, None, ITypes.U, AluSrc.RS2, 0b00, False, False, False, False),

    #
    # J-Type Instructions
    #

    'jal': Inst(Opcodes.JAL, None, None, ITypes.J, AluSrc.RS2, 0b00, True, False, False, False),
}

#
# Helper functions to retrieve information from an instruction. Note that the
# only reason these are lambdas is because they're one-liners.
#

Opcode = lambda inst: inst(6, 0)
Rd = lambda inst: inst(11, 7)
Rs1 = lambda inst: inst(19, 15)
Rs2 = lambda inst: inst(24, 20)
Funct3 = lambda inst: inst(14, 12)
Funct7 = lambda inst: inst(31, 25)

def SetControlSignals(inst_spec, itype, ex_ctrl, mem_ctrl, wb_ctrl):
    """Update given control signals based on inst_spec."""

    itype <<= inst_spec.itype

    ex_ctrl.alu_src <<= inst_spec.alu_src
    ex_ctrl.alu_op <<= inst_spec.alu_op

    #
    # N.B. Atlas doesn't currently support bool literals as contant values so
    # just convert them to 1 / 0 here via Python ternarys.
    #

    mem_ctrl.branch <<= 1 if inst_spec.branch else 0
    mem_ctrl.mem_write <<= 1 if inst_spec.mem_write else 0
    mem_ctrl.mem_read <<= 1 if inst_spec.mem_read else 0

    wb_ctrl.mem_to_reg <<= 1 if inst_spec.mem_to_reg else 0

def Control(inst, itype, ex_ctrl, mem_ctrl, wb_ctrl):
    """Primary control logic for Geode."""

    #
    # opcode, funct3 and func7 are computed once here so that duplicate verilog
    # code isn't produced for every loop iteration below.
    #

    opcode = Opcode(inst)
    funct3 = Funct3(inst)
    funct7 = Funct7(inst)

    #
    # Atlas requires all wire signals to be fully initialized or it fails in the
    # emitter. An easy solution is to do a first assignment to a default value,
    # and later assignments will take precedence.
    #

    itype <<= 0

    ex_ctrl.alu_src <<= 0
    ex_ctrl.alu_op <<= 0
    ex_ctrl.funct3 <<= funct3
    ex_ctrl.funct7 <<= funct7

    mem_ctrl.branch <<= 0
    mem_ctrl.mem_write <<= 0
    mem_ctrl.mem_read <<= 0

    wb_ctrl.mem_to_reg <<= 0

    #
    # This part here really shows the power / advantage of Atlas's meta-
    # programming abilities. Each instruction declared above is considered, and
    # a "match" signal is produced. Upon a match, the control signals for that
    # function are assigned to the output of the idecode stage.
    #

    for name in instructions:
        inst_spec = instructions[name]
        print(f'Instruction {name}: {inst_spec}')

        opcode_match = opcode == inst_spec.opcode
        funct3_match = 1 if inst_spec.funct3 is None else funct3 == inst_spec.funct3
        funct7_match = 1 if inst_spec.funct7 is None else funct7 == inst_spec.funct7

        with opcode_match & funct3_match & funct7_match:
            SetControlSignals(inst_spec, itype, ex_ctrl, mem_ctrl, wb_ctrl)

def GenerateImmediate(inst, itype):
    imm = Wire(Bits(32))
    zero = Wire(Bits(1))
    zero <<= 0

    #
    # The immediate value is generated differently based on the decoded
    # instruction type. This logic essentially will produce all immediates in
    # parallel then select the result based on itype.
    #

    imm <<= 0

    with itype == ITypes.I:
        imm <<= Cat([
            Fill(inst(31, 31), 21),
            inst(30, 25),
            inst(24, 21),
            inst(20, 20)
        ])

    with itype == ITypes.S:
        imm <<= Cat([
            Fill(inst(31, 31), 21),
            inst(30, 25),
            inst(11, 7)
        ])

    with itype == ITypes.B:
        imm <<= Cat([
            Fill(inst(31, 31), 20),
            inst(7, 7),
            inst(30, 25),
            inst(11, 8),
            zero
        ])

    with itype == ITypes.U:
        imm <<= Cat([
            inst(31, 12),
            Fill(zero, 12)
        ])

    with itype == ITypes.J:
        imm <<= Cat([
            Fill(inst(31, 31), 12),
            inst(19, 12),
            inst(20, 20),
            inst(30, 25),
            inst(24, 21),
            zero
        ])

    #
    # N.B. Since RISC-V guarantees the most significant bit of the immediate is
    # always at isnt(31, 31), Sign extention can be computed in parallel /
    # independent of itype. The Cat statement below combines the sign extension
    # with the computed immediate value.
    #

    NameSignals(locals())
    return Cat([Fill(inst(31, 31), 32), imm])

@Module
def RegisterFile():
    """The primary register file for Geode.

    This register file contains two read and one write port.
    """

    io = Io({
        'r0_addr': Input(Bits(Log2Ceil(C['reg-count']))),
        'r1_addr': Input(Bits(Log2Ceil(C['reg-count']))),
        'w0_addr': Input(Bits(Log2Ceil(C['reg-count']))),
        'w0_data': Input(Bits(C['core-width'])),
        'w0_en' : Input(Bits(1)),
        'r0_data': Output(Bits(C['core-width'])),
        'r1_data': Output(Bits(C['core-width']))
    })

    reg_array = Reg(
        [Bits(C['core-width']) for _ in range(C['reg-count'])],
        reset_value=[0 for _ in range(C['reg-count'])])

    with io.r0_addr == 0:
        io.r0_data <<= 0
    with otherwise:
        io.r0_data <<= reg_array[io.r0_addr]

    with io.r1_addr == 0:
        io.r1_data <<= 0
    with otherwise:
        io.r1_data <<= reg_array[io.r1_addr]

    with (io.w0_addr != 0) & io.w0_en:
        reg_array[io.w0_addr] <<= io.w0_data

    NameSignals(locals())

@Module
def IDecodeStage():
    """The instruction decode stage for Geode.

    This stage consumes the instruction produced by the most recent imem access
    and produces control signals and a sign-extended immediate value. In
    addition, this module contains the register file and produces read values
    for register source data.
    """

    io = Io({
        'if_id': Input(if_id_bundle),
        'inst': Input(Bits(32)),
        'reg_write': Input(reg_write_bundle),
        'id_ex': Output(id_ex_bundle)
    })

    regfile = Instance(RegisterFile())

    itype = Wire(Bits(ITypes.bitwidth))

    regfile.r0_addr <<= Rs1(io.inst)
    regfile.r1_addr <<= Rs2(io.inst)

    regfile.w0_addr <<= io.reg_write.w_addr
    regfile.w0_en <<= io.reg_write.w_en
    regfile.w0_data <<= io.reg_write.w_data

    #
    # inst_data is metadata about the current instruction that is passed through
    # the pipeline unrelated to control signals. It's primary use is for hazard
    # detection and data forwarding.
    #

    io.id_ex.inst_data.inst <<= io.inst
    io.id_ex.inst_data.pc <<= io.if_id.pc
    io.id_ex.inst_data.rs1 <<= Rs1(io.inst)
    io.id_ex.inst_data.rs2 <<= Rs2(io.inst)
    io.id_ex.inst_data.rd <<= Rd(io.inst)

    #
    # Hook up the register read outputs.
    #

    io.id_ex.rs1_data <<= regfile.r0_data
    io.id_ex.rs2_data <<= regfile.r1_data

    #
    # Control is a Python function that produces the primary decode logic. It
    # matches against a set of known instructions to produce control signals for
    # later stages in the pipeline. The known instructions are encoded in the
    # 'instructions' variable above.
    #

    Control(
        io.inst,
        itype,
        io.id_ex.ex_ctrl,
        io.id_ex.mem_ctrl,
        io.id_ex.wb_ctrl)

    #
    # GenerateImmediate produces logic that consume the itype (instruction
    # type, which is R, I, S, B, U, or J) and produces the immediate value for
    # this instruction.
    #

    io.id_ex.imm <<= GenerateImmediate(io.inst, itype)

    NameSignals(locals())