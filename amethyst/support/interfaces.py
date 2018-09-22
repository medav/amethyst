from atlas import *
from .config import *

#
# Memory signals
#

access_rtype = Enum(['b', 'h', 'w', 'd', 'bu', 'hu', 'wu'])

mem_read_request = {
    'valid': Bits(1),
    'ready': Flip(Bits(1)),
    'addr': Bits(C['paddr-width']),
}

mem_read_response = {
    'valid': Bits(1),
    'ready': Flip(Bits(1)),
    'addr': Bits(C['paddr-width']),
    'data': Bits(C['mem-width'])
}

mem_write_request = {
    'valid': Bits(1),
    'ready': Flip(Bits(1)),
    'addr': Bits(C['paddr-width']),
    'data': Bits(C['mem-width'])
}

mem_bundle = {
    'read': mem_read_request,
    'resp': Flip(mem_read_response),
    'write': mem_write_request
}

cpu_cache_req = {
    'valid': Bits(1),
    'addr': Bits(C['paddr-width']),
    'rtype': Bits(access_rtype.bitwidth),
    'read': Bits(1),
}

cpu_cache_req_reset = {
    'valid': False,
    'addr': 0,
    'rtype': 0,
    'read': False
}

cpu_cache_resp = {
    'data': Bits(C['core-width'])
}

#
# Control signal bundles
#

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
    'mem_to_reg': Bits(1),
    'write_reg': Bits(1)
}

writeback_ctrl_bundle_reset = {
    'mem_to_reg': False,
    'write_reg': False
}

ctrl_bundle = {
    'valid': Bits(1),
    'inst': Bits(32),
    'pc': Bits(C['paddr-width']),
    'ex': execute_ctrl_bundle,
    'mem': mem_ctrl_bundle,
    'wb': writeback_ctrl_bundle
}

ctrl_bundle_reset = {
    'valid': False,
    'inst': 0,
    'pc': 0,
    'ex': execute_ctrl_bundle_reset,
    'mem': mem_ctrl_bundle_reset,
    'wb': writeback_ctrl_bundle_reset
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
    'valid': Bits(1),
    'pc': Bits(C['paddr-width'])
}

if_id_bundle_reset = {
    'valid': False,
    'pc': 0
}

id_ex_bundle = {
    'ctrl': ctrl_bundle,
    'rs1_data': Bits(C['core-width']),
    'rs2_data': Bits(C['core-width']),
    'imm': Bits(C['core-width'])
}

id_ex_bundle_reset = {
    'ctrl': ctrl_bundle_reset,
    'rs1_data': 0,
    'rs2_data': 0,
    'imm': 0
}

ex_mem_bundle = {
    'ctrl': ctrl_bundle,
    'branch_target': Bits(C['paddr-width']),
    'rs2_data': Bits(C['core-width']),
    'alu_result': Bits(C['core-width']),
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
    'alu_result': Bits(C['core-width']),
}

mem_wb_bundle_reset = {
    'ctrl': ctrl_bundle_reset,
    'alu_result': 0
}

#
# Other
#

mispred_bundle = {
    'valid': Bits(1),
    'pc': Bits(C['paddr-width']),
    'target': Bits(C['paddr-width']),
    'taken': Bits(1),
    'is_return': Bits(1)
}

mispred_bundle_reset = {
    'valid': False,
    'pc': 0,
    'target': 0,
    'taken': False,
    'is_return': False
}

ras_ctrl_bundle = {
    'push': Bits(1),
    'pop': Bits(1),
    'pc': Bits(C['paddr-width'])
}