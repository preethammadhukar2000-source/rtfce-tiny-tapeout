"""
Cocotb unit test for monitor_ctx.v (baseline single-context temporal monitor)
Covers: reset, config read/write, PASS (mid/min/max boundary), EARLY,
TIMEOUT (incl. D8 wraparound regression), retrigger-ignore (D9),
disable-forces-idle, result_valid pulse width.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles, ReadOnly, NextTimeStep

# Event codes (spec section 3)
REQ, ACK, DATA, DONE = 0, 1, 2, 3

# Result codes (spec section 5)
PASS, EARLY, TIMEOUT = 0, 1, 2


async def start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())


async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.cfg_write.value = 0
    dut.cfg_byte_sel.value = 0
    dut.cfg_wdata.value = 0
    dut.event_strobe.value = 0
    dut.event_code.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def configure(dut, start_ev, end_ev, min_lat, max_lat, enable=1):
    """Write byte0 then byte1 to configure this context."""
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
    """Drive event_code + event_strobe for exactly one clock cycle."""
    dut.event_code.value = code
    dut.event_strobe.value = 1
    await RisingEdge(dut.clk)
    await ReadOnly()
    await NextTimeStep()
    dut.event_strobe.value = 0
    dut.event_code.value = 0


async def wait_for_result_valid(dut, max_cycles=40):
    """Step clock-by-clock until result_valid pulses high, or fail after max_cycles."""
    for _ in range(max_cycles):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if dut.result_valid.value == 1:
            return
        await NextTimeStep()
    raise AssertionError(f"result_valid never asserted within {max_cycles} cycles")


@cocotb.test()
async def test_reset(dut):
    await start_clock(dut)
    await reset_dut(dut)
    assert dut.busy.value == 0
    assert dut.result_valid.value == 0


@cocotb.test()
async def test_config_write_readback(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure(dut, start_ev=REQ, end_ev=DONE, min_lat=3, max_lat=10, enable=1)

    dut.cfg_byte_sel.value = 0
    await RisingEdge(dut.clk)
    expected_byte0 = (REQ << 6) | (DONE << 4) | 3
    assert dut.cfg_rdata.value == expected_byte0, \
        f"byte0 mismatch: got {dut.cfg_rdata.value}, expected {expected_byte0}"

    dut.cfg_byte_sel.value = 1
    await RisingEdge(dut.clk)
    expected_byte1 = (1 << 7) | 10
    assert dut.cfg_rdata.value == expected_byte1, \
        f"byte1 mismatch: got {dut.cfg_rdata.value}, expected {expected_byte1}"


@cocotb.test()
async def test_pass_mid(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure(dut, start_ev=REQ, end_ev=DONE, min_lat=3, max_lat=10, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 5)
    await pulse_event(dut, DONE)

    assert dut.result_valid.value == 1
    assert dut.result.value == PASS


@cocotb.test()
async def test_pass_boundary_min(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure(dut, start_ev=REQ, end_ev=DONE, min_lat=3, max_lat=10, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 3)
    await pulse_event(dut, DONE)

    assert dut.result_valid.value == 1
    assert dut.result.value == PASS, "latency == min_latency must be PASS, not EARLY"


@cocotb.test()
async def test_pass_boundary_max(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure(dut, start_ev=REQ, end_ev=DONE, min_lat=3, max_lat=10, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 10)
    await pulse_event(dut, DONE)

    assert dut.result_valid.value == 1
    assert dut.result.value == PASS, "latency == max_latency must be PASS, not TIMEOUT (end event wins)"


@cocotb.test()
async def test_early(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure(dut, start_ev=REQ, end_ev=DONE, min_lat=5, max_lat=10, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 2)
    await pulse_event(dut, DONE)

    assert dut.result_valid.value == 1
    assert dut.result.value == EARLY


@cocotb.test()
async def test_timeout_max15_regression(dut):
    """Regression test for the D8 wraparound bug: max_latency=15 must not
    let the 4-bit-equivalent timer wrap before TIMEOUT is declared."""
    await start_clock(dut)
    await reset_dut(dut)
    await configure(dut, start_ev=REQ, end_ev=DONE, min_lat=0, max_lat=15, enable=1)

    await pulse_event(dut, REQ)
    await wait_for_result_valid(dut, max_cycles=40)

    assert dut.result.value == TIMEOUT, \
        "TIMEOUT did not fire correctly with max_latency=15 (D8 wraparound check)"


@cocotb.test()
async def test_retrigger_ignored_while_armed(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure(dut, start_ev=REQ, end_ev=DONE, min_lat=3, max_lat=15, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 2)
    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 3)
    await pulse_event(dut, DONE)

    assert dut.result_valid.value == 1
    assert dut.result.value == PASS, "retrigger must not reset the timer"


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


@cocotb.test()
async def test_result_valid_pulse_width(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure(dut, start_ev=REQ, end_ev=DONE, min_lat=3, max_lat=10, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 5)
    await pulse_event(dut, DONE)

    assert dut.result_valid.value == 1
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result_valid.value == 0, "result_valid must deassert after exactly 1 cycle"
