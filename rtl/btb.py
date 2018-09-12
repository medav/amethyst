from atlas import *
from interfaces import *

from config import config as C

btb_size = C['btb']['size']
hash_bits = Log2Ceil(btb_size)
tag_bits = C['paddr-width'] - hash_bits

TargetAddress = lambda btb_entry: btb_entry

def BtbHashFunction(pc):
    return pc(hash_bits, 0)

@Module
def BranchTargetBuffer():
    io = Io({
        'cur_pc': Input(Bits(C['paddr-width'])),
        'pred': Output({
            'valid': Bits(1),
            'target': Bits(C['paddr-width'])
        }),
        'update': Input({
            'valid': Bits(1),
            'pc': Bits(C['paddr-width']),
            'target': Bits(C['paddr-width'])
        })
    })

    valid_bits = Reg(
        [Bits(1) for _ in range(btb_size)],
        reset_value=[0 for _ in range(btb_size)])

    table = Mem(tag_bits + C['paddr-width'], btb_size)

    table_index = BtbHashFunction(io.cur_pc)

    io.pred.valid <<= valid_bits[table_index]
    io.pred.target <<= table.Read(table_index)

    update_index = BtbHashFunction(io.update.pc)
    table.Write(update_index, io.update.target, io.update.valid)

    with io.update.valid:
        valid_bits[update_index] <<= True

    NameSignals(locals())