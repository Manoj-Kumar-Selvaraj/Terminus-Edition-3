# Build the native freight ledger engine.
#
#   make            -> build/libfreight.a and build/freightctl
#   make clean      -> remove build artifacts

CXX      ?= g++
CXXFLAGS ?= -std=c++17 -O0 -Iinclude
AR       ?= ar

SRCS := $(shell find src -name '*.cpp' -not -path 'src/cli/*' | LC_ALL=C sort)
OBJS := $(patsubst src/%.cpp,build/obj/%.o,$(SRCS))
CLI_SRCS := $(shell find src/cli -name '*.cpp' | LC_ALL=C sort)
CLI_OBJS := $(patsubst src/%.cpp,build/obj/%.o,$(CLI_SRCS))

all: build/freightctl

build/libfreight.a: $(OBJS)
	@mkdir -p $(dir $@)
	$(AR) rcs $@ $(OBJS)

build/freightctl: $(CLI_OBJS) build/libfreight.a
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -o $@ $(CLI_OBJS) build/libfreight.a

build/obj/%.o: src/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -c -o $@ $<

clean:
	rm -rf build

.PHONY: all clean
