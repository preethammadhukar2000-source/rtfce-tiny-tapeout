"""
Cocotb unit test for monitor_ctx_heavy.v (D13).
Same core coverage as monitor_ctx.v, plus near_miss propagation.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles, ReadOnly, NextTimeStep

REQ, ACK, DATA, DONE = 0, 1, 2, 3
PASS, EARLY, TIMEOUT = 0, 1, 2


async def start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())


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


async def wait_for_result_valid(dut, max_cycles=40):
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
async def test_pass_mid_no_near_miss(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure(dut, start_ev=REQ, end_ev=DONE, min_lat=0, max_lat=15, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 7)
    await pulse_event(dut, DONE)

    assert dut.result_valid.value == 1
    assert dut.result.value == PASS
    assert dut.near_miss.value == 0, "latency=7 well clear of max=15, not a near miss"


@cocotb.test()
async def test_pass_near_timeout(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure(dut, start_ev=REQ, end_ev=DONE, min_lat=0, max_lat=10, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 9)
    await pulse_event(dut, DONE)

    assert dut.result_valid.value == 1
    assert dut.result.value == PASS
    assert dut.near_miss.value == 1, "latency=9 within margin of max=10"


@cocotb.test()
async def test_timeout_near_miss(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure(dut, start_ev=REQ, end_ev=DONE, min_lat=0, max_lat=10, enable=1)

    await pulse_event(dut, REQ)
    await wait_for_result_valid(dut, max_cycles=40)

    assert dut.result.value == TIMEOUT
    assert dut.near_miss.value == 1, "latency=12 (max=10, margin=2) is a near-miss timeout"


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
async def test_boundary_max_still_pass(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure(dut, start_ev=REQ, end_ev=DONE, min_lat=0, max_lat=10, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 10)
    await pulse_event(dut, DONE)

    assert dut.result_valid.value == 1
    assert dut.result.value == PASS, "latency==max must still be PASS (D8/D13 unchanged)"
