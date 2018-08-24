from atlas import *

from config import config as C

#
# Memory signals
#

imem_bundle = {
    'r_addr': Bits(C['paddr-width']),
    'r_data': Flip(Bits(32)),
    'r_en': Bits(1)
}

dmem_bundle = {
    'r_addr': Bits(C['paddr-width']),
    'r_data': Flip(Bits(C['core-width'])),
    'r_en': Bits(1),
    'w_addr': Bits(C['paddr-width']),
    'w_data': Bits(C['core-width']),
    'w_en': Bits(1)
}

#
# Control signal bundles
#

inst_data_bundle = {
    'inst': Bits(32),
    'pc': Bits(C['paddr-width']),
    'rs1': Bits(Log2Ceil(C['reg-count'])),
    'rs2': Bits(Log2Ceil(C['reg-count'])),
    'rd': Bits(Log2Ceil(C['reg-count']))
}

inst_data_bundle_reset = {
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
    'zero': 0,
    'sign': 0,
    'overflow': 0
}

mem_ctrl_bundle = {
    'branch': Bits(1),
    'mem_write': Bits(1),
    'mem_read': Bits(1)
}

mem_ctrl_bundle_reset = {
    'branch': 0,
    'mem_write': 0,
    'mem_read': 0
}

writeback_ctrl_bundle = {
    'mem_to_reg': Bits(1)
}

writeback_ctrl_bundle_reset = {
    'mem_to_reg': 0
}

reg_write_bundle = {
    'w_addr': Bits(Log2Ceil(C['reg-count'])),
    'w_en': Bits(1),
    'w_data': Bits(C['core-width'])
}

#
# Pipeline stage bundles
#

if_id_bundle = {
    'pc': Bits(C['paddr-width']),
    'valid': Bits(1),
}

if_id_bundle_reset = {
    'pc': 0,
    'valid': 0
}

id_ex_bundle = {
    'ex_ctrl': execute_ctrl_bundle,
    'mem_ctrl': mem_ctrl_bundle,
    'wb_ctrl': writeback_ctrl_bundle,
    'inst_data': inst_data_bundle,
    'rs1_data': Bits(C['core-width']),
    'rs2_data': Bits(C['core-width']),
    'imm': Bits(C['core-width'])
}

id_ex_bundle_reset = {
    'ex_ctrl': execute_ctrl_bundle_reset,
    'mem_ctrl': mem_ctrl_bundle_reset,
    'wb_ctrl': writeback_ctrl_bundle_reset,
    'inst_data': inst_data_bundle_reset,
    'rs1_data': 0,
    'rs2_data': 0,
    'imm': 0
}

ex_mem_bundle = {
    'mem_ctrl': mem_ctrl_bundle,
    'wb_ctrl': writeback_ctrl_bundle,
    'inst_data': inst_data_bundle,
    'branch_target': Bits(C['paddr-width']),
    'rs2_data': Bits(C['core-width']),
    'alu_result': Bits(C['core-width']),
    'alu_flags': alu_flags
}

ex_mem_bundle_reset = {
    'mem_ctrl': mem_ctrl_bundle_reset,
    'wb_ctrl': writeback_ctrl_bundle_reset,
    'inst_data': inst_data_bundle_reset,
    'branch_target': 0,
    'rs2_data': 0,
    'alu_result': 0,
    'alu_flags': alu_flags_reset
}

mem_wb_bundle = {
    'wb_ctrl': writeback_ctrl_bundle,
    'inst_data': inst_data_bundle,
    'alu_result': Bits(C['core-width']),
}

mem_wb_bundle_reset = {
    'wb_ctrl': writeback_ctrl_bundle_reset,
    'inst_data': inst_data_bundle_reset,
    'alu_result': 0
}
