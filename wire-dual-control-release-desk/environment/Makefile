.PHONY: all clean

SOURCE := src/wire-terminal.cbl
SQL_INCLUDES := src/copybooks/transaction-begin \
	src/copybooks/request-identity \
	src/copybooks/dual-control-check \
	src/copybooks/twin-post \
	src/copybooks/freeze-gate
PRECOMPILED := build/wire-terminal.cob
TARGET := bin/wire-terminal

all: $(TARGET)

$(PRECOMPILED): $(SOURCE) $(SQL_INCLUDES) \
	src/copybooks/validation-rules.cpy
	mkdir -p build
	ocesql --inc=src/copybooks $(SOURCE) $(PRECOMPILED)

$(TARGET): $(PRECOMPILED)
	cobc -x -fixed -Wall -I src/copybooks -o $(TARGET) \
		$(PRECOMPILED) \
		-Q "-Wl,--no-as-needed" -locesql -lpq

clean:
	rm -f $(PRECOMPILED) $(TARGET)
