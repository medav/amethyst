from atlas import *

from config import *

#
# Memory signals
#

mem_read_request = {
    'valid': Bits(1),
    'ready': Flip(Bits(1)),
    'addr': Bits(paddr_width),
}

mem_read_response = {
    'valid': Flip(Bits(1)),
    'ready': Bits(1),
    'addr': Bits(paddr_width),
    'data': Bits(C['mem-width'])
}

mem_write_request = {
    'valid': Bits(1),
    'ready': Flip(Bits(1)),
    'addr': Bits(paddr_width),
    'data': Bits(C['mem-width'])
}

#
# Control signal bundles
#

inst_bundle = {
    'inst': Bits(32),
    'pc': Bits(paddr_width),
    'rs1': Bits(Log2Ceil(C['reg-count'])),
    'rs2': Bits(Log2Ceil(C['reg-count'])),
    'rd': Bits(Log2Ceil(C['reg-count']))
}

inst_bundle_reset = {
    'inst': 0,
    'pc': 0,
    'rs1': 0,
    'rs2': 0,
    'rd': 0
}

execute_ctrl_bundle = {
    'alu_src': Bits(Log2Ceil(C['reg-count'])),
    'alu_op': Bits(2),
    'funct3': Bits(3),
    'funct7': Bits(7)
}

execute_ctrl_bundle_reset = {
    'alu_src': 0,
    'alu_op': 0,
    'funct3': 0,
    'funct7': 0
}

alu_flags = {
    'zero': Bits(1),
    'sign': Bits(1),
    'overflow': Bits(1)
}

alu_flags_reset = {
    'zero': False,
    'sign': 0,
    'overflow': False
}

mem_ctrl_bundle = {
    'branch': Bits(1),
    'mem_write': Bits(1),
    'mem_read': Bits(1)
}

mem_ctrl_bundle_reset = {
    'branch': False,
    'mem_write': False,
    'mem_read': False
}

writeback_ctrl_bundle = {
    'mem_to_reg': Bits(1)
}

writeback_ctrl_bundle_reset = {
    'mem_to_reg': False
}

ctrl_bundle = {
    'valid': Bits(1),
    'inst': inst_bundle,
    'ex': execute_ctrl_bundle,
    'mem': mem_ctrl_bundle,
    'wb': writeback_ctrl_bundle
}

ctrl_bundle_reset = {
    'valid': False,
    'inst': inst_bundle_reset,
    'ex': execute_ctrl_bundle_reset,
    'mem': mem_ctrl_bundle_reset,
    'wb': writeback_ctrl_bundle_reset
}

reg_write_bundle = {
    'w_addr': Bits(Log2Ceil(C['reg-count'])),
    'w_en': Bits(1),
    'w_data': Bits(core_width)
}

#
# Pipeline stage bundles
#

if_id_bundle = {
    'valid': Bits(1),
    'pc': Bits(paddr_width),
    'inst': Bits(32)
}

if_id_bundle_reset = {
    'valid': False,
    'pc': 0,
    'inst': 0
}

id_ex_bundle = {
    'ctrl': ctrl_bundle,
    'rs1_data': Bits(core_width),
    'rs2_data': Bits(core_width),
    'imm': Bits(core_width)
}

id_ex_bundle_reset = {
    'ctrl': ctrl_bundle_reset,
    'rs1_data': 0,
    'rs2_data': 0,
    'imm': 0
}

ex_mem_bundle = {
    'ctrl': ctrl_bundle,
    'branch_target': Bits(paddr_width),
    'rs2_data': Bits(core_width),
    'alu_result': Bits(core_width),
    'alu_flags': alu_flags
}

ex_mem_bundle_reset = {
    'ctrl': ctrl_bundle_reset,
    'branch_target': 0,
    'rs2_data': 0,
    'alu_result': 0,
    'alu_flags': alu_flags_reset
}

mem_wb_bundle = {
    'ctrl': ctrl_bundle,
    'alu_result': Bits(core_width),
}

mem_wb_bundle_reset = {
    'ctrl': ctrl_bundle_reset,
    'alu_result': 0
}
