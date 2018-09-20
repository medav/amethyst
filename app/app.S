
.section .text.init, "ax", @progbits
.globl _init
_init:
    li s0, 0
loop:
    li s1, 1
    add s0, s0, s1
    j loop
    li s0, 4
    li s1, 5
