
.section .text.init, "ax", @progbits
.globl _init
_init:
    li s0, 2
    li s1, 1
    add s0, s0, s1

