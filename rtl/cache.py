from dataclasses import dataclass
from functools import reduce

from atlas import *
from interfaces import *
from instructions import *

import forward

from config import *

#
# Since this code is used for both the I+D caches, some disambiguation between
# the parameter sets is needed. The CacheConfig class holds all the relevant
# parameters specific to each cache.
#

@dataclass(unsafe_hash=True)
class CacheConfig(object):

    #
    # Parameters supplied via global config.
    #

    cache_type : str
    num_sets : int
    num_ways : int
    line_width : int

    #
    # Parameters computed from above.
    #

    set_addr_width : int = None
    way_addr_width : int = None
    line_width_bytes : int = None
    line_index_width : int = None
    untag_width : int = None
    tag_width : int = None

    def __post_init__(self):
        self.set_addr_width = Log2Ceil(self.num_sets)
        self.way_addr_width = Log2Ceil(self.num_ways)
        self.line_width_bytes = self.line_width // 8
        self.line_index_width = Log2Ceil(self.line_width_bytes)
        self.untag_width = self.set_addr_width + self.line_index_width
        self.tag_width = C['paddr-width'] - self.untag_width

    def AddrTag(self, addr):
        return addr(C['paddr-width'] - 1, self.untag_width)

    def AddrSet(self, addr):
        return addr(self.untag_width - 1, self.line_index_width)

    def AddrIndex(self, addr):
        return addr(self.line_index_width - 1, 0)

    def MetaTag(self, meta, way):
        return meta(self.tag_width * (way + 1) - 1, self.tag_width * way)

    @staticmethod
    def FromCacheType(cache_type):
        return CacheConfig(
            cache_type=cache_type
            num_sets=C[cache_type]['num-sets'],
            num_ways=C[cache_type]['num-ways'],
            line_width=C[cache_type]['line-size'])

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

@Module
def CacheMetaArray(CC : CacheConfig):
    io = Io({
        'read': Input({
            'addr': Bits(C['paddr-width'])
        }),
        'resp': Output({
            'hit': Bits(1),
            'way': Bits(CC.way_addr_width),
            'meta': Bits(CC.num_ways * CC.tag_width)
        }),
        'write': Input({
            'valid': Bits(1),
            'set': Bits(CC.set_addr_width),
            'way': Bits(CC.way_addr_width),
            'meta': Bits(CC.num_ways * CC.tag_width)
        })
    })

    meta_array = Mem(CC.tag_width * CC.num_ways, CC.num_sets)

    read_data = Wire(Bits(CC.num_ways * CC.tag_width))
    evict_way = Wire(Bits(CC.way_addr_width))

    valid_bits = Reg([
        [Bits(1) for _ in range(CC.num_sets)]
        for _ in range(CC.num_ways)],
        reset_value=[
        [0 for _ in range(CC.num_sets)]
        for _ in range(CC.num_ways)])

    read_data <<= meta_array.Read(CC.AddrSet(io.read.addr))

    read_tags = [
        (way, CC.MetaTag(read_data, way)) for way in range(CC.num_ways)
    ]

    io.query_resp.hit <<= False

    #
    # When there is not a hit in the cache, the way that is reported here will
    # be used for eviction purposes.
    #

    io.query_resp.way <<= evict_way

    for (way, read_tag) in read_tags:
        valid = valid_bits[way][CC.AddrSet(io.read.addr)]
        with (read_tag == CC.AddrTag(io.read.addr)) & valid:
            io.query_resp.hit <<= True
            io.query_resp.way <<= way

    NameSignals(locals())

@Module
def CacheDataArray(CC : CacheConfig):
    io = Io({
        'read': Input({
            'set': Bits(CC.set_addr_width),
            'way': Bits(CC.way_addr_width)
        }),
        'resp': Output(Bits(CC.line_width)),
        'update': Input({
            'valid': Bits(1),
            'set': Bits(CC.set_addr_width),
            'way': Bits(CC.way_addr_width),
            'data': Bits(CC.line_width)
        })
    })

    data_arrays = [
        Mem(CC.line_width, CC.num_sets)
        for _ in range(CC.num_ways)
    ]

    #
    # Read Logic
    #

    read_result = Wire(Bits(CC.num_ways * CC.line_width))
    read_lines = Wire([Bits(CC.line_width) for _ in range(CC.num_ways)])
    read_data = [
        data_arrays[way].Read(io.read.set)
        for way in range(CC.num_ways)
    ]

    for way in range(num_ways):
        read_lines[way] <<= read_data[way]

    io.read_resp <<= read_lines[io.read_req.way]

    #
    # Update Logic
    #

    write_array = Wire([Bits(1) for _ in range(CC.num_ways)])

    for way in range(num_ways):
        write_array[way] <<= io.update.valid & (io.update.way == way)
        data_arrays[way].Write(io.update.set, io.update.data, write_array[way])

    NameSignals(locals())

def UpdateMetaArray(CC, old_data, new_element, update_way, elem_width):
    new_data = Wire([Bits(elem_width) for _ in range(num_ways)])

    Element = lambda way: old_data(elem_width * (way + 1) - 1, elem_width * way)

    for way in range(num_ways):
        with update_way == way:
            new_data[way] <<= new_element
        with otherwise:
            new_data[way] <<= Element(way)

    write_data = Cat(reversed(new_data[way] for way in range(num_ways)))

    NameSignals(locals())
    return new_data

@Module
def Aligner(CC : CacheConfig):
    output_width = 32 if CC.cache_type == 'icache' else C['core-width']

    io = Io({
        'rtype': Input(rtype.bitwidth),
        'line': Input(Bits(CC.line_width)),
        'result': Output(Bits(output_width))
    })

    io.result <<= 0

    NameSignals(locals())

@Module
def Cache(cache_type='dcache'):
    io = Io({
        'cpu_req': Input(cpu_dcache_req),
        'cpu_resp': Output(cpu_dcache_resp),
        'stall': Output(Bits(1)),
        'mem': Output({
            'read': mem_read_request,
            'resp': mem_read_response,
            'write': mem_write_request
        })
    })

    meta_array = Instance(CacheMetaArray(cache_type))
    data_array = Instance(CacheDataArray(cache_type))
    aligner = Instance(Aligner(cache_type))

    stall = Wire(Bits(1))

    s0_req = Wire(cpu_dcache_req)
    s1_req = Reg(cpu_dcache_req, reset_value=cpu_dcache_req_reset)

    captured_meta = Reg(Bits(CC.tag_width * CC.num_ways), reset_value=0)
    mstates = Enum(['idle', 'read', 'evict', 'update'])
    miss_state = Reg(Bits(mstates.bitwidth), reset_value=mstates.idle)

    io.stall <<= stall

    with ~stall:
        s1_req <<= s0_req
        s2_req <<= s1_req

    #
    # Stage 0: Metadata read
    #

    s0_req <<= io.cpu_req
    io.ready <<= True

    meta_array.read <<= s1_req.addr

    #
    # Stage 1: Handle Request
    #

    data_array.read.set <<= Set(s2_req.addr)
    data_array.read.way <<= meta_array.query_resp.way

    #
    # Stage 2: Select and align data
    #

    aligner.rtype <<=



    #
    # Miss Handling
    #
    # Note: this is done via state machine and this cache will output a stall
    # signal until the miss has been serviced and the pipeline can resume as if
    # nothing ever happened.
    #

    miss_read_sent = Reg(Bits(1), reset_value=False)
    miss_evict_sent = Reg(Bits(1), reset_value=False)

    io.mem.read.valid <<= False

    with miss_state == mstates.idle:
        with ~meta_array.quer_resp.hit & s2_req.valid:
            miss_state <<= mstates.read

    with miss_state == mstates.read_evict:
        io.mem.read.valid <<= ~miss_read_sent
        io.mem.read.addr <<=
        with io.mem.read.ready:



    with miss_state == mstates.update:



    stall <<= (miss_state != mstates.idle) | ~meta_array.quer_resp.hit


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



