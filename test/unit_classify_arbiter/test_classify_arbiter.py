"""
Cocotb unit test for classify_arbiter.v (v2 -- adds round-robin, D12).
Existing fixed-priority tests unchanged in behavior (rr_enable=0).
New tests cover round-robin fairness and mode switching.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles, ReadOnly, NextTimeStep

PASS, EARLY, TIMEOUT = 0, 1, 2


async def start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())


async def reset_dut(dut, rr_enable=0):
    dut.rst_n.value = 0
    dut.rr_enable.value = rr_enable
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
async def test_fixed_priority_unchanged(dut):
    """rr_enable=0 must behave EXACTLY as v1.1 -- regression check."""
    await start_clock(dut)
    await reset_dut(dut, rr_enable=0)

    dut.pend0.value = 1
    dut.latency0.value = 5
    dut.min0.value = 3
    dut.max0.value = 10

    dut.pend1.value = 1
    dut.latency1.value = 20
    dut.min1.value = 0
    dut.max1.value = 15

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.context_id.value == 0, "fixed priority must still serve ctx0 first"
    await NextTimeStep()
    dut.pend0.value = 0

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.context_id.value == 1
    await NextTimeStep()
    dut.pend1.value = 0


@cocotb.test()
async def test_three_way_contention(dut):
    await start_clock(dut)
    await reset_dut(dut, rr_enable=0)

    dut.pend0.value = 1
    dut.latency0.value = 5
    dut.min0.value = 3
    dut.max0.value = 10

    dut.pend1.value = 1
    dut.latency1.value = 1
    dut.min1.value = 5
    dut.max1.value = 10

    dut.pend2.value = 1
    dut.latency2.value = 12
    dut.min2.value = 0
    dut.max2.value = 10

    expected = [(0, PASS), (1, EARLY), (2, TIMEOUT)]
    pend_signals = [dut.pend0, dut.pend1, dut.pend2]

    for exp_ctx, exp_result in expected:
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert dut.context_id.value == exp_ctx
        assert dut.result.value == exp_result
        await NextTimeStep()
        pend_signals[exp_ctx].value = 0


@cocotb.test()
async def test_busy_reflects_pending(dut):
    await start_clock(dut)
    await reset_dut(dut, rr_enable=0)

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
    assert dut.busy.value == 1
    await NextTimeStep()
    dut.pend0.value = 0

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.busy.value == 1
    await NextTimeStep()
    dut.pend2.value = 0

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.busy.value == 0


@cocotb.test()
async def test_grant_pulse_width(dut):
    await start_clock(dut)
    await reset_dut(dut, rr_enable=0)

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
    assert dut.grant0.value == 0


@cocotb.test()
async def test_round_robin_rotates_fairly(dut):
    """With rr_enable=1 and all 3 contexts persistently pending, the
    arbiter must cycle through them in rotation (0,1,2,0,1,2,...)
    rather than always favoring ctx0 like fixed priority would."""
    await start_clock(dut)
    await reset_dut(dut, rr_enable=1)

    # All 3 persistently pending (re-assert every cycle to simulate
    # constant contention -- like 3 always-busy monitoring contexts)
    dut.pend0.value = 1
    dut.pend1.value = 1
    dut.pend2.value = 1
    dut.latency0.value = 5
    dut.min0.value = 3
    dut.max0.value = 10
    dut.latency1.value = 5
    dut.min1.value = 3
    dut.max1.value = 10
    dut.latency2.value = 5
    dut.min2.value = 3
    dut.max2.value = 10

    served_order = []
    for _ in range(6):
        await RisingEdge(dut.clk)
        await ReadOnly()
        served_order.append(int(dut.context_id.value))
        await NextTimeStep()

    assert served_order == [0, 1, 2, 0, 1, 2], \
        f"round-robin must rotate fairly, got {served_order}"


@cocotb.test()
async def test_round_robin_skips_idle_contexts(dut):
    """If ctx1 is never pending, round-robin must skip it and keep
    rotating between ctx0 and ctx2 -- not stall waiting for ctx1."""
    await start_clock(dut)
    await reset_dut(dut, rr_enable=1)

    dut.pend0.value = 1
    dut.pend2.value = 1
    dut.latency0.value = 5
    dut.min0.value = 3
    dut.max0.value = 10
    dut.latency2.value = 5
    dut.min2.value = 3
    dut.max2.value = 10

    served_order = []
    for _ in range(4):
        await RisingEdge(dut.clk)
        await ReadOnly()
        served_order.append(int(dut.context_id.value))
        await NextTimeStep()

    assert served_order == [0, 2, 0, 2], \
        f"round-robin must skip never-pending ctx1, got {served_order}"


@cocotb.test()
async def test_mode_switch_takes_effect(dut):
    """Switching rr_enable mid-operation must change behavior on the
    next arbitration decision (policy is purely combinational on
    sel_ctx, so this should take effect immediately)."""
    await start_clock(dut)
    await reset_dut(dut, rr_enable=0)

    dut.pend0.value = 1
    dut.pend1.value = 1
    dut.latency0.value = 5
    dut.min0.value = 3
    dut.max0.value = 10
    dut.latency1.value = 5
    dut.min1.value = 3
    dut.max1.value = 10

    # Fixed priority: ctx0 served first
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.context_id.value == 0
    await NextTimeStep()

    # Switch to round-robin -- last_served is now 0, so next pick skips to ctx1
    dut.rr_enable.value = 1
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.context_id.value == 1, "after switching to RR, must serve ctx1 next"
