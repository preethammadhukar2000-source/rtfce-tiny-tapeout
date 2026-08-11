"""
Cocotb unit test for classify_arbiter.v
Verifies: single-context classification, fixed-priority arbitration
under 2-way/3-way contention, and -- critically -- that arbitration
delay never changes the reported latency (spec section 11).
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles, ReadOnly, NextTimeStep

PASS, EARLY, TIMEOUT = 0, 1, 2


async def start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())


async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.pend0.value = 0
    dut.pend1.value = 0
    dut.pend2.value = 0
    dut.latency0.value = 0
    dut.latency1.value = 0
    dut.latency2.value = 0
    dut.min0.value = 0
    dut.min1.value = 0
    dut.min2.value = 0
    dut.max0.value = 0
    dut.max1.value = 0
    dut.max2.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_reset(dut):
    await start_clock(dut)
    await reset_dut(dut)
    assert dut.busy.value == 0
    assert dut.result_valid.value == 0


@cocotb.test()
async def test_single_context_pass(dut):
    await start_clock(dut)
    await reset_dut(dut)

    dut.pend0.value = 1
    dut.latency0.value = 5
    dut.min0.value = 3
    dut.max0.value = 10

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result_valid.value == 1
    assert dut.context_id.value == 0
    assert dut.result.value == PASS
    assert dut.grant0.value == 1
    await NextTimeStep()
    dut.pend0.value = 0


@cocotb.test()
async def test_two_way_priority_latency_unmodified(dut):
    """Ctx0 and Ctx1 both pending simultaneously with DIFFERENT
    latencies -- Ctx0 served first, Ctx1 served next cycle, and
    critically Ctx1's reported latency must be its own captured
    value, completely unaffected by having to wait one cycle."""
    await start_clock(dut)
    await reset_dut(dut)

    dut.pend0.value = 1
    dut.latency0.value = 5
    dut.min0.value = 3
    dut.max0.value = 10

    dut.pend1.value = 1
    dut.latency1.value = 20   # deliberately > max1 -> should classify TIMEOUT
    dut.min1.value = 0
    dut.max1.value = 15

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.context_id.value == 0
    assert dut.result.value == PASS
    assert dut.grant0.value == 1
    assert dut.grant1.value == 0
    await NextTimeStep()
    dut.pend0.value = 0   # ctx0 done, drops pend

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.context_id.value == 1
    assert dut.result.value == TIMEOUT, \
        "ctx1's latency=20 vs max=15 must still classify TIMEOUT after the 1-cycle wait"
    assert dut.grant1.value == 1
    await NextTimeStep()
    dut.pend1.value = 0


@cocotb.test()
async def test_three_way_contention(dut):
    await start_clock(dut)
    await reset_dut(dut)

    dut.pend0.value = 1
    dut.latency0.value = 5
    dut.min0.value = 3
    dut.max0.value = 10   # PASS

    dut.pend1.value = 1
    dut.latency1.value = 1
    dut.min1.value = 5
    dut.max1.value = 10   # EARLY

    dut.pend2.value = 1
    dut.latency2.value = 12
    dut.min2.value = 0
    dut.max2.value = 10   # TIMEOUT

    expected = [(0, PASS), (1, EARLY), (2, TIMEOUT)]
    pend_signals = [dut.pend0, dut.pend1, dut.pend2]

    for exp_ctx, exp_result in expected:
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert dut.context_id.value == exp_ctx, \
            f"expected ctx{exp_ctx}, got {int(dut.context_id.value)}"
        assert dut.result.value == exp_result
        await NextTimeStep()
        pend_signals[exp_ctx].value = 0


@cocotb.test()
async def test_busy_reflects_pending(dut):
    await start_clock(dut)
    await reset_dut(dut)

    dut.pend0.value = 1
    dut.latency0.value = 5
    dut.min0.value = 3
    dut.max0.value = 10

    dut.pend2.value = 1
    dut.latency2.value = 1
    dut.min2.value = 0
    dut.max2.value = 10

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.busy.value == 1, "busy must be high while ctx2 still pending"
    await NextTimeStep()
    dut.pend0.value = 0

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.busy.value == 1, "still busy -- ctx2 being served this cycle"
    await NextTimeStep()
    dut.pend2.value = 0

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.busy.value == 0, "busy must clear once nothing pending"


@cocotb.test()
async def test_grant_pulse_width(dut):
    await start_clock(dut)
    await reset_dut(dut)

    dut.pend0.value = 1
    dut.latency0.value = 5
    dut.min0.value = 3
    dut.max0.value = 10

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.grant0.value == 1
    await NextTimeStep()
    dut.pend0.value = 0

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.grant0.value == 0, "grant0 must deassert after exactly 1 cycle"
