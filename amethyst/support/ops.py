from atlas import *

class BitOrReduceOperator(Operator):
    """Operator that reduces a bits signal via logic OR."""

    #
    # N.B. This is a good example of how extendable Atlas/Python is. It enables
    # user code to create new synthesizable operations that generate custom
    # Verilog code.
    #
    # Since Atlas doesn't currently have a good way of producing an OR reduction
    # tree, we can just make our own, here!
    #

    def __init__(self, bits):
        super().__init__('reduce_or')
        self.bit_vec = [FilterFrontend(bits(i, i)) for i in range(bits.width)]
        self.result = CreateSignal(
            Bits(1),
            name='result',
            parent=self,
            frontend=False)

    def Declare(self):
        VDeclWire(self.result)

    def Synthesize(self):
        add_str = ' | '.join([VName(bit) for bit in self.bit_vec])
        VAssignRaw(VName(self.result), add_str)

@OpGen(default='result')
def BitOrReduce(bits):
    return BitOrReduceOperator(bits)

class ValidSetOperator(Operator):
    """Operator that manages a bit array for valid flags.

    N.B. Reads are not clocked (I.e. done combinationally).
    """

    def __init__(self, width : int, clock=None, reset=None):
        super().__init__('validset')
        self.width = width
        self.addrwidth = Log2Ceil(self.width)

        if clock is None:
            self.clock = DefaultClock()
        else:
            self.clock = clock

        if reset is None:
            self.reset = DefaultReset()
        else:
            self.reset = reset

        self.read_ports = []
        self.write_ports = []

    def Get(self, addr_signal):
        read_signal = CreateSignal(
            Bits(1),
            name=f'read_{len(self.read_ports)}',
            parent=self,
            frontend=False)

        self.read_ports.append((FilterFrontend(addr_signal), read_signal))
        return WrapSignal(read_signal)

    def __getitem__(self, key):
        return self.Get(key)

    def Set(self, addr_signal, data_signal, enable_signal):
        assert enable_signal.width == 1
        assert (type(data_signal) is bool) or \
            (type(data_signal) is int) or \
            (data_signal.width == 1)

        self.write_ports.append((
            FilterFrontend(addr_signal),
            FilterFrontend(data_signal),
            FilterFrontend(enable_signal)))

    def Declare(self):
        for (addr, data) in self.read_ports:
            VDeclWire(data)

    def Synthesize(self):
        set_name = self.name

        VEmitRaw(
            f'reg {set_name} [{self.width - 1} : 0];')

        for (addr, data) in self.read_ports:
            VAssignRaw(VName(data), f'{set_name}[{VName(addr)}]')

        with VAlways([VPosedge(self.clock)]):
            with VIf(self.reset):
                VConnectRaw(f'{set_name}', '\'{default:0};')
            with VElse():
                for (addr, data, enable) in self.write_ports:
                    with VIf(enable):
                        VConnectRaw(f'{set_name}[{VName(addr)}]', VName(data))

@OpGen(cacheable=False)
def ValidSet(width : int):
    return ValidSetOperator(width)

class ProbeOperator(Operator):
    """Operator that produces a verilog signal for probing.

    The resulting signal will be marked as verilator public
    """

    def __init__(self, bits, probe_name=None):
        super().__init__(override_name='probe')
        self.bits = FilterFrontend(bits)
        self.probe_name = probe_name
        self.probe = CreateSignal(
            bits.meta.typespec,
            name=None,
            parent=self,
            frontend=False)

    def Declare(self):
        if self.probe_name is not None:
            self.probe.meta.name = self.probe_name
        else:
            self.probe.meta.name = self.bits.meta.name

        width_str = \
            f'[{self.probe.width - 1} : 0]' if self.probe.width > 1 else ''

        VEmitRaw(
            f'wire {width_str} {VName(self.probe)} /* verilator public */;')

    def Synthesize(self):
        VAssign(self.probe, self.bits)

@OpGen(cacheable=False)
def Probe(bits, name=None):
    return ProbeOperator(bits, probe_name=name)