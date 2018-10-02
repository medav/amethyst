from atlas import *
from ..support import *

from .aligner import Aligner
from .data import CacheDataArray
from .meta import CacheMetaArray

#
# Addresses in this cache are broken up as follows:
#
# | -------- tag -------- | - set - | - index - |
# | -------- tag -------- | ------ untag ------ |
#
# The "untag" is the set + index
#

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
    about_to_miss = Wire(Bits(1))
    miss_state = Reg(Bits(mstates.bitwidth), reset_value=mstates.idle)
    miss_data = Reg(Bits(C['core-width']), reset_value=0)
    complete_miss = Reg(Bits(1), reset_value=False)

    io.miss_stall <<= stall
    complete_miss <<= False

    with ~stall & ~io.cpu_stall:
        s1_req <<= s0_req
        s2_req <<= s1_req

        with complete_miss:
            s2_resp_data <<= miss_data

        with otherwise:
            s2_resp_data <<= aligner.result

    #
    # Stage 0: Cache read
    #
    # N.B. The meta and data arrays will _always_ read (I.e. have no read
    # enable signal). Therefore, when we stall, give the current s1_req's addr
    # to them to effectively "replay" the read.
    #

    s0_req <<= io.cpu_req

    with stall | io.cpu_stall:
        meta_array.read.addr <<= s1_req.addr
        data_array.read.addr <<= s1_req.addr

    with otherwise:
        meta_array.read.addr <<= s0_req.addr
        data_array.read.addr <<= s0_req.addr

    #
    # Stage 1: Handle Request
    #

    # This is the "way mux"
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

    about_to_miss <<= ~meta_array.resp.hit & s1_req.valid
    stall <<= (miss_state != mstates.idle) | about_to_miss

    evict_way = Reg(Bits(CC.way_addr_width), reset_value=0)
    evict_data = Reg(Bits(CC.line_width), reset_value=0)

    #
    # Defaults
    #

    io.mem.read <<= {
        'valid': False,
        'addr': 0
    }

    io.mem.write <<= {
        'valid': False,
        'addr': 0,
        'data': 0
    }

    io.mem.resp.ready <<= False

    meta_array.update <<= {
        'valid': False,
        'way': evict_way,
        'set': CC.Set(io.mem.resp.addr),
        'tag': CC.Tag(io.mem.resp.addr)
    }

    data_array.update <<= {
        'valid': False,
        'way': evict_way,
        'set': CC.Set(io.mem.resp.addr),
        'data': io.mem.resp.data
    }

    with miss_state == mstates.idle:
        with about_to_miss:
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

        io.mem.write <<= {
            'valid': True,
            'addr': s1_req.addr,
            'data': evict_data
        }

        with io.mem.write.ready:
            miss_state <<= mstates.read

    with miss_state == mstates.read:

        #
        # Here send the request to the memory the missed line of data.
        #

        io.mem.read <<= {
            'valid': True,
            'addr': s1_req.addr
        }

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
            miss_data <<= aligner.result
            complete_miss <<= True
            meta_array.update.valid <<= True
            data_array.update.valid <<= True
            miss_state <<= mstates.idle
            s1_req <<= cpu_cache_req_reset

    NameSignals(locals())



