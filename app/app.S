
.section .text.init, "ax", @progbits
.globl _init
_init:
    li s0, 0
    j _init
