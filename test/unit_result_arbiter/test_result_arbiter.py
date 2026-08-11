"""
Cocotb unit test for result_arbiter.v
Verifies: single result passthrough, fixed-priority serialization when
2 or 3 contexts complete simultaneously, one-result-per-cycle serving,
result_valid pulse width, busy signal correctness.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles, ReadOnly, NextTimeStep

PASS, EARLY, TIMEOUT = 0, 1, 2


async def start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())


async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.result_valid_in0.value = 0
    dut.result_valid_in1.value = 0
    dut.result_valid_in2.value = 0
    dut.result_code_in0.value = 0
    dut.result_code_in1.value = 0
    dut.result_code_in2.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def fire(dut, ctx, code):
    """Pulse a single context's result_valid_in for exactly one cycle."""
    getattr(dut, f"result_valid_in{ctx}").value = 1
    getattr(dut, f"result_code_in{ctx}").value = code
    await RisingEdge(dut.clk)
    await ReadOnly()
    await NextTimeStep()
    getattr(dut, f"result_valid_in{ctx}").value = 0


async def fire_multi(dut, entries):
    """entries = list of (ctx, code) all asserted in the SAME cycle."""
    for ctx, code in entries:
        getattr(dut, f"result_valid_in{ctx}").value = 1
        getattr(dut, f"result_code_in{ctx}").value = code
    await RisingEdge(dut.clk)
    await ReadOnly()
    await NextTimeStep()
    for ctx, code in entries:
        getattr(dut, f"result_valid_in{ctx}").value = 0


@cocotb.test()
async def test_reset(dut):
    await start_clock(dut)
    await reset_dut(dut)
    assert dut.busy.value == 0
    assert dut.result_valid.value == 0


@cocotb.test()
async def test_single_passthrough(dut):
    await start_clock(dut)
    await reset_dut(dut)

    await fire(dut, 0, PASS)
    await RisingEdge(dut.clk)
    await ReadOnly()

    assert dut.result_valid.value == 1
    assert dut.result.value == PASS
    assert dut.context_id.value == 0


@cocotb.test()
async def test_two_way_priority(dut):
    """Ctx0 and Ctx1 complete same cycle -- Ctx0 must be served first."""
    await start_clock(dut)
    await reset_dut(dut)

    await fire_multi(dut, [(0, PASS), (1, TIMEOUT)])

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result_valid.value == 1
    assert dut.context_id.value == 0
    assert dut.result.value == PASS
    await NextTimeStep()

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result_valid.value == 1
    assert dut.context_id.value == 1
    assert dut.result.value == TIMEOUT


@cocotb.test()
async def test_three_way_priority(dut):
    await start_clock(dut)
    await reset_dut(dut)

    await fire_multi(dut, [(0, PASS), (1, EARLY), (2, TIMEOUT)])

    expected = [(0, PASS), (1, EARLY), (2, TIMEOUT)]
    for exp_ctx, exp_res in expected:
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert dut.result_valid.value == 1, f"expected ctx{exp_ctx} result_valid"
        assert dut.context_id.value == exp_ctx, f"expected ctx{exp_ctx}, got {int(dut.context_id.value)}"
        assert dut.result.value == exp_res
        await NextTimeStep()


@cocotb.test()
async def test_busy_reflects_pending(dut):
    await start_clock(dut)
    await reset_dut(dut)

    await fire_multi(dut, [(0, PASS), (2, TIMEOUT)])
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.busy.value == 1, "busy must be high while ctx2 still pending"
    await NextTimeStep()

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.busy.value == 0, "busy must clear once all pending results served"


@cocotb.test()
async def test_result_valid_pulse_width(dut):
    await start_clock(dut)
    await reset_dut(dut)

    await fire(dut, 1, EARLY)
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result_valid.value == 1
    await NextTimeStep()

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result_valid.value == 0, "result_valid must deassert after exactly 1 cycle"
