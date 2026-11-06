# Builds libaxidma.so, the C++ DMA driver that loopback_cpp.py calls.
# Run on the Kria: `make`

CXX      ?= g++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra

libaxidma.so: dma_lib.cpp axi_dma.hpp
	$(CXX) $(CXXFLAGS) -shared -fPIC -o $@ dma_lib.cpp

clean:
	rm -f libaxidma.so

.PHONY: clean
