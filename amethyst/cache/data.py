from atlas import *
from ..support import *

@Module
def CacheDataArray(CC : CacheConfig):
    io = Io({
        'read': Input({
            'addr': Bits(C['paddr-width'])
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
        data_arrays[way].Read(CC.Set(io.read.addr))
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