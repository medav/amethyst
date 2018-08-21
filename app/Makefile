CC=riscv64-unknown-elf-gcc
OBJCOPY=riscv64-unknown-elf-objcopy

all: app.img

%.img: %.bin
	dd if=$< of=$@ bs=128 count=1

%.bin: %.elf
	$(OBJCOPY) -O binary $< $@

%.elf: %.S link.ld
	$(CC) -Tlink.ld $< -mabi=lp64 -march=rv64i -nostdlib -static -Wl,--no-gc-sections -o $@

clean:
	rm -f app.bin app.img app.elf