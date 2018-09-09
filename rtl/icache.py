from dataclasses import dataclass
from functools import reduce

from atlas import *
from interfaces import *
from instructions import *

import forward

from config import config as C

#
# Configuration variables (Either pulled from config, or computed based off
# values from config).
#

num_sets = C['icache']['num-sets']
line_width = C['icache']['line-width']
line_width_bytes = line_width // 8

set_addr_width = Log2Ceil(num_sets)
line_index_width = Log2Ceil(line_width_bytes)
way_addr_width = Log2Ceil(num_ways)

untag_width = set_addr_width + line_index_width
tag_width = C['paddr-width'] - untag_width

#
# Addresses in this cache are broken up as follows:
#
# | -------- tag -------- | - set - | - index - |
# | -------- tag -------- | ------ untag ------ |
#
# The "untag" is the set + index
#

access_rtype = Enum(['read', 'write'])

Tag = lambda addr: addr(C['paddr-width'] - 1, untag_width)
Set = lambda addr: addr(untag_width - 1, line_index_width)
Index = lambda addr: addr(line_index_width - 1, 0)

@Module
def Aligner():
    io = Io({
        'cpu_req': Input(Bits(C['paddr-width'])),
        'line': Input(Bits(line_width)),
        'result': Output(Bits(C['core-width']))
    })

    io.result <<= 0

    NameSignals(locals())

@Module
def ICache():
    io = Io({
        'cpu_req': Input(Bits(C['paddr-width'])),
        'cpu_resp': Output({
            'miss': Bits(1),
            'data': Bits(C['core-width'])
        })
    })

    aligner = Instance(Aligner())

    valid_bits = Reg(
        [Bits(1) for _ in range(num_sets)],
        reset_value=[0 for _ in range(num_sets)])

    miss_active = Reg(Bits(1), reset_value=False)

    hit = Wire(Bits(1))

    tag_array = Mem(tag_width, num_sets)
    data_array = Mem(line_width, num_sets)

    tag_read = tag_array.Read(Set(io.cpu_req))
    data_read = data_array.Read(Set(io.cpu_req))

    aligner.cpu_req <<= io.cpu_req
    aligner.line <<= data_read

    io.cpu_resp.data <<= aligner.result

    #
    # Miss Handling
    #

    miss_active <<= ~hit
    io.cpu_resp.miss <<= miss_active | ~hit

    NameSignals(locals())



