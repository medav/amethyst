from dataclasses import dataclass
from functools import reduce

from atlas import *
from interfaces import *
from instructions import *

import forward

from config import *

#
# Configuration variables (Either pulled from config, or computed based off
# values from config).
#

num_sets = C['icache']['num-sets']
line_width = C['icache']['line-width']
line_bytes = line_width // 8

set_addr_width = Log2Ceil(num_sets)
line_index_width = Log2Ceil(line_bytes)

untag_width = set_addr_width + line_index_width
tag_width = paddr_width - untag_width

#
# Constraints
#

assert line_width % 8 == 0
assert line_bytes % 4 == 0

#
# Addresses in this cache are broken up as follows:
#
# | -------- tag -------- | - set - | - index - |
# | -------- tag -------- | ------ untag ------ |
#
# The "untag" is the set + index
#

access_rtype = Enum(['read', 'write'])

Tag = lambda addr: addr(paddr_width - 1, untag_width)
Set = lambda addr: addr(untag_width - 1, line_index_width)
Index = lambda addr: addr(line_index_width - 1, 0)

@Module
def Aligner():
    io = Io({
        'cpu_req': Input(Bits(paddr_width)),
        'line': Input(Bits(line_width)),
        'result': Output(Bits(core_width))
    })

    index = Index(io.cpu_req)
    word_index = index(index.width, 2)

    words = Wire([Bits(32) for _ in range(line_bytes // 4)])

    for i in range(line_bytes // 4):
        words[i] <<= io.line(32 * (i + 1) - 1, i)

    io.result <<= Mux(words, word_index)

    NameSignals(locals())

@Module
def ICache():
    io = Io({
        'cpu_req': Input(Bits(paddr_width)),
        'cpu_resp': Output({
            'miss': Bits(1),
            'data': Bits(32)
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



