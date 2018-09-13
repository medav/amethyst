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
num_ways = C['icache']['num-ways']
line_width = C['icache']['line-width']
line_bytes = line_width // 8

set_addr_width = Log2Ceil(num_sets)
line_index_width = Log2Ceil(line_bytes)
way_addr_width = Log2Ceil(num_ways)

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

Tag = lambda addr: addr(paddr_width - 1, untag_width)
Set = lambda addr: addr(untag_width - 1, line_index_width)
Index = lambda addr: addr(line_index_width - 1, 0)
GetTag = lambda meta, way: meta(tag_width * (way + 1) - 1, tag_width * way)
GetData = lambda data, way: data(line_width * (way + 1) - 1, line_width * way)

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
        }),
        'imem': Output({
            'read_req': mem_read_request,
            'read_resp': mem_read_response
        }),
    })

    aligner = Instance(Aligner())

    valid_bits = Reg([
        [Bits(1) for _ in range(num_sets)]
        for _ in range(num_ways)],
        reset_value=[
        [0 for _ in range(num_sets)]
        for _ in range(num_ways)])

    miss_active = Reg(Bits(1), reset_value=False)
    miss_req_sent = Reg(Bits(1), reset_value=False)

    hit = Wire(Bits(1))
    line = Wire(Bits(line_width))

    meta_array = Mem(tag_width * num_ways, num_sets)
    data_array = Mem(line_width * num_ways, num_sets)

    #
    # Read the set from the meta and data arrays that is being requested.
    #

    meta = meta_array.ReadComb(Set(io.cpu_req))
    data = data_array.ReadComb(Set(io.cpu_req))

    #
    # In parallel, compare all tags in the set against the request. This will
    # produce a _Python_ list (not an Atlas list) of 1 bit (bool) values.
    #

    tag_match_list = [
        Tag(io.cpu_req) == GetTag(meta, way)
        for way in range(num_ways)
    ]

    #
    # This ands the resulting tag comparison with the corresponding valid bit
    # to determine if any of the ways have a hit.
    #

    match_list = [
        tag_match_list[way] & valid_bits[way][Set(io.cpu_req)]
        for way in range(num_ways)
    ]

    #
    # Here use Python's built in reduce function to perform the logical or of
    # all the match bits. Any one being true indicates a hit in the cache.
    #

    hit <<= reduce(lambda a, b: a | b, match_list)

    #
    # This implements the "way mux" that selects out a line from the read data
    # based on which way has a matching tag.
    #

    line <<= 0
    for way in range(num_ways):
        with match_list[way]:
            line <<= GetData(data, way)

    #
    # Give the resulting line to the aligner so it can be sent out to the cpu.
    #

    aligner.cpu_req <<= io.cpu_req
    aligner.line <<= line

    io.cpu_resp.data <<= aligner.result

    #
    # Miss Handling
    #

    miss_active <<= ~hit
    io.cpu_resp.miss <<= miss_active | ~hit

    #
    # Handle sending the memory request for a miss. This can wait an arbitrary
    # number of cycles for the memory to become ready.
    #
    # Note: This icache assumes the requested addr is held constant until the
    # miss has been serviced.
    #

    io.imem.read_req.addr <<= io.cpu_req
    io.imem.read_req.valid <<= False

    with ~miss_req_sent & (miss_active | ~hit):
        io.imem.read_req.valid <<= True

        with io.imem.read_req.ready:
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

    new_data = Wire([Bits(line_width) for _ in range(num_ways)])
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



