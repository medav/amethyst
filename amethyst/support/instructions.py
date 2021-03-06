from dataclasses import dataclass
from contextlib import contextmanager

from atlas import *
from .interfaces import *
from .config import *

AluSrc = Enum(['RS2', 'IMM'])
ITypes = Enum(['R', 'I', 'S', 'B', 'U', 'J'])

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

class AluOp(object):
    """TODO: document me
    """
    width = 2
    IMM = 0b00
    REG = 0b01
    BRANCH = 0b10

class BranchType(object):
    width = 3
    EQ = 0b000
    NEQ = 0b001
    LT = 0b100
    GEQ = 0b101
    LTU = 0b110
    GEQU = 0b111

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
    lui : bool = False
    auipc : bool = False
    jalr: bool = False

    def Literal(self):
        return {
            'alu_src': self.alu_src,
            'alu_op': self.alu_op,
            'lui': self.lui,
            'auipc': self.auipc,
            'jalr': self.jalr
        }

@dataclass(frozen=True)
class MemCtrl(object):
    """Mem control signals bundle."""

    branch : bool
    branch_type : int
    jal : bool
    mem_write : bool
    mem_read : bool

    def Literal(self):
        return {
            'branch': self.branch,
            'branch_type': self.branch_type,
            'jal': self.jal,
            'mem_write': self.mem_write,
            'mem_read': self.mem_read
        }

    @staticmethod
    def Load():
        return MemCtrl(False, 0, False, False, True)

    @staticmethod
    def Store():
        return MemCtrl(False, 0, False, True, False)

    @staticmethod
    def Jal():
        return MemCtrl(False, 0, True, False, False)

    @staticmethod
    def Branch(ty):
        return MemCtrl(True, ty, False, False, False)

    @staticmethod
    def Nop():
        return MemCtrl(False, 0, False, False, False)

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
    def Load():
        return WbCtrl(True, True)

    @staticmethod
    def Store():
        return WbCtrl(False, False)

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

    'add': Inst.R(Pattern(Opcodes.OP, 0b000, 0b0000000), ExCtrl(AluSrc.RS2, AluOp.REG), MemCtrl.Nop(), WbCtrl.Reg()),
    'sub': Inst.R(Pattern(Opcodes.OP, 0b000, 0b0100000), ExCtrl(AluSrc.RS2, AluOp.REG), MemCtrl.Nop(), WbCtrl.Reg()),
    'sll': Inst.R(Pattern(Opcodes.OP, 0b001, 0b0000000), ExCtrl(AluSrc.RS2, AluOp.REG), MemCtrl.Nop(), WbCtrl.Reg()),
    'xor': Inst.R(Pattern(Opcodes.OP, 0b100, 0b0000000), ExCtrl(AluSrc.RS2, AluOp.REG), MemCtrl.Nop(), WbCtrl.Reg()),
    'srl': Inst.R(Pattern(Opcodes.OP, 0b101, 0b0000000), ExCtrl(AluSrc.RS2, AluOp.REG), MemCtrl.Nop(), WbCtrl.Reg()),
    'or': Inst.R(Pattern(Opcodes.OP, 0b110, 0b0000000),  ExCtrl(AluSrc.RS2, AluOp.REG), MemCtrl.Nop(), WbCtrl.Reg()),
    'and': Inst.R(Pattern(Opcodes.OP, 0b111, 0b0000000), ExCtrl(AluSrc.RS2, AluOp.REG), MemCtrl.Nop(), WbCtrl.Reg()),

    #
    # I-Type Instructions
    #

    'lb': Inst.I(Pattern(Opcodes.LOAD, 0b000, None), ExCtrl(AluSrc.IMM, AluOp.IMM), MemCtrl.Load(), WbCtrl.Load()),
    'lh': Inst.I(Pattern(Opcodes.LOAD, 0b001, None), ExCtrl(AluSrc.IMM, AluOp.IMM), MemCtrl.Load(), WbCtrl.Load()),
    'lw': Inst.I(Pattern(Opcodes.LOAD, 0b010, None), ExCtrl(AluSrc.IMM, AluOp.IMM), MemCtrl.Load(), WbCtrl.Load()),
    'ld': Inst.I(Pattern(Opcodes.LOAD, 0b011, None), ExCtrl(AluSrc.IMM, AluOp.IMM), MemCtrl.Load(), WbCtrl.Load()),

    'lbu': Inst.I(Pattern(Opcodes.LOAD, 0b100, None), ExCtrl(AluSrc.IMM, AluOp.IMM), MemCtrl.Load(), WbCtrl.Load()),
    'lhu': Inst.I(Pattern(Opcodes.LOAD, 0b101, None), ExCtrl(AluSrc.IMM, AluOp.IMM), MemCtrl.Load(), WbCtrl.Load()),
    'lwu': Inst.I(Pattern(Opcodes.LOAD, 0b110, None), ExCtrl(AluSrc.IMM, AluOp.IMM), MemCtrl.Load(), WbCtrl.Load()),

    'addi': Inst.I(Pattern(Opcodes.OPIMM, 0b000, None), ExCtrl(AluSrc.IMM, AluOp.IMM), MemCtrl.Nop(), WbCtrl.Reg()),
    'slli': Inst.I(Pattern(Opcodes.OPIMM, 0b001, 0b0000000), ExCtrl(AluSrc.IMM, AluOp.IMM), MemCtrl.Nop(), WbCtrl.Reg()),
    'xori': Inst.I(Pattern(Opcodes.OPIMM, 0b100, None), ExCtrl(AluSrc.IMM, AluOp.IMM), MemCtrl.Nop(), WbCtrl.Reg()),
    'srli': Inst.I(Pattern(Opcodes.OPIMM, 0b101, 0b0000000), ExCtrl(AluSrc.IMM, AluOp.IMM), MemCtrl.Nop(), WbCtrl.Reg()),
    'srai': Inst.I(Pattern(Opcodes.OPIMM, 0b101, 0b0100000), ExCtrl(AluSrc.IMM, AluOp.IMM), MemCtrl.Nop(), WbCtrl.Reg()),
    'ori': Inst.I(Pattern(Opcodes.OPIMM, 0b110, None), ExCtrl(AluSrc.IMM, AluOp.IMM), MemCtrl.Nop(), WbCtrl.Reg()),
    'andi': Inst.I(Pattern(Opcodes.OPIMM, 0b111, None), ExCtrl(AluSrc.IMM, AluOp.IMM), MemCtrl.Nop(), WbCtrl.Reg()),

    'jalr': Inst.I(Pattern(Opcodes.JALR, 0b000, None), ExCtrl(AluSrc.IMM, AluOp.IMM, jalr=True), MemCtrl.Jal(), WbCtrl.Reg()),

    #
    # S-Type Instructions
    #

    'sb': Inst.S(Pattern(Opcodes.STORE, 0b000, None), ExCtrl(AluSrc.IMM, AluOp.IMM), MemCtrl.Store(), WbCtrl.Store()),
    'sh': Inst.S(Pattern(Opcodes.STORE, 0b001, None), ExCtrl(AluSrc.IMM, AluOp.IMM), MemCtrl.Store(), WbCtrl.Store()),
    'sw': Inst.S(Pattern(Opcodes.STORE, 0b010, None), ExCtrl(AluSrc.IMM, AluOp.IMM), MemCtrl.Store(), WbCtrl.Store()),
    'sd': Inst.S(Pattern(Opcodes.STORE, 0b011, None), ExCtrl(AluSrc.IMM, AluOp.IMM), MemCtrl.Store(), WbCtrl.Store()),

    #
    # B-Type Instructions
    #

    'beq':  Inst.B(Pattern(Opcodes.BRANCH, 0b000, None), ExCtrl(AluSrc.RS2, AluOp.BRANCH), MemCtrl.Branch(BranchType.EQ), WbCtrl.Nop()),
    'bne':  Inst.B(Pattern(Opcodes.BRANCH, 0b001, None), ExCtrl(AluSrc.RS2, AluOp.BRANCH), MemCtrl.Branch(BranchType.NEQ), WbCtrl.Nop()),
    'blt':  Inst.B(Pattern(Opcodes.BRANCH, 0b100, None), ExCtrl(AluSrc.RS2, AluOp.BRANCH), MemCtrl.Branch(BranchType.LT), WbCtrl.Nop()),
    'bge':  Inst.B(Pattern(Opcodes.BRANCH, 0b101, None), ExCtrl(AluSrc.RS2, AluOp.BRANCH), MemCtrl.Branch(BranchType.GEQ), WbCtrl.Nop()),
    'bltu': Inst.B(Pattern(Opcodes.BRANCH, 0b110, None), ExCtrl(AluSrc.RS2, AluOp.BRANCH), MemCtrl.Branch(BranchType.LTU), WbCtrl.Nop()),
    'bgeu': Inst.B(Pattern(Opcodes.BRANCH, 0b111, None), ExCtrl(AluSrc.RS2, AluOp.BRANCH), MemCtrl.Branch(BranchType.GEQU), WbCtrl.Nop()),

    #
    # U-Type Instructions
    #

    'lui': Inst.U(Pattern(Opcodes.LUI, None, None), ExCtrl(AluSrc.RS2, 0b00, True), MemCtrl.Nop(), WbCtrl.Reg()),

    #
    # J-Type Instructions
    #

    'jal': Inst.J(Pattern(Opcodes.JAL, None, None), ExCtrl(AluSrc.RS2, 0b00), MemCtrl.Jal(), WbCtrl.Nop())
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
    alu_op : int
    alu_op1 : int
    alu_op0 : int
    funct7 : int
    funct3 : int

    # What to set alu_inst to
    alu_inst : int

alu_instructions = [
    # Branch operation
    AluInst(AluOp.BRANCH, None, None, None, None, AluInsts.SUB),

    # All the regular operations
    AluInst(AluOp.REG, 0, 0, None, None, AluInsts.ADD),
    AluInst(AluOp.REG, None, 1, None, None, AluInsts.SUB),
    AluInst(AluOp.REG, 1, None, 0b0000000, 0b000, AluInsts.ADD),
    AluInst(AluOp.REG, 1, None, 0b0000000, 0b001, AluInsts.SLL),
    AluInst(AluOp.REG, 1, None, 0b0000000, 0b100, AluInsts.XOR),
    AluInst(AluOp.REG, 1, None, 0b0000000, 0b101, AluInsts.SRL),
    AluInst(AluOp.REG, 1, None, 0b0100000, 0b000, AluInsts.SUB),
    AluInst(AluOp.REG, 1, None, 0b0000000, 0b111, AluInsts.AND),
    AluInst(AluOp.REG, 1, None, 0b0000000, 0b110, AluInsts.OR),

    AluInst(AluOp.IMM, 0, 0, None, None, AluInsts.ADD),
    AluInst(AluOp.IMM, None, 1, None, None, AluInsts.SUB),
    AluInst(AluOp.IMM, 1, None, 0b0000000, 0b000, AluInsts.ADD),
    AluInst(AluOp.IMM, 1, None, 0b0000000, 0b001, AluInsts.SLL),
    AluInst(AluOp.IMM, 1, None, 0b0000000, 0b100, AluInsts.XOR),
    AluInst(AluOp.IMM, 1, None, 0b0000000, 0b101, AluInsts.SRL),
    AluInst(AluOp.IMM, 1, None, 0b0100000, 0b000, AluInsts.SUB),
    AluInst(AluOp.IMM, 1, None, 0b0000000, 0b111, AluInsts.AND),
    AluInst(AluOp.IMM, 1, None, 0b0000000, 0b110, AluInsts.OR)
]
