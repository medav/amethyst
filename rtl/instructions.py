from dataclasses import dataclass
from contextlib import contextmanager

from atlas import *
from interfaces import *

from config import *

AluSrc = Enum(['RS2', 'IMM'])
ITypes = Enum(['R', 'I', 'S', 'B', 'U', 'J'])

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

@dataclass(frozen=True)
class Pattern(object):
    """Instruction pattern record.

    The values in this class are used to detect when a particular instruction
    is matched (and its related control values should be set).

    N.B. Some instructions do not require a match for funct3 and funct7 so in
    the following code, some instructions mark funct3 and/or funct7 as None
    which will cause that field to be ignored when matching.
    """

    opcode : int
    funct3 : int
    funct7 : int

@dataclass(frozen=True)
class ExCtrl(object):
    """Execute control signals bundle."""

    alu_src : int
    alu_op : int

    def Literal(self):
        return {
            'alu_src': self.alu_src,
            'alu_op': self.alu_op
        }

@dataclass(frozen=True)
class MemCtrl(object):
    """Mem control signals bundle."""

    branch : bool
    mem_write : bool
    mem_read : bool

    def Literal(self):
        return {
            'branch': self.branch,
            'mem_write': self.mem_write,
            'mem_read': self.mem_read
        }

    @staticmethod
    def Nop():
        return MemCtrl(False, False, False)

@dataclass(frozen=True)
class WbCtrl(object):
    """Writeback control signals bundle."""

    mem_to_reg : bool
    write_reg : bool

    def Literal(self):
        return {
            'mem_to_reg': self.mem_to_reg,
            'write_reg': self.write_reg
        }

    @staticmethod
    def Reg():
        return WbCtrl(False, True)

    @staticmethod
    def Mem():
        return WbCtrl(True, True)

    @staticmethod
    def Nop():
        return WbCtrl(False, False)

@dataclass
class Inst(object):
    """Instruction specification record.

    This is a dataclass that basically just acts as a record that relates a
    given instruction "pattern" to the control signals that should be produced
    by that pattern.
    """

    itype : int
    pattern : Pattern
    ex_ctrl : ExCtrl
    mem_ctrl : MemCtrl
    wb_ctrl : WbCtrl

    #
    # The following are helper functions for creating an instruction of a
    # particular type. This is mainly used for verbosity of code below.
    #

    @staticmethod
    def R(pattern, ex_ctrl, mem_ctrl, wb_ctrl):
        return Inst(ITypes.R, pattern, ex_ctrl, mem_ctrl, wb_ctrl)

    @staticmethod
    def I(pattern, ex_ctrl, mem_ctrl, wb_ctrl):
        return Inst(ITypes.I, pattern, ex_ctrl, mem_ctrl, wb_ctrl)

    @staticmethod
    def S(pattern, ex_ctrl, mem_ctrl, wb_ctrl):
        return Inst(ITypes.S, pattern, ex_ctrl, mem_ctrl, wb_ctrl)

    @staticmethod
    def B(pattern, ex_ctrl, mem_ctrl, wb_ctrl):
        return Inst(ITypes.B, pattern, ex_ctrl, mem_ctrl, wb_ctrl)

    @staticmethod
    def U(pattern, ex_ctrl, mem_ctrl, wb_ctrl):
        return Inst(ITypes.U, pattern, ex_ctrl, mem_ctrl, wb_ctrl)

    @staticmethod
    def J(pattern, ex_ctrl, mem_ctrl, wb_ctrl):
        return Inst(ITypes.J, pattern, ex_ctrl, mem_ctrl, wb_ctrl)

instructions = {

    #
    # R-Type Instructions
    #

    'add': Inst.R(Pattern(Opcodes.OP, 0b000, 0b0000000), ExCtrl(AluSrc.RS2, 0b10), MemCtrl.Nop(), WbCtrl.Reg()),
    'sub': Inst.R(Pattern(Opcodes.OP, 0b000, 0b0100000), ExCtrl(AluSrc.RS2, 0b10), MemCtrl.Nop(), WbCtrl.Reg()),
    'sll': Inst.R(Pattern(Opcodes.OP, 0b001, 0b0000000), ExCtrl(AluSrc.RS2, 0b10), MemCtrl.Nop(), WbCtrl.Reg()),
    'xor': Inst.R(Pattern(Opcodes.OP, 0b100, 0b0000000), ExCtrl(AluSrc.RS2, 0b10), MemCtrl.Nop(), WbCtrl.Reg()),
    'srl': Inst.R(Pattern(Opcodes.OP, 0b101, 0b0000000), ExCtrl(AluSrc.RS2, 0b10), MemCtrl.Nop(), WbCtrl.Reg()),
    'or': Inst.R(Pattern(Opcodes.OP, 0b110, 0b0000000), ExCtrl(AluSrc.RS2, 0b10), MemCtrl.Nop(), WbCtrl.Reg()),
    'and': Inst.R(Pattern(Opcodes.OP, 0b111, 0b0000000), ExCtrl(AluSrc.RS2, 0b10), MemCtrl.Nop(), WbCtrl.Reg()),

    #
    # I-Type Instructions
    #

    'lb': Inst.I(Pattern(Opcodes.LOAD, 0b000, None), ExCtrl(AluSrc.RS2, 0b00), MemCtrl(False, False, True), WbCtrl.Mem()),
    'lh': Inst.I(Pattern(Opcodes.LOAD, 0b001, None), ExCtrl(AluSrc.RS2, 0b00), MemCtrl(False, False, True), WbCtrl.Mem()),
    'lw': Inst.I(Pattern(Opcodes.LOAD, 0b010, None), ExCtrl(AluSrc.RS2, 0b00), MemCtrl(False, False, True), WbCtrl.Mem()),
    'ld': Inst.I(Pattern(Opcodes.LOAD, 0b011, None), ExCtrl(AluSrc.RS2, 0b00), MemCtrl(False, False, True), WbCtrl.Mem()),
    'lbu': Inst.I(Pattern(Opcodes.LOAD, 0b100, None), ExCtrl(AluSrc.RS2, 0b00), MemCtrl(False, False, True), WbCtrl.Mem()),
    'lhu': Inst.I(Pattern(Opcodes.LOAD, 0b101, None), ExCtrl(AluSrc.RS2, 0b00), MemCtrl(False, False, True), WbCtrl.Mem()),
    'lwu': Inst.I(Pattern(Opcodes.LOAD, 0b110, None), ExCtrl(AluSrc.RS2, 0b00), MemCtrl(False, False, True), WbCtrl.Mem()),
    'addi': Inst.I(Pattern(Opcodes.OPIMM, 0b000, None), ExCtrl(AluSrc.IMM, 0b00), MemCtrl.Nop(), WbCtrl.Reg()),
    'slli': Inst.I(Pattern(Opcodes.OPIMM, 0b001, 0b0000000), ExCtrl(AluSrc.IMM, 0b00), MemCtrl.Nop(), WbCtrl.Reg()),
    'xori': Inst.I(Pattern(Opcodes.OPIMM, 0b100, None), ExCtrl(AluSrc.IMM, 0b00), MemCtrl.Nop(), WbCtrl.Reg()),
    'srli': Inst.I(Pattern(Opcodes.OPIMM, 0b101, 0b0000000), ExCtrl(AluSrc.IMM, 0b00), MemCtrl.Nop(), WbCtrl.Reg()),
    'srai': Inst.I(Pattern(Opcodes.OPIMM, 0b101, 0b0100000), ExCtrl(AluSrc.IMM, 0b00), MemCtrl.Nop(), WbCtrl.Reg()),
    'ori': Inst.I(Pattern(Opcodes.OPIMM, 0b110, None), ExCtrl(AluSrc.IMM, 0b00), MemCtrl.Nop(), WbCtrl.Reg()),
    'andi': Inst.I(Pattern(Opcodes.OPIMM, 0b111, None), ExCtrl(AluSrc.IMM, 0b00), MemCtrl.Nop(), WbCtrl.Reg()),
    'jalr': Inst.I(Pattern(Opcodes.JALR, 0b000, None), ExCtrl(AluSrc.RS2, 0b00), MemCtrl.Nop(), WbCtrl.Reg()),

    #
    # S-Type Instructions
    #

    'sb': Inst.S(Pattern(Opcodes.STORE, 0b000, None), ExCtrl(AluSrc.RS2, 0b00), MemCtrl(False, True, False), WbCtrl.Mem()),
    'sh': Inst.S(Pattern(Opcodes.STORE, 0b001, None), ExCtrl(AluSrc.RS2, 0b00), MemCtrl(False, True, False), WbCtrl.Mem()),
    'sw': Inst.S(Pattern(Opcodes.STORE, 0b010, None), ExCtrl(AluSrc.RS2, 0b00), MemCtrl(False, True, False), WbCtrl.Mem()),
    'sd': Inst.S(Pattern(Opcodes.STORE, 0b111, None), ExCtrl(AluSrc.RS2, 0b00), MemCtrl(False, True, False), WbCtrl.Mem()),

    #
    # B-Type Instructions
    #

    'beq': Inst.B(Pattern(Opcodes.BRANCH, 0b000, None), ExCtrl(AluSrc.RS2, 0b01), MemCtrl(True, False, False), WbCtrl.Nop()),
    'bne': Inst.B(Pattern(Opcodes.BRANCH, 0b001, None), ExCtrl(AluSrc.RS2, 0b01), MemCtrl(True, False, False), WbCtrl.Nop()),
    'blt': Inst.B(Pattern(Opcodes.BRANCH, 0b100, None), ExCtrl(AluSrc.RS2, 0b01), MemCtrl(True, False, False), WbCtrl.Nop()),
    'bge': Inst.B(Pattern(Opcodes.BRANCH, 0b101, None), ExCtrl(AluSrc.RS2, 0b01), MemCtrl(True, False, False), WbCtrl.Nop()),
    'bltu': Inst.B(Pattern(Opcodes.BRANCH, 0b110, None), ExCtrl(AluSrc.RS2, 0b01), MemCtrl(True, False, False), WbCtrl.Nop()),
    'bgeu': Inst.B(Pattern(Opcodes.BRANCH, 0b111, None), ExCtrl(AluSrc.RS2, 0b01), MemCtrl(True, False, False), WbCtrl.Nop()),

    #
    # U-Type Instructions
    #

    'lui': Inst.U(Pattern(Opcodes.LUI, None, None), ExCtrl(AluSrc.RS2, 0b00), MemCtrl(False, False, False), WbCtrl.Reg()),

    #
    # J-Type Instructions
    #

    'jal': Inst.J(Pattern(Opcodes.JAL, None, None), ExCtrl(AluSrc.RS2, 0b00), MemCtrl(True, False, False), WbCtrl.Nop())
}

class AluInsts(object):
    width = 4

    AND = 0b0000
    OR = 0b0001
    ADD = 0b0010
    SUB = 0b0110
    XOR = 0b0101
    SRL = 0b1000
    SLL = 0b1001

@dataclass
class AluInst(object):
    # Inputs to match
    alu_op1 : int
    alu_op0 : int
    funct7 : int
    funct3 : int

    # What to set alu_inst to
    alu_inst : int

alu_instructions = [
    AluInst(0, 0, None, None, AluInsts.ADD),
    AluInst(None, 1, None, None, AluInsts.SUB),
    AluInst(1, None, 0b0000000, 0b000, AluInsts.ADD),
    AluInst(1, None, 0b0000000, 0b001, AluInsts.SLL),
    AluInst(1, None, 0b0000000, 0b100, AluInsts.XOR),
    AluInst(1, None, 0b0000000, 0b101, AluInsts.SRL),
    AluInst(1, None, 0b0100000, 0b000, AluInsts.SUB),
    AluInst(1, None, 0b0000000, 0b111, AluInsts.AND),
    AluInst(1, None, 0b0000000, 0b110, AluInsts.OR)
]