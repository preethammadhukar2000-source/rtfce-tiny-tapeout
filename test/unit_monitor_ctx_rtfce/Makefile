SIM ?= icarus
TOPLEVEL_LANG ?= verilog

SRC_DIR = $(PWD)/../../src

VERILOG_SOURCES = $(SRC_DIR)/monitor_ctx_rtfce.v

TOPLEVEL = monitor_ctx_rtfce

COCOTB_TEST_MODULES = test_monitor_ctx_rtfce

include $(shell cocotb-config --makefiles)/Makefile.sim
