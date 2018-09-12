from atlas import *
from interfaces import *

from config import *

@Module
def BranchPredictor():
    io = Io({
        'cur_pc': Input(Bits(paddr_width)),
        'pred': Output({
            'taken': Bits(1)
        }),
        'update': Input({
            'valid': Bits(1),
            'pc': Bits(paddr_width),
            'taken': Bits(1)
        })
    })

    io.pred.taken <<= True

    NameSignals(locals())

