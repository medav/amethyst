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
GetTag = lambda meta, way: meta(tag_width * (way + 1) - 1, tag_width * way)
GetData = lambda data, way: data(line_width * (way + 1) - 1, line_width * way)

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

@Module
def CacheMetaArray():
    io = Io({
        'read': Input({
            'set': Bits(set_addr_Width)
        }),
        'resp': Output({
            'hit': Bits(1),
            'way': Bits(way_addr_width)
        }),
        'write': Input({
            'valid': Bits(1),
            'set': Bits(set_addr_width),
            'way': Bits(way_addr_width),
            'meta': Bits(num_ways * tag_width)
        })
    })

    meta_array = Mem(tag_width * num_ways, num_sets)

    read_data = Wire(Bits(num_ways * tag_width))
    evict_way = Wire(Bits(way_addr_width))

    valid_bits = Reg([
        [Bits(1) for _ in range(num_sets)]
        for _ in range(num_ways)],
        reset_value=[
        [0 for _ in range(num_sets)]
        for _ in range(num_ways)])

    read_data <<= meta_array.Read(Set(io.query_req))

    read_tags = [(way, GetTag(read_data, way)) for way in range(num_ways)]

    io.query_resp.hit <<= False

    #
    # When there is not a hit in the cache, the way that is reported here will
    # be used for eviction purposes.
    #

    io.query_resp.way <<= evict_way

    for (way, read_tag) in read_tags:
        valid = valid_bits[way][Set(io.query_req)]
        with (read_tag == Tag(io.read.set)) & valid:
            io.query_resp.hit <<= True
            io.query_resp.way <<= way

    #
    # Update Logic
    #

    new_meta = Wire([Bits(tag_width) for _ in range(num_ways)])

    for way in range(num_ways):
        with io.update.way == way:
            new_meta[way] <<= Tag(io.imem.read_resp.data)
        with otherwise:
            new_meta[way] <<= GetData(io.update.oldmeta, way)

    write_meta = Cat(reversed(new_meta[way] for way in range(num_ways)))

    data_array.Write(io.update.set, write_meta, io.update.valid)

    NameSignals(locals())

@Module
def DCacheDataArray():
    io = Io({
        'read_req': Input({
            'set': Bits(set_addr_width),
            'way': Bits(way_addr_width)
        }),
        'read_resp': Output(Bits(line_width)),
        'update': Input({
            'valid': Bits(1),
            'set': Bits(set_addr_width),
            'way': Bits(way_addr_width),
            'data': Bits(line_width)
        })
    })

    data_array = Mem(num_ways * line_width, num_sets)

    #
    # Read Logic
    #

    read_result = Wire(Bits(num_ways * line_width))
    read_lines = Wire([Bits(line_width) for _ in range(num_ways)])
    read_result <<= data_array.ReadComb(io.read_req.set)

    for way in range(num_ways):
        read_lines[way] <<= GetData(read_result, way)

    io.read_resp <<= read_lines[io.read_req.way]

    #
    # Update Logic
    #

    new_data = Wire([Bits(line_width) for _ in range(num_ways)])
    update_data = data_array.ReadComb(io.update.set)

    for way in range(num_ways):
        with io.update.way == way:
            new_data[way] <<= Tag(io.imem.read_resp.data)
        with otherwise:
            new_data[way] <<= GetData(data, way)

    write_data = Cat(reversed(new_data[way] for way in range(num_ways)))

    data_array.Write(io.update.set, write_data, io.update.valid)

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
    miss_req_sent = Reg(Bits(1), reset_value=False)
    miss_evict_sent = Reg(Bits(1), reset_value=False)

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
    # Miss Handling
    #

    miss_active <<= ~meta_array.quer_resp.hit
    io.cpu_resp.miss <<= miss_active | ~meta_array.quer_resp.hit

    #
    # Handle sending the memory request for a miss. This can wait an arbitrary
    # number of cycles for the memory to become ready.
    #
    # Note: This icache assumes the requested addr is held constant until the
    # miss has been serviced.
    #

    io.dmem.read_req.addr <<= io.cpu_req
    io.dmem.read_req.valid <<= False
    io.dmem.write_req.

    with ~miss_req_sent & (miss_active | ~hit):
        io.dmem.read_req.valid <<= True

        with io.dmem.read_req.ready:
            miss_req_sent <<= True

    #
    # Now wait for the respone. When it comes in, pick a way to replace and
    # update the meta and data arrays. For now, just replace a random line
    # determined by a modulo cycle counter (replace_way).
    #

    replace_way = Reg(Bits(way_addr_width), reset_value=0)
    replace_way <<= replace_way + 1

    meta_write = Wire(Bits(1))
    data_write = Wire(Bits(1))

    ready_for_mem = Wire(Bits(1))
    ready_for_mem <<= miss_active & miss_req_sent

    io.imem.read_resp.ready <<= ready_for_mem

    #
    # Compute the new meta and data to write to the meta array. This is the
    # same as the original metadata with the tag corresponding to replace_way
    # replaced with the tag of the current request.
    #


    new_tags = Wire([Bits(tag_width) for _ in range(num_ways)])

    for way in range(num_ways):
        with replace_way == way:
            new_tags[way] <<= Tag(io.cpu_req)
            new_data[way] <<= Tag(io.imem.read_resp.data)
        with otherwise:
            new_tags[way] <<= GetTag(meta, way)
            new_data[way] <<= GetData(data, way)

    meta_write_data = Cat(reversed([
        new_tags[way]
        for way in range(num_ways)
    ]))

    data_write_data = Cat(reversed([
        new_data[way]
        for way in range(num_ways)
    ]))

    #
    # Similarly, compute the data to write to the data array.
    #

    complete_miss = Wire(Bits(1))
    complete_miss <<= io.imem.read_resp.valid & ready_for_mem

    with complete_miss:
        miss_active <<= False
        miss_req_sent <<= False
        valid_bits[way][Set(io.cpu_req)] <<= True

    meta_array.Write(Set(io.cpu_req), meta_write_data, complete_miss)
    data_array.Write(Set(io.cpu_req), data_write_data, complete_miss)

    NameSignals(locals())



