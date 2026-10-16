CXX := /opt/homebrew/opt/llvm/bin/clang++
CXXFLAGS := -std=c++17 -O3 -Wall -Wextra -Wpedantic -ffp-contract=off
.PHONY: all
all: bin/serial bin/paralelo1 bin/paralelo2
bin:
	mkdir -p bin
bin/serial: src/serial.cpp src/dbscan_common.hpp | bin
	$(CXX) $(CXXFLAGS) $< -o $@
bin/paralelo%: src/paralelo%.cpp src/dbscan_common.hpp | bin
	$(CXX) $(CXXFLAGS) -fopenmp $< -o $@
