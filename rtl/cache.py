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
            'tag': Bits(CC.tag_width)
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
            io.update.tag,
            io.update.valid & (io.update.way == way))

    NameSignals(locals())

@Module
def CacheDataArray(CC : CacheConfig):
    io = Io({
        'read': Input({
            'set': Bits(CC.set_addr_width)
        }),
        'resp': Output([Bits(CC.line_width) for _ in range(CC.num_ways)]),
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

    read_data = [
        data_arrays[way].Read(io.read.set)
        for way in range(CC.num_ways)
    ]

    for way in range(CC.num_ways):
        io.resp[way] <<= read_data[way]

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
        'addr': Input(Bits(C['paddr-width'])),
        'rtype': Input(Bits(access_rtype.bitwidth)),
        'line': Input(Bits(CC.line_width)),
        'result': Output(Bits(output_width))
    })

    zero = Wire(Bits(1))
    addr_byte_index = Wire(Bits(CC.line_index_width))
    addr_byte_index <<= CC.Index(io.addr)

    zero <<= 0
    io.result <<= 0

    def SplitLine(line, asize):
        assert CC.line_width % asize == 0
        data = Wire([Bits(asize) for _ in range(CC.line_width // asize)])
        for i in range(CC.line_width // asize):
            data[i] <<= io.line(asize * (i + 1) - 1, asize * i)
        return data

    def GetIndex(byte_index, asize):
        return byte_index(byte_index.width - 1, Log2Ceil(asize // 8))

    def SignExtend(data, width):
        sign_bit = data(data.width - 1, data.width - 1)
        return Cat([Fill(sign_bit, width - data.width), data])

    def ZeroExtend(data, width):
        return Cat([Fill(zero, width - data.width), data])

    if CC.cache_type == 'icache':
        data_words = SplitLine(io.line, 32)
        io.result <<= data_words[GetIndex(addr_byte_index, 32)]

    else:
        data_bytes = SplitLine(io.line, 8)
        data_byte = data_bytes[addr_byte_index]

        data_hwords = SplitLine(io.line, 16)
        addr_hword_index = GetIndex(addr_byte_index, 16)
        data_hword = data_hwords[addr_hword_index]

        data_words = SplitLine(io.line, 32)
        addr_word_index = GetIndex(addr_byte_index, 32)
        data_word = data_words[addr_word_index]

        data_dwords = SplitLine(io.line, 64)
        addr_dword_index = GetIndex(addr_byte_index, 64)
        data_dword = data_dwords[addr_dword_index]

        with io.rtype == access_rtype.b:
            io.result <<= SignExtend(data_byte, C['core-width'])

        with io.rtype == access_rtype.bu:
            io.result <<= ZeroExtend(data_byte, C['core-width'])

        with io.rtype == access_rtype.h:
            io.result <<= SignExtend(data_hword, C['core-width'])

        with io.rtype == access_rtype.hu:
            io.result <<= ZeroExtend(data_hword, C['core-width'])

        with io.rtype == access_rtype.w:
            io.result <<= SignExtend(data_word, C['core-width'])

        with io.rtype == access_rtype.wu:
            io.result <<= ZeroExtend(data_word, C['core-width'])

        with io.rtype == access_rtype.d:
            io.result <<= data_dword

    NameSignals(locals())

@Module
def Cache(CC : CacheConfig):
    io = Io({
        'cpu_req': Input(cpu_cache_req),
        'cpu_resp': Output(cpu_cache_resp),
        'cpu_stall': Input(Bits(1)),
        'miss_stall': Output(Bits(1)),
        'mem': Output(mem_bundle)
    })

    meta_array = Instance(CacheMetaArray(CC))
    data_array = Instance(CacheDataArray(CC))
    aligner = Instance(Aligner(CC))

    stall = Wire(Bits(1))

    s0_req = Wire(cpu_cache_req)

    s1_req = Reg(cpu_cache_req, reset_value=cpu_cache_req_reset)
    s1_read_data = Wire(Bits(CC.line_width))

    s2_req = Reg(cpu_cache_req, reset_value=cpu_cache_req_reset)
    s2_resp_data = Reg(Bits(C['core-width']), reset_value=0)

    mstates = Enum(['idle', 'read', 'evict', 'update'])
    miss_state = Reg(Bits(mstates.bitwidth), reset_value=mstates.idle)

    io.miss_stall <<= stall

    with ~stall & ~io.cpu_stall:
        s1_req <<= s0_req
        s2_req <<= s1_req
        s2_resp_data <<= aligner.result

    #
    # Stage 0: Metadata read
    #

    s0_req <<= io.cpu_req

    meta_array.read.addr <<= s0_req.addr
    data_array.read.set <<= CC.Set(s0_req.addr)

    #
    # Stage 1: Handle Request
    #

    # N.B. This is the "way mux"
    s1_read_data <<= data_array.resp[meta_array.resp.way]

    aligner.addr <<= s1_req.addr
    aligner.line <<= s1_read_data
    aligner.rtype <<= s1_req.rtype

    #
    # Stage 2: Select and align data
    #

    io.cpu_resp.data <<= s2_resp_data

    #
    # Miss Handling
    #
    # Note: this is done via state machine and this cache will output a stall
    # signal until the miss has been serviced and the pipeline can resume as if
    # nothing ever happened.
    #

    evict_way = Reg(Bits(CC.way_addr_width), reset_value=0)
    evict_data = Reg(Bits(CC.line_width), reset_value=0)

    stall <<= (miss_state != mstates.idle) | \
        (~meta_array.resp.hit & s1_req.valid & s1_req.read)

    #
    # Defaults
    #

    io.mem.read.valid <<= False
    io.mem.read.addr <<= 0

    io.mem.write.valid <<= False
    io.mem.write.addr <<= 0
    io.mem.write.data <<= 0

    io.mem.resp.ready <<= False

    meta_array.update.way <<= evict_way
    meta_array.update.set <<= CC.Set(io.mem.resp.addr)
    meta_array.update.tag <<= CC.Tag(io.mem.resp.addr)

    data_array.update.way <<= evict_way
    data_array.update.set <<= CC.Set(io.mem.resp.addr)
    data_array.update.data <<= io.mem.resp.data

    meta_array.update.valid <<= False
    data_array.update.valid <<= False

    with miss_state == mstates.idle:
        with ~meta_array.resp.hit & s1_req.valid & s1_req.read:
            evict_way <<= meta_array.resp.way
            evict_data <<= s1_read_data

            #
            # Here we are about to take a miss. For the dcache, if the reported
            # way to evict is valid (in meta data), then the data needs to be
            # written to memory before new data can be pulled into the cache.
            # In that case, move to the evict state. If this is an icache or the
            # way does not contain valid data, go immediately to the read state.
            #

            if CC.cache_type == 'dcache':
                with meta_array.resp.valid:
                    miss_state <<= mstates.evict
                with otherwise:
                    miss_state <<= mstates.read
            else:
                miss_state <<= mstates.read

    with miss_state == mstates.evict:

        #
        # Here wait for the memory to be ready for a write. Send the evict data
        # to the memory and move to the read state.
        #

        io.mem.write.valid <<= True
        io.mem.write.addr <<= s1_req.addr
        io.mem.write.data <<= evict_data

        with io.mem.write.ready:
            miss_state <<= mstates.read

    with miss_state == mstates.read:

        #
        # Here send the request to the memory the missed line of data.
        #

        io.mem.read.valid <<= True
        io.mem.read.addr <<= s1_req.addr

        with io.mem.read.ready:
            miss_state <<= mstates.update

    with miss_state == mstates.update:

        #
        # Here wait for the read request to be fulfilled. When it is, the meta
        # and data arrays are ready to be updated. When the data is ready, the
        # stall signal can be pulled low.
        #

        io.mem.resp.ready <<= True
        aligner.line <<= io.mem.resp.data

        with io.mem.resp.valid:
            stall <<= False
            meta_array.update.valid <<= True
            data_array.update.valid <<= True

    NameSignals(locals())



