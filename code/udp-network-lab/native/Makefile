CLANG ?= /opt/homebrew/opt/llvm/bin/clang
SSL   ?= /opt/homebrew/opt/openssl@3
CFLAGS = -I$(SSL)/include -Wall -Wextra -O1 -g
LDFLAGS = -L$(SSL)/lib -lcrypto

all: fuzz_decode sf_selftest

fuzz_decode: fuzz_decode.c secure_framing.c secure_framing.h
	$(CLANG) -fsanitize=fuzzer,address $(CFLAGS) fuzz_decode.c secure_framing.c -o $@ $(LDFLAGS)

sf_selftest: sf_selftest.c secure_framing.c secure_framing.h
	$(CLANG) -fsanitize=address $(CFLAGS) sf_selftest.c secure_framing.c -o $@ $(LDFLAGS)

clean:
	rm -f fuzz_decode sf_selftest vectors.txt
