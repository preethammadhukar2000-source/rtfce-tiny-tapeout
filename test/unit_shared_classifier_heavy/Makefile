SIM ?= icarus
TOPLEVEL_LANG ?= verilog

SRC_DIR = $(PWD)/../../src

VERILOG_SOURCES = $(SRC_DIR)/shared_classifier_heavy.v

TOPLEVEL = shared_classifier_heavy

COCOTB_TEST_MODULES = test_shared_classifier_heavy

include $(shell cocotb-config --makefiles)/Makefile.sim
