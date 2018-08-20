from atlas import *

from atlas import *
from interfaces import *
from common import *

from config import config as C

@Module
def IFetchStage():
    io = Io({
        'if_id': Output(if_id_bundle),
        'inst': Output(Bits(32)),
        'imem': Output(imem_bundle),
        'branch': Input(Bits(1)),
        'branch_target': Input(Bits(C['paddr-width']))
    })

    pc = Reg(Bits(C['paddr-width']), reset_value=C['reset-addr'])
    pc <<= pc + 4

    io.imem.r_addr <<= pc
    io.imem.r_en <<= 1

    io.if_id.pc <<= pc
    io.inst <<= io.imem.r_data

    with io.branch:
        pc <<= io.branch_target

    NameSignals(locals())