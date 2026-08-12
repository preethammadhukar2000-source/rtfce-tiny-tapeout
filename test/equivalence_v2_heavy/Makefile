SIM ?= icarus
TOPLEVEL_LANG ?= verilog

SRC_DIR = $(PWD)/../../src

VERILOG_SOURCES = $(SRC_DIR)/project_v2.v $(SRC_DIR)/monitor_ctx_heavy.v $(SRC_DIR)/result_arbiter_heavy.v
VERILOG_SOURCES += $(SRC_DIR)/rtfce_top_v2_heavy.v $(SRC_DIR)/monitor_ctx_rtfce.v $(SRC_DIR)/classify_arbiter_heavy.v
VERILOG_SOURCES += $(SRC_DIR)/shared_classifier_heavy.v
VERILOG_SOURCES += $(PWD)/tb_equiv_v2.v

TOPLEVEL = tb_equiv_v2

COCOTB_TEST_MODULES = test_equivalence_v2

include $(shell cocotb-config --makefiles)/Makefile.sim
