# Standalone cocotb unit test for monitor_ctx.v
# (Separate from the Tiny Tapeout top-level test in ../ -- do not merge)

SIM ?= icarus
TOPLEVEL_LANG ?= verilog

SRC_DIR = $(PWD)/../../src

VERILOG_SOURCES = $(SRC_DIR)/monitor_ctx.v

TOPLEVEL = monitor_ctx

COCOTB_TEST_MODULES = test_monitor_ctx

include $(shell cocotb-config --makefiles)/Makefile.sim
