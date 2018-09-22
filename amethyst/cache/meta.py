from atlas import *
from ..support import *

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

    read_tag = Reg(Bits(CC.tag_width), reset_value=0)
    read_tag <<= CC.Tag(io.read.addr)

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

    valid_reg = Reg(
        [Bits(1) for _ in range(CC.num_ways)],
        reset_value=[0 for _ in range(CC.num_ways)])

    io.resp.way <<= evict_way
    io.resp.hit <<= False
    io.resp.valid <<= valid_reg[evict_way]

    #
    # Read Logic
    #

    read_data = [
        meta_arrays[way].Read(CC.Set(io.read.addr))
        for way in range(CC.num_ways)
    ]

    for way in range(CC.num_ways):
        valid_reg[way] <<= valid_bits[way][CC.Set(io.read.addr)]

        with (read_data[way] == read_tag) & valid_reg[way]:
            io.resp.hit <<= True
            io.resp.way <<= way
            io.resp.valid <<= valid_reg[way]

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
