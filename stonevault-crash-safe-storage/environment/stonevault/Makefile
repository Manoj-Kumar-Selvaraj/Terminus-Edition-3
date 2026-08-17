.PHONY: all clean

all:
	cargo build --release
	mkdir -p bin
	cp target/release/stonevault bin/stonevault

clean:
	cargo clean
	rm -f bin/stonevault
