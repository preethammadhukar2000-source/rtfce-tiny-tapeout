SIM ?= icarus
TOPLEVEL_LANG ?= verilog

SRC_DIR = $(PWD)/../../src

VERILOG_SOURCES = $(SRC_DIR)/shared_classifier.v

TOPLEVEL = shared_classifier

COCOTB_TEST_MODULES = test_shared_classifier

include $(shell cocotb-config --makefiles)/Makefile.sim
