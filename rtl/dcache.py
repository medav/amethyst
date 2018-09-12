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

num_sets = C['dcache']['num-sets']
num_ways = C['dcache']['num-ways']
line_width = C['dcache']['line-width']
line_width_bytes = line_width // 8

set_addr_width = Log2Ceil(num_sets)
line_index_width = Log2Ceil(line_width_bytes)
way_addr_width = Log2Ceil(num_ways)

untag_width = set_addr_width + line_index_width
tag_width = paddr_width - untag_width

#
# Addresses in this cache are broken up as follows:
#
# | -------- tag -------- | - set - | - index - |
# | -------- tag -------- | ------ untag ------ |
#
# The "untag" is the set + index
#

access_size = Enum(['byte', 'half', 'word', 'dword'])
access_rtype = Enum(['read', 'write'])

Tag = lambda addr: addr(paddr_width - 1, untag_width)
Set = lambda addr: addr(untag_width - 1, line_index_width)
Index = lambda addr: addr(line_index_width - 1, 0)

cpu_dcache_req = {
    'valid': Bits(1),
    'size': Bits(access_size.bitwidth),
    'addr': Bits(paddr_width),
    'rtype': Bits(access_rtype.bitwidth)
}

cpu_dcache_req_reset = {
    'valid': False,
    'size': 0,
    'addr': 0,
    'rtype': 0
}

cpu_dcache_resp = {
    'valid': Bits(1),
    'data': Bits(core_width)
}

meta_query_req = Bits(paddr_width)

meta_query_resp = {
    'hit': Bits(1),
    'way': Bits(way_addr_width)
}

meta_write = {
    'write': Bits(1),
    'set': Bits(set_addr_width),
    'tag': Bits(tag_width)
}

data_read_req = {
    'set': Bits(set_addr_width),
    'way': Bits(way_addr_width)
}

data_read_resp = Bits(line_width)

# @Module
# def Mshr():
#     io = Io({

#     })

@Module
def DCacheMetaArray():
    io = Io({
        'query_req': Input(meta_query_req),
        'query_resp': Output(meta_query_resp),
        'write': Input(meta_write)
    })

    meta_read_data = Wire(Bits(num_ways * tag_width))

    valid_bits = Reg([
        [Bits(1) for _ in range(num_sets)]
        for _ in range(num_ways)],
        reset_value=[
        [0 for _ in range(num_sets)]
        for _ in range(num_ways)])

    meta_array = Mem(
        tag_width * num_ways,
        num_sets)

    meta_read_data <<= meta_array.Read(Set(io.query_req))

    read_tags = [
        (i, meta_read_data((i + 1) * tag_width - 1, i * tag_width))
        for i in range(num_ways)
    ]

    io.query_resp.hit <<= False
    io.query_resp.way <<= 0

    for (way, read_tag) in read_tags:
        valid = valid_bits[way][Set(io.query_req)]
        with (read_tag == Tag(io.query_req)) & valid:
            io.query_resp.hit <<= True
            io.query_resp.way <<= way

    NameSignals(locals())

@Module
def DCacheDataArray():
    io = Io({
        'read_req': Input(data_read_req),
        'read_resp': Output(data_read_resp)
    })

    read_result = Wire(Bits(num_ways * line_width))
    read_lines = Wire([Bits(line_width) for _ in range(num_ways)])
    data_array = Mem(num_ways * line_width, num_sets)
    read_result <<= data_array.Read(io.read_req.set)

    for i in range(num_ways):
        read_lines[i] <<= read_result(line_width * (i + 1) - 1, line_width * i)

    io.read_resp <<= Mux(read_lines, io.read_req.way)
    NameSignals(locals())


@Module
def Aligner():
    io = Io({
        'cpu_req': Input(cpu_dcache_req),
        'line': Input(Bits(line_width)),
        'result': Output(Bits(core_width))
    })

    io.result <<= 0

    NameSignals(locals())

@Module
def DCache():
    io = Io({
        'ready': Output(Bits(1)),
        'cpu_req': Input(cpu_dcache_req),
        'stall': Output(Bits(1)),
        'cpu_resp': Output(cpu_dcache_resp)
    })

    meta_array = Instance(DCacheMetaArray())
    data_array = Instance(DCacheDataArray())
    aligner = Instance(Aligner())

    s1_req = Wire(cpu_dcache_req)
    s2_req = Reg(cpu_dcache_req, reset_value=cpu_dcache_req_reset)
    miss_active = Reg(Bits(1), reset_value=False)

    #
    # Stage 1: Metadata read
    #

    s1_req <<= io.cpu_req
    io.ready <<= True

    meta_array.query_req <<= s1_req.addr

    #
    # Stage 2: Data read
    #

    with s1_req.valid:
        s2_req <<= s1_req

    data_array.read_req.set <<= Set(s2_req.addr)
    data_array.read_req.way <<= meta_array.query_resp.way

    #
    # Miss handling
    #

    miss_active <<= ~meta_array.query_resp.hit
    io.stall <<= ~meta_array.query_resp.hit | miss_active

    NameSignals(locals())



