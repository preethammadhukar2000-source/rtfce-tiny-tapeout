# Standalone cocotb unit test for result_arbiter.v
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

SRC_DIR = $(PWD)/../../src

VERILOG_SOURCES = $(SRC_DIR)/result_arbiter.v

TOPLEVEL = result_arbiter

COCOTB_TEST_MODULES = test_result_arbiter

include $(shell cocotb-config --makefiles)/Makefile.sim
