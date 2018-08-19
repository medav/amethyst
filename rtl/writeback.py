from atlas import *
from interfaces import *
from common import *

from config import config as C

@Module
def WritebackStage():
    io = Io({
        'mem_wb': Input(mem_wb_bundle),
        'mem_read_data': Input(Bits(C['core-width'])),
        'reg_write': Output(reg_write_bundle)
    })

    io.reg_write.w_addr <<= io.mem_wb.inst_data.rd
    io.reg_write.w_data <<= io.mem_read_data
    io.reg_write.w_en <<= io.mem_wb.wb_ctrl.mem_to_reg

    NameSignals(locals())