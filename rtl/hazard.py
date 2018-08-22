from atlas import *
from interfaces import *
from common import *

from config import config as C

@Module
def HazardUnit():
    io = Io({
        'ex_mem_read': Input(Bits(1)),
        'ex_rd': Input(Bits(Log2Ceil(C['reg-count']))),
        'id_rs1': Input(Bits(Log2Ceil(C['reg-count']))),
        'id_rs2': Input(Bits(Log2Ceil(C['reg-count']))),
        'data_hazard': Output(Bits(1))
    })

    io.data_hazard <<= 0

    #
    # This logic is taken straight from Hennessy and Patterson's comp org book.
    # All it does is signal when there is a data hazard between the ex and mem
    # stage which means a pipeline stall needs to happen or bad things happen.
    #

    with io.ex_mem_read:
        with (io.ex_rd == io.id_rs1) | (io.ex_rd == io.id_rs2):
            io.data_hazard <<= 1

    NameSignals(locals())