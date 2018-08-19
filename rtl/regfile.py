from atlas import *
from config import config as C

@Module
def RegisterFile():
    io = Io({
        'r0_addr': Input(Bits(Log2Ceil(C['reg-count']))),
        'r1_addr': Input(Bits(Log2Ceil(C['reg-count']))),
        'w0_addr': Input(Bits(Log2Ceil(C['reg-count']))),
        'w0_data': Input(Bits(C['core-width'])),
        'w0_en' : Input(Bits(1)),
        'r0_data': Output(Bits(C['core-width'])),
        'r1_data': Output(Bits(C['core-width']))
    })

    reg_array = Reg(
        [Bits(C['core-width']) for _ in range(C['reg-count'])],
        reset_value=[0 for _ in range(C['reg-count'])])

    with io.r0_addr == 0:
        io.r0_data <<= 0
    with otherwise:
        io.r0_data <<= reg_array[io.r0_addr]

    with io.r1_addr == 0:
        io.r1_data <<= 0
    with otherwise:
        io.r1_data <<= reg_array[io.r1_addr]

    with (io.w0_addr != 0) & io.w0_en:
        reg_array[io.w0_addr] <<= io.w0_data

    NameSignals(locals())
