from atlas import *

from atlas import *
from interfaces import *
from common import *

from config import config as C

@Module
def IFetchStage():
    io = Io({
        'if_id': Output(if_id_bundle),
    })

    pc = Reg(Bits(C['core-width']))

    io.if_id.inst <<= 0

    NameSignals(locals())