SIM ?= icarus
TOPLEVEL_LANG ?= verilog

SRC_DIR = $(PWD)/../../src

VERILOG_SOURCES = $(SRC_DIR)/rtfce_top.v $(SRC_DIR)/monitor_ctx_rtfce.v $(SRC_DIR)/classify_arbiter.v $(SRC_DIR)/shared_classifier.v $(SRC_DIR)/result_arbiter.v
VERILOG_SOURCES += $(PWD)/tb_rtfce.v

TOPLEVEL = tb_rtfce

COCOTB_TEST_MODULES = test_rtfce_top

include $(shell cocotb-config --makefiles)/Makefile.sim
