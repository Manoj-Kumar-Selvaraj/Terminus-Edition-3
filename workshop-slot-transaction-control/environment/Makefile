.PHONY: all clean

SOURCE := src/workshop-terminal.cbl
POLICY_SOURCE := src/modules/workshop-policy-engine.cbl
SQL_INCLUDES := src/copybooks/transaction-begin \
	src/copybooks/request-identity \
	src/copybooks/resource-lock \
	src/copybooks/overlap-check \
	src/copybooks/move-transaction
PRECOMPILED := build/workshop-terminal.cob
TARGET := bin/workshop-terminal

all: $(TARGET)

$(PRECOMPILED): $(SOURCE) $(SQL_INCLUDES) \
	src/copybooks/validation-rules.cpy
	mkdir -p build
	ocesql --inc=src/copybooks $(SOURCE) $(PRECOMPILED)

$(TARGET): $(PRECOMPILED) $(POLICY_SOURCE)
	cobc -x -fixed -Wall -I src/copybooks -o $(TARGET) \
		$(PRECOMPILED) $(POLICY_SOURCE) \
		-Q "-Wl,--no-as-needed" -locesql -lpq

clean:
	rm -f $(PRECOMPILED) $(TARGET)
