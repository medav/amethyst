from dataclasses import dataclass
from contextlib import contextmanager

from atlas import *
from interfaces import *
from instructions import *

from config import config as C

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

    #
    # The Literal() function (see instructions.py) generates an Atlas 'literal'
    # value that can be used on the right-hand side of an assignment (as is done
    # below).
    #

    ex_ctrl <<= inst_spec.ex_ctrl.Literal()
    mem_ctrl <<= inst_spec.mem_ctrl.Literal()
    wb_ctrl <<= inst_spec.wb_ctrl.Literal()

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

        #
        # For some instructions, funct3 and funct7 don't need to be matched
        # (and so are marked as Python "None"). For these cases, funct3_match
        # and/or funct7_match are just set to 1 (always true).
        #

        opcode_match = opcode == inst_spec.pattern.opcode

        if inst_spec.pattern.funct3 is None:
            funct3_match = 1
        else:
            funct3_match = funct3 == inst_spec.pattern.funct3

        if inst_spec.pattern.funct7 is None:
            funct7_match = 1
        else:
            funct7_match = funct7 == inst_spec.pattern.funct7

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

    #
    # For now the register file is an array of registers. This is implemented
    # as a "list" signal in Atlas. When compiled to Verilog, the registers
    # become separate signals and likely if ever synthesized will become
    # regular HW registers.
    #
    # In the future, this register file should be revised to be implemented by
    # an SRAM structure instead of an array of registers so it takes up less
    # area / transistors / etc...
    #
    # N.B. Technically, x0 doesn't need a register since it should just be read
    # as zero. It's still instantiated here to make it easy to just index into
    # a list signal for reads. Most synthesis tools are smart enough to remove
    # signals that are unused like this.
    #

    reg_array = Reg(
        [Bits(C['core-width']) for _ in range(C['reg-count'])],
        reset_value=[0 for _ in range(C['reg-count'])])

    #
    # Handle the two read ports. If the read address is 0, always read 0.
    #

    with io.r0_addr == 0:
        io.r0_data <<= 0
    with otherwise:
        io.r0_data <<= reg_array[io.r0_addr]

    with io.r1_addr == 0:
        io.r1_data <<= 0
    with otherwise:
        io.r1_data <<= reg_array[io.r1_addr]

    #
    # Register writes to x0 are ignored since that register must always read as
    # zero.
    #

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