from atlas import *
from interfaces import *

from config import *

paddr_width = paddr_width
btb_size = C['btb']['size']
hash_bits = Log2Ceil(btb_size)
tag_bits = paddr_width - hash_bits
flag_bits = 1

entry_size = tag_bits + flag_bits + paddr_width

Tag = lambda btb_entry: btb_entry(entry_size - 1, entry_size - tag_bits)
IsReturn = lambda btb_entry: btb_entry(entry_size - tag_bits - 1, paddr_width)
Target = lambda btb_entry: btb_entry(paddr_width - 1, 0)

def BtbHashFunction(pc):
    return pc(hash_bits, 0)

@Module
def BranchTargetBuffer():
    io = Io({
        'cur_pc': Input(Bits(paddr_width)),
        'pred': Output({
            'valid': Bits(1),
            'is_return': Bits(1),
            'target': Bits(paddr_width)
        }),
        'update': Input({
            'valid': Bits(1),
            'pc': Bits(paddr_width),
            'target': Bits(paddr_width),
            'is_return': Bits(1)
        })
    })

    valid_bits = Reg(
        [Bits(1) for _ in range(btb_size)],
        reset_value=[0 for _ in range(btb_size)])

    tag_match = Wire(Bits(1))
    table = Mem(entry_size, btb_size)

    #
    # Each entry in the BTB has the following layout:
    #
    # msb                                             lsb
    # | ---- tag ---- | flags | ---- target addr ---- |
    #

    read_entry = Wire(Bits(entry_size))

    #
    # The entry to read is based off the has of the current pc. This hash
    # realisitcally could be anything that can be produced combinationally but
    # (above) is implemented by extracting the lower order bits of the pc.
    #

    table_index = BtbHashFunction(io.cur_pc)
    read_entry <<= table.Read(table_index)

    tag_match <<= Tag(read_entry) == io.cur_pc(paddr_width - 1, hash_bits)

    #
    # The prediction is only valid when the read tag matches _and_ the entry is
    # valid. This prevents the BTB from ever producing a false positive branch
    # instruction. This is important because the pipeline assumes a non-branch
    # will never be predicted as a branch.
    #

    io.pred.valid <<= valid_bits[table_index] & tag_match
    io.pred.is_return <<= IsReturn(read_entry)
    io.pred.target <<= Target(read_entry)

    #
    # Handle BTB update requests. The BTB is effectively a direct mapped cache
    # so all that happens is a simple overwrite of the update_index.
    #
    # The entry to be written (upon an update) is simply the tag of the current
    # pc, flags, and target concatenated together.
    #

    write_entry = Cat([
        io.update.pc(paddr_width - 1, hash_bits),
        io.update.is_return,
        io.update.target
    ])

    update_index = BtbHashFunction(io.update.pc)
    table.Write(update_index, write_entry, io.update.valid)

    with io.update.valid:
        valid_bits[update_index] <<= True

    NameSignals(locals())