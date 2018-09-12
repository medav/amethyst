from atlas import *
from interfaces import *

from config import *

ras_size = C['ras']['size']
ras_index_width = Log2Ceil(ras_size)

@Module
def ReturnAddressStack():
    io = Io({
        'push': Input({
            'valid': Bits(1),
            'address': Bits(paddr_width)
        }),
        'pop': Output({
            'valid': Flip(Bits(1)),
            'address': Bits(paddr_width)
        })
    })

    rstack = Mem(paddr_width, ras_size)

    #
    # The return address stack is implemented as a circular buffer so values
    # don't need to be shifted around wasting energy.
    #

    enq_address = Reg(Bits(ras_index_width), reset_value=0)
    head = Wire(Bits(ras_index_width))

    head <<= enq_address - 1

    with io.push.valid & ~io.pop.valid:
        enq_address <<= enq_address + 1

    with io.pop.valid & ~io.push.valid:
        enq_address <<= enq_address - 1

    rstack.Write(enq_address, io.push.address, io.push.valid)
    io.pop.address <<= rstack.Read(head)

    NameSignals(locals())