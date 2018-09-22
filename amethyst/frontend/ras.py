from atlas import *
from ..support import *

ras_size = C['ras']['size']
ras_index_width = Log2Ceil(ras_size)

@Module
def ReturnAddressStack():
    io = Io({
        'ctrl': Input(ras_ctrl_bundle),
        'top': C['paddr-width']
    })

    rstack = Mem(C['paddr-width'], ras_size)

    #
    # The return address stack is implemented as a circular buffer so values
    # don't need to be shifted around wasting energy.
    #

    push_address = Reg(Bits(ras_index_width), reset_value=0)
    head = Wire(Bits(ras_index_width))
    write_address = Wire(Bits(ras_index_width))

    head <<= push_address - 1


    with io.ctrl.push & io.ctrl.pop:
        write_address <<= head

    with otherwise:
        write_address <<= push_address

        with io.ctrl.push:
            push_address <<= push_address + 1

        with io.ctrl.pop.valid:
            push_address <<= push_address - 1

    rstack.Write(write_address, io.ctrl.pc + 4, io.ctrl.push)
    io.pop.address <<= rstack.Read(head)

    NameSignals(locals())