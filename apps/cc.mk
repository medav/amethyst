CC=riscv64-unknown-elf-gcc
OBJCOPY=riscv64-unknown-elf-objcopy

all: $(APP).img

%.img: %.bin
	dd if=$< of=$@ bs=1024 count=1
	dd if=/dev/zero bs=1 count=65536 >> $@

$(APP).bin: $(APP).elf
	$(OBJCOPY) -O binary $< $@

$(APP).elf: $(APP).c ../link.ld
	$(CC) -T../link.ld ../crt0.S $< -march=rv64g -nostdlib -static -Wl,--no-gc-sections -o $@

clean:
	rm -f *.bin *.img *.elf