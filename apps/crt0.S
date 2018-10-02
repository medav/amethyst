
.section .text.init, "ax", @progbits
.globl _init
_init:
    li    sp, 0x00002000
    j main
loop:
    j loop
