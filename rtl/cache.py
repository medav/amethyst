from dataclasses import dataclass
from functools import reduce

from atlas import *
from interfaces import *
from instructions import *
from ops import *

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

    def Tag(self, addr):
        return addr(C['paddr-width'] - 1, self.untag_width)

    def Set(self, addr):
        return addr(self.untag_width - 1, self.line_index_width)

    def Index(self, addr):
        return addr(self.line_index_width - 1, 0)

    @staticmethod
    def FromCacheType(cache_type : str):
        return CacheConfig(
            cache_type=cache_type,
            num_sets=C[cache_type]['num-sets'],
            num_ways=C[cache_type]['num-ways'],
            line_width=C[cache_type]['line-width'])

#
# Addresses in this cache are broken up as follows:
#
# | -------- tag -------- | - set - | - index - |
# | -------- tag -------- | ------ untag ------ |
#
# The "untag" is the set + index
#

@Module
def CacheMetaArray(CC : CacheConfig):
    io = Io({
        'read': Input({
            'addr': Bits(C['paddr-width'])
        }),
        'resp': Output({
            'hit': Bits(1),
            'way': Bits(CC.way_addr_width),
            'valid' : Bits(1)
        }),
        'update': Input({
            'valid': Bits(1),
            'set': Bits(CC.set_addr_width),
            'way': Bits(CC.way_addr_width),
            'meta': Bits(CC.num_ways * CC.tag_width)
        })
    })

    meta_arrays = [
        Mem(CC.tag_width, CC.num_sets)
        for _ in range(CC.num_ways)
    ]

    resp_way = Wire(Bits(CC.way_addr_width))
    resp_hit = Wire(Bits(1))
    resp_valid = Wire(Bits(1))

    io.resp.way <<= resp_way
    io.resp.hit <<= resp_hit
    io.resp.valid <<= resp_valid

    #
    # When this array reports a miss, evict_way is used to report the way that
    # should be evicted (if needed).
    #

    evict_way = Reg(Bits(CC.way_addr_width), reset_value=0)
    evict_way <<= evict_way + 1

    valid_bits = [
        ValidSet(CC.num_sets)
        for _ in range(CC.num_ways)
    ]

    #
    # Read Logic
    #

    read_data = [
        meta_arrays[way].Read(CC.Set(io.read.addr))
        for way in range(CC.num_ways)
    ]

    resp_hit <<= False
    resp_way <<= evict_way
    resp_valid <<= False

    for way in range(CC.num_ways):
        valid = valid_bits[way][CC.Set(io.read.addr)]
        with (read_data[way] == CC.Tag(io.read.addr)) & valid:
            io.resp.hit <<= True
            resp_way <<= way
            io.resp.valid <<= valid

        with resp_way == way:
            resp_valid <<= valid

    #
    # Update Logic
    #

    for way in range(CC.num_ways):
        valid_bits[way].Set(
            io.update.set,
            True,
            io.update.valid & (io.update.way == way))

        meta_arrays[way].Write(
            io.update.set,
            io.update.meta,
            io.update.valid & (io.update.way == way))

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

    read_lines = Wire([Bits(CC.line_width) for _ in range(CC.num_ways)])
    read_data = [
        data_arrays[way].Read(io.read.set)
        for way in range(CC.num_ways)
    ]

    for way in range(CC.num_ways):
        read_lines[way] <<= read_data[way]

    io.resp <<= read_lines[io.read.way]

    #
    # Update Logic
    #

    for way in range(CC.num_ways):
        data_arrays[way].Write(
            io.update.set,
            io.update.data,
            io.update.valid & (io.update.way == way))

    NameSignals(locals())

@Module
def Aligner(CC : CacheConfig):
    output_width = 32 if CC.cache_type == 'icache' else C['core-width']

    io = Io({
        'rtype': Input(Bits(access_rtype.bitwidth)),
        'line': Input(Bits(CC.line_width)),
        'result': Output(Bits(output_width))
    })

    if CC.cache_type == 'icache':
        pass

    else:
        pass

    io.result <<= 0

    NameSignals(locals())

@Module
def Cache(CC : CacheConfig):
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

    meta_array = Instance(CacheMetaArray(CC))
    data_array = Instance(CacheDataArray(CC))
    aligner = Instance(Aligner(CC))

    stall = Wire(Bits(1))

    s0_req = Wire(cpu_dcache_req)
    s1_req = Reg(cpu_dcache_req, reset_value=cpu_dcache_req_reset)
    s2_req = Reg(cpu_dcache_req, reset_value=cpu_dcache_req_reset)

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

    meta_array.read.addr <<= s1_req.addr

    #
    # Stage 1: Handle Request
    #

    data_array.read.set <<= CC.Set(s2_req.addr)
    data_array.read.way <<= meta_array.resp.way

    #
    # Stage 2: Select and align data
    #

    # aligner.rtype <<=



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
        with ~meta_array.resp.hit & s2_req.valid:
            miss_state <<= mstates.read

    with miss_state == mstates.read:
        io.mem.read.valid <<= ~miss_read_sent
        # io.mem.read.addr <<=
        # with io.mem.read.ready:

    with miss_state == mstates.evict:
        pass

    with miss_state == mstates.update:
        pass



    stall <<= (miss_state != mstates.idle) | ~meta_array.resp.hit

    NameSignals(locals())



