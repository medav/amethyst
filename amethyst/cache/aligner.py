from atlas import *
from ..support import *

@Module
def Aligner(CC : CacheConfig):
    io = Io({
        'addr': Input(Bits(C['paddr-width'])),
        'rtype': Input(Bits(access_rtype.bitwidth)),
        'line': Input(Bits(CC.line_width)),
        'result': Output(Bits(C['core-width']))
    })

    zero = Wire(Bits(1))
    addr_byte_index = Wire(Bits(CC.line_index_width))
    addr_byte_index <<= CC.Index(io.addr)

    zero <<= 0
    io.result <<= 0

    def SplitLine(line, asize):
        assert CC.line_width % asize == 0
        data = Wire([Bits(asize) for _ in range(CC.line_width // asize)])
        for i in range(CC.line_width // asize):
            data[i] <<= io.line(asize * (i + 1) - 1, asize * i)
        return data

    def GetIndex(byte_index, asize):
        return byte_index(byte_index.width - 1, Log2Ceil(asize // 8))

    def SignExtend(data, width):
        sign_bit = data(data.width - 1, data.width - 1)
        return Cat([Fill(sign_bit, width - data.width), data])

    def ZeroExtend(data, width):
        return Cat([Fill(zero, width - data.width), data])

    if CC.cache_type == 'icache':
        data_words = SplitLine(io.line, 32)
        io.result <<= ZeroExtend(
            data_words[GetIndex(addr_byte_index, 32)],
            C['core-width'])

    else:
        data_bytes = SplitLine(io.line, 8)
        data_byte = data_bytes[addr_byte_index]

        data_hwords = SplitLine(io.line, 16)
        addr_hword_index = GetIndex(addr_byte_index, 16)
        data_hword = data_hwords[addr_hword_index]

        data_words = SplitLine(io.line, 32)
        addr_word_index = GetIndex(addr_byte_index, 32)
        data_word = data_words[addr_word_index]

        data_dwords = SplitLine(io.line, 64)
        addr_dword_index = GetIndex(addr_byte_index, 64)
        data_dword = data_dwords[addr_dword_index]

        with io.rtype == access_rtype.b:
            io.result <<= SignExtend(data_byte, C['core-width'])

        with io.rtype == access_rtype.bu:
            io.result <<= ZeroExtend(data_byte, C['core-width'])

        with io.rtype == access_rtype.h:
            io.result <<= SignExtend(data_hword, C['core-width'])

        with io.rtype == access_rtype.hu:
            io.result <<= ZeroExtend(data_hword, C['core-width'])

        with io.rtype == access_rtype.w:
            io.result <<= SignExtend(data_word, C['core-width'])

        with io.rtype == access_rtype.wu:
            io.result <<= ZeroExtend(data_word, C['core-width'])

        with io.rtype == access_rtype.d:
            io.result <<= data_dword

    NameSignals(locals())