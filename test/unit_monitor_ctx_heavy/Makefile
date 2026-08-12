SIM ?= icarus
TOPLEVEL_LANG ?= verilog

SRC_DIR = $(PWD)/../../src

VERILOG_SOURCES = $(SRC_DIR)/shared_classifier_heavy.v $(SRC_DIR)/monitor_ctx_heavy.v

TOPLEVEL = monitor_ctx_heavy

COCOTB_TEST_MODULES = test_monitor_ctx_heavy

include $(shell cocotb-config --makefiles)/Makefile.sim
