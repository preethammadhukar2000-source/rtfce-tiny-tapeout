SIM ?= icarus
TOPLEVEL_LANG ?= verilog

SRC_DIR = $(PWD)/../../src

VERILOG_SOURCES = $(SRC_DIR)/rtfce_top_v2_heavy.v $(SRC_DIR)/monitor_ctx_rtfce.v $(SRC_DIR)/classify_arbiter_heavy.v $(SRC_DIR)/shared_classifier_heavy.v $(SRC_DIR)/result_arbiter_heavy.v
VERILOG_SOURCES += $(PWD)/tb_v2_heavy.v

TOPLEVEL = tb_v2_heavy

COCOTB_TEST_MODULES = test_rtfce_v2_heavy_top

include $(shell cocotb-config --makefiles)/Makefile.sim
