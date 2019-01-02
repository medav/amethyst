from dataclasses import dataclass
from contextlib import contextmanager

from atlas import *
from ..support import *


def SetControlSignals(inst_spec, itype, ctrl):
    """Update given control signals based on inst_spec."""

    itype <<= inst_spec.itype

    #
    # The Literal() function (see instructions.py) generates an Atlas 'literal'
    # value that can be used on the right-hand side of an assignment (as is done
    # below).
    #

    ctrl.ex <<= inst_spec.ex_ctrl.Literal()
    ctrl.mem <<= inst_spec.mem_ctrl.Literal()
    ctrl.wb <<= inst_spec.wb_ctrl.Literal()

def Control(inst, itype, ctrl):
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

    ctrl.ex.alu_src <<= 0
    ctrl.ex.alu_op <<= 0
    ctrl.ex.lui <<= False
    ctrl.ex.auipc <<= False
    ctrl.ex.funct3 <<= funct3
    ctrl.ex.funct7 <<= funct7

    ctrl.mem.branch <<= False
    ctrl.mem.mem_write <<= False
    ctrl.mem.mem_read <<= False

    ctrl.wb.mem_to_reg <<= False
    ctrl.wb.write_reg <<= False

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
            SetControlSignals(inst_spec, itype, ctrl)

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
        'r0_en' : Input(Bits(1)),
        'r1_addr': Input(Bits(Log2Ceil(C['reg-count']))),
        'r1_en' : Input(Bits(1)),
        'w0_addr': Input(Bits(Log2Ceil(C['reg-count']))),
        'w0_data': Input(Bits(C['core-width'])),
        'w0_en' : Input(Bits(1)),
        'r0_data': Output(Bits(C['core-width'])),
        'r1_data': Output(Bits(C['core-width']))
    })

    r0_data = Wire(Bits(C['core-width']))
    r1_data = Wire(Bits(C['core-width']))

    reg_mem = Mem(C['core-width'], C['reg-count'])

    #
    # Handle the two read ports. If the read address is 0, always read 0.
    #

    with io.r0_addr == 0:
        io.r0_data <<= 0
    with otherwise:
        with io.r0_addr == io.w0_addr:
            io.r0_data <<= io.w0_data
        with otherwise:
            io.r0_data <<= reg_mem.Read(io.r0_addr, io.r0_en)

    with io.r1_addr == 0:
        io.r1_data <<= 0
    with otherwise:
        with io.r1_addr == io.w0_addr:
            io.r1_data <<= io.w0_data
        with otherwise:
            io.r1_data <<= reg_mem.Read(io.r1_addr, io.r1_en)

    #
    # Register writes to x0 are ignored since that register must always read as
    # zero.
    #

    reg_mem.Write(io.w0_addr, io.w0_data, (io.w0_addr != 0) & io.w0_en)

    NameSignals(locals())

def HandleRasCtrl(ras_ctrl, inst, pc):
    link_rs1 = (Rs1(inst) == 1) | (Rs1(inst) == 5)
    link_rd = (Rd(inst) == 1) | (Rd(inst) == 5)

    ras_ctrl.pc <<= pc
    ras_ctrl.push <<= False
    ras_ctrl.pop <<= False

    with Opcode(inst) == Opcodes.JALR:
        ras_ctrl.push <<= link_rd

        with ~link_rd & link_rs1:
            ras_ctrl.pop <<= True

        with link_rd & link_rs1 & (Rs1(inst) != Rd(inst)):
            ras_ctrl.pop <<= True

@Module
def DecodeStage():
    """The instruction decode stage for Geode.

    This stage consumes the instruction produced by the most recent imem access
    and produces control signals and a sign-extended immediate value. In
    addition, this module contains the register file and produces read values
    for register source data.
    """

    io = Io({
        'if_id': Input(if_bundle),
        'inst': Input(Bits(32)),
        'stall': Input(Bits(1)),
        'reg_write': Input(reg_write_bundle),
        'ras_ctrl': Output(ras_ctrl_bundle),
        'id_ex': Output(id_ex_bundle),
        'rs1_data': Output(Bits(C['core-width'])),
        'rs2_data': Output(Bits(C['core-width'])),
    })

    inst = Wire(Bits(32))

    with io.if_id.valid:
        inst <<= io.inst
    with otherwise:
        inst <<= 0

    regfile = Instance(RegisterFile())

    itype = Wire(Bits(ITypes.bitwidth))

    regfile.r0_addr <<= Rs1(inst)
    regfile.r0_en <<= ~io.stall
    regfile.r1_addr <<= Rs2(inst)
    regfile.r1_en <<= ~io.stall

    regfile.w0_addr <<= io.reg_write.w_addr
    regfile.w0_en <<= io.reg_write.w_en & ~io.stall
    regfile.w0_data <<= io.reg_write.w_data

    #
    # inst_data is metadata about the current instruction that is passed through
    # the pipeline unrelated to control signals. It's primary use is for hazard
    # detection and data forwarding.
    #

    io.id_ex.ctrl.valid <<= io.if_id.valid
    io.id_ex.ctrl.inst <<= inst
    io.id_ex.ctrl.pc <<= io.if_id.pc

    #
    # Hook up the register read outputs.
    #

    io.rs1_data <<= regfile.r0_data
    io.rs2_data <<= regfile.r1_data

    #
    # Control is a Python function that produces the primary decode logic. It
    # matches against a set of known instructions to produce control signals for
    # later stages in the pipeline. The known instructions are encoded in the
    # 'instructions' variable above.
    #

    Control(inst, itype, io.id_ex.ctrl)

    #
    # TODO: Documentation
    #

    HandleRasCtrl(io.ras_ctrl, inst, io.if_id.pc)

    #
    # GenerateImmediate produces logic that consume the itype (instruction
    # type, which is R, I, S, B, U, or J) and produces the immediate value for
    # this instruction.
    #

    io.id_ex.imm <<= GenerateImmediate(inst, itype)

    NameSignals(locals())