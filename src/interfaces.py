from atlas import *
from config import config as C

#
# Memory signals
#

imem_bundle = {
    'r_addr': Bits(C['paddr-width']),
    'r_data': Bits(C['paddr-width'])
}

#
# Control signal bundles
#

execute_ctrl_bundle = {
    'alu_src': Bits(Log2Ceil(C['reg-count'])),
    'alu_op': Bits(2),
    'funct3': Bits(3),
    'funct7': Bits(7),
    'rs0': Bits(Log2Ceil(C['reg-count'])),
    'rs1': Bits(Log2Ceil(C['reg-count']))
}

execute_ctrl_bundle_reset = {
    'alu_src': 0,
    'alu_op': 0,
    'funct3': 0,
    'funct7': 0,
    'rs0': 0,
    'rs1': 0
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
    'mem_to_reg': Bits(1),
    'rd': Bits(Log2Ceil(C['reg-count']))
}

writeback_ctrl_bundle_reset = {
    'mem_to_reg': 0,
    'rd': 0
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
    'inst': Bits(32)
}

if_id_bundle_reset = {
    'inst': 0
}

id_ex_bundle = {
    'ex_ctrl': execute_ctrl_bundle,
    'mem_ctrl': mem_ctrl_bundle,
    'wb_ctrl': writeback_ctrl_bundle,
    'rs1_data': Bits(C['core-width']),
    'rs2_data': Bits(C['core-width']),
    'imm': Bits(C['core-width'])
}

id_ex_bundle_reset = {
    'ex_ctrl': execute_ctrl_bundle_reset,
    'mem_ctrl': mem_ctrl_bundle_reset,
    'wb_ctrl': writeback_ctrl_bundle_reset,
    'rs1_data': 0,
    'rs2_data': 0,
    'imm': 0
}

ex_mem_bundle = {
    'mem_ctrl': mem_ctrl_bundle,
    'wb_ctrl': writeback_ctrl_bundle
}

mem_wb_bundle = {
    'wb_ctrl': writeback_ctrl_bundle

}