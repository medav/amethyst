
class ITypes(object):
    R = 0
    I = 1
    S = 2
    B = 3
    U = 4
    J = 5

    itype_width = 3

class AluSrc(object):
    """Possible sources for the second operand on the ALU

    N.B. The values here are used to set the mux into the ALU. Also, the 'none'
    value means that the second operand is unused. It doesn't matter what value
    its set to, as long as its a legal mux index (Hence why it's the same as
    rs1).
    """

    none = 0
    rs2 = 0
    imm = 1
