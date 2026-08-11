"""
Cocotb unit test for monitor_ctx_rtfce.v
Same functional coverage as baseline monitor_ctx.v, but here the
module itself does NOT classify -- we verify it correctly requests
service (pend=1) and correctly returns to IDLE on grant, with
latched_latency held stable throughout DONE_PENDING regardless of
how many cycles the (here, manually driven) grant is delayed.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles, ReadOnly, NextTimeStep

REQ, ACK, DATA, DONE = 0, 1, 2, 3


async def start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())


async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.cfg_write.value = 0
    dut.cfg_byte_sel.value = 0
    dut.cfg_wdata.value = 0
    dut.event_strobe.value = 0
    dut.event_code.value = 0
    dut.grant.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def configure(dut, start_ev, end_ev, min_lat, max_lat, enable=1):
    byte0 = (start_ev << 6) | (end_ev << 4) | (min_lat & 0xF)
    byte1 = (enable << 7) | (max_lat & 0xF)

    dut.cfg_byte_sel.value = 0
    dut.cfg_wdata.value = byte0
    dut.cfg_write.value = 1
    await RisingEdge(dut.clk)
    dut.cfg_write.value = 0
    await RisingEdge(dut.clk)

    dut.cfg_byte_sel.value = 1
    dut.cfg_wdata.value = byte1
    dut.cfg_write.value = 1
    await RisingEdge(dut.clk)
    dut.cfg_write.value = 0
    await RisingEdge(dut.clk)


async def pulse_event(dut, code):
    dut.event_code.value = code
    dut.event_strobe.value = 1
    await RisingEdge(dut.clk)
    await ReadOnly()
    await NextTimeStep()
    dut.event_strobe.value = 0
    dut.event_code.value = 0


async def pulse_grant(dut):
    dut.grant.value = 1
    await RisingEdge(dut.clk)
    await ReadOnly()
    await NextTimeStep()
    dut.grant.value = 0


@cocotb.test()
async def test_reset(dut):
    await start_clock(dut)
    await reset_dut(dut)
    assert dut.busy.value == 0
    assert dut.pend.value == 0


@cocotb.test()
async def test_reaches_done_pending_and_holds_latency(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure(dut, start_ev=REQ, end_ev=DONE, min_lat=3, max_lat=10, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 5)
    await pulse_event(dut, DONE)

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.pend.value == 1, "must request classification (pend=1) after end event"
    assert dut.latched_latency_out.value == 5

    # Simulate arbitration delay -- wait several extra cycles before granting
    await NextTimeStep()
    for _ in range(4):
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert dut.pend.value == 1, "must remain pending until granted"
        assert dut.latched_latency_out.value == 5, \
            "latched_latency must NOT change while waiting for grant (spec section 11)"
        await NextTimeStep()

    await pulse_grant(dut)
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.pend.value == 0, "pend must clear after grant"
    assert dut.busy.value == 0, "must return to IDLE after grant"


@cocotb.test()
async def test_timeout_reaches_done_pending(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure(dut, start_ev=REQ, end_ev=DONE, min_lat=0, max_lat=15, enable=1)

    await pulse_event(dut, REQ)

    # Let it run past max_latency with no end event
    for _ in range(20):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if dut.pend.value == 1:
            break
        await NextTimeStep()

    assert dut.pend.value == 1, "must reach DONE_PENDING via timeout"
    assert int(dut.latched_latency_out.value) > 15, \
        "timed-out latency must exceed max_latency for classifier to see TIMEOUT"


@cocotb.test()
async def test_retrigger_ignored_while_armed(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure(dut, start_ev=REQ, end_ev=DONE, min_lat=3, max_lat=15, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 2)
    await pulse_event(dut, REQ)   # retrigger while ARMED -- must be ignored
    await ClockCycles(dut.clk, 3)
    await pulse_event(dut, DONE)

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.latched_latency_out.value == 6, \
        "retrigger must not reset the timer (total latency from FIRST start = 6)"


@cocotb.test()
async def test_start_ignored_while_done_pending(dut):
    """A start_event arriving while DONE_PENDING (not just ARMED) must
    also be ignored -- this is the generalization from D9."""
    await start_clock(dut)
    await reset_dut(dut)
    await configure(dut, start_ev=REQ, end_ev=DONE, min_lat=3, max_lat=10, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 5)
    await pulse_event(dut, DONE)

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.pend.value == 1
    await NextTimeStep()

    # Try to retrigger while sitting in DONE_PENDING
    await pulse_event(dut, REQ)
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.pend.value == 1, "must still be pending -- start event while DONE_PENDING ignored"
    assert dut.latched_latency_out.value == 5, "latency must remain unchanged"


@cocotb.test()
async def test_disable_forces_idle(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure(dut, start_ev=REQ, end_ev=DONE, min_lat=3, max_lat=15, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 2)
    assert dut.busy.value == 1

    await configure(dut, start_ev=REQ, end_ev=DONE, min_lat=3, max_lat=15, enable=0)
    await ClockCycles(dut.clk, 2)
    assert dut.busy.value == 0, "disabling mid-measurement must force context back to idle"
