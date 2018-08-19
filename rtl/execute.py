from atlas import *
from interfaces import *
from common import *
from regfile import *

@Module
def ArithmeticLogicUnit():
    io = Io({
        ''
    })

@Module
def ExecuteStage():
    io = Io({
        'in_data': id_ex_bundle,
        'out_data': ex_mem_bundle
    })

    io.out_data.mem_ctrl <<= io.in_data.mem_ctrl
    io.out_data.wb_ctrl <<= io.in_data.wb_ctrl