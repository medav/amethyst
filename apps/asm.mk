CC=riscv64-unknown-elf-gcc
OBJCOPY=riscv64-unknown-elf-objcopy

all: $(APP).img

%.img: %.bin
	dd if=$< of=$@ bs=1024 count=1

%.bin: %.elf
	$(OBJCOPY) -O binary $< $@

%.elf: %.S ../link.ld
	$(CC) -T../link.ld $< -mabi=lp64 -march=rv64i -nostdlib -static -Wl,--no-gc-sections -o $@

clean:
	rm -f *.bin *.img *.elf