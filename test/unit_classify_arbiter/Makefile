SIM ?= icarus
TOPLEVEL_LANG ?= verilog

SRC_DIR = $(PWD)/../../src

VERILOG_SOURCES = $(SRC_DIR)/shared_classifier.v $(SRC_DIR)/classify_arbiter.v

TOPLEVEL = classify_arbiter

COCOTB_TEST_MODULES = test_classify_arbiter

include $(shell cocotb-config --makefiles)/Makefile.sim
