from atlas import *
from ..support import *

ras_size = C['ras']['size']
ras_index_width = Log2Ceil(ras_size)

@Module
def ReturnAddressStack():
    io = Io({
        'ctrl': Input(ras_ctrl_bundle),
        'top': Output(Bits(C['paddr-width']))
    })

    rstack = Mem(C['paddr-width'], ras_size)

    #
    # The return address stack is implemented as a circular buffer so values
    # don't need to be shifted around wasting energy.
    #

    push_address = Reg(Bits(ras_index_width), reset_value=0)
    top_address = Wire(Bits(ras_index_width))
    write_address = Wire(Bits(ras_index_width))

    top_address <<= push_address - 1
    pc_plus_4 = io.ctrl.pc + 4

    with io.ctrl.push & io.ctrl.pop:
        write_address <<= top_address

    with otherwise:
        write_address <<= push_address

        with io.ctrl.push:
            push_address <<= push_address + 1

        with io.ctrl.pop:
            push_address <<= push_address - 1

    rstack.Write(write_address, pc_plus_4(C['core-width'] - 1, 0), io.ctrl.push)
    io.top <<= rstack.Read(top_address)

    NameSignals(locals())