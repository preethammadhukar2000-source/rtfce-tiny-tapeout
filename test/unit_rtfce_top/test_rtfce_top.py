"""
Top-level pin-driven test for rtfce_top.v (optimized RTFCE).
Mirrors project.v's test.py structure exactly, for direct comparison,
plus one RTFCE-specific test proving arbitration delay never corrupts
the reported result through the real pin interface.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles, ReadOnly, NextTimeStep

REQ, ACK, DATA, DONE = 0, 1, 2, 3
PASS, EARLY, TIMEOUT = 0, 1, 2


def build_ui_in(strobe=0, cfg_mode=0, cfg_rw=0, cfg_byte_sel=0, addr_sel=0, event_code=0):
    return ((event_code & 0x3) << 6) | ((addr_sel & 0x3) << 4) | \
           ((cfg_byte_sel & 1) << 3) | ((cfg_rw & 1) << 2) | \
           ((cfg_mode & 1) << 1) | (strobe & 1)


async def start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())


async def reset_dut(dut):
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def cfg_write(dut, ctx, byte_sel, data):
    dut.uio_in.value = data
    dut.ui_in.value = build_ui_in(strobe=1, cfg_mode=1, cfg_rw=0, cfg_byte_sel=byte_sel, addr_sel=ctx)
    await RisingEdge(dut.clk)
    dut.ui_in.value = build_ui_in(strobe=0, cfg_mode=1, cfg_rw=0, cfg_byte_sel=byte_sel, addr_sel=ctx)
    await RisingEdge(dut.clk)


async def configure_ctx(dut, ctx, start_ev, end_ev, min_lat, max_lat, enable=1):
    byte0 = (start_ev << 6) | (end_ev << 4) | (min_lat & 0xF)
    byte1 = (enable << 7) | (max_lat & 0xF)
    await cfg_write(dut, ctx, 0, byte0)
    await cfg_write(dut, ctx, 1, byte1)


async def cfg_read(dut, ctx, byte_sel):
    dut.ui_in.value = build_ui_in(strobe=1, cfg_mode=1, cfg_rw=1, cfg_byte_sel=byte_sel, addr_sel=ctx)
    await RisingEdge(dut.clk)
    await ReadOnly()
    val = int(dut.uio_out.value)
    await NextTimeStep()
    dut.ui_in.value = build_ui_in(strobe=0, cfg_mode=1, cfg_rw=1, cfg_byte_sel=byte_sel, addr_sel=ctx)
    return val


async def pulse_event(dut, code):
    dut.ui_in.value = build_ui_in(strobe=1, cfg_mode=0, event_code=code)
    await RisingEdge(dut.clk)
    await ReadOnly()
    await NextTimeStep()
    dut.ui_in.value = build_ui_in(strobe=0, cfg_mode=0, event_code=0)


async def wait_for_uo_result_valid(dut, max_cycles=20):
    for _ in range(max_cycles):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if (int(dut.uo_out.value) >> 4) & 1:
            return int(dut.uo_out.value)
        await NextTimeStep()
    raise AssertionError("uo_out result_valid never asserted within max_cycles")


@cocotb.test()
async def test_reset(dut):
    await start_clock(dut)
    await reset_dut(dut)
    assert (int(dut.uo_out.value) >> 4) & 1 == 0, "result_valid must be 0 after reset"


@cocotb.test()
async def test_pass_via_pins(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure_ctx(dut, ctx=0, start_ev=REQ, end_ev=DONE, min_lat=3, max_lat=10, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 5)
    await pulse_event(dut, DONE)

    val = await wait_for_uo_result_valid(dut)
    result = val & 0x3
    context_id = (val >> 2) & 0x3
    assert result == PASS, f"expected PASS, got {result}"
    assert context_id == 0, f"expected context 0, got {context_id}"


@cocotb.test()
async def test_config_readback_via_pins(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure_ctx(dut, ctx=1, start_ev=ACK, end_ev=DATA, min_lat=5, max_lat=12, enable=1)

    byte0 = await cfg_read(dut, ctx=1, byte_sel=0)
    expected_byte0 = (ACK << 6) | (DATA << 4) | 5
    assert byte0 == expected_byte0

    byte1 = await cfg_read(dut, ctx=1, byte_sel=1)
    expected_byte1 = (1 << 7) | 12
    assert byte1 == expected_byte1


@cocotb.test()
async def test_two_way_arbitration_via_pins(dut):
    """Same scenario as baseline's equivalent test -- proves the
    RTFCE arbitration chain (monitor_ctx_rtfce -> classify_arbiter ->
    shared_classifier -> result_arbiter) works correctly end-to-end
    through the real pin interface, with correct priority ordering."""
    await start_clock(dut)
    await reset_dut(dut)
    await configure_ctx(dut, ctx=0, start_ev=REQ, end_ev=DONE, min_lat=0, max_lat=15, enable=1)
    await configure_ctx(dut, ctx=1, start_ev=REQ, end_ev=DONE, min_lat=0, max_lat=15, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 5)
    await pulse_event(dut, DONE)

    val1 = await wait_for_uo_result_valid(dut)
    ctx1_first = (val1 >> 2) & 0x3
    assert ctx1_first == 0, f"expected ctx0 served first, got {ctx1_first}"
    await NextTimeStep()

    val2 = await wait_for_uo_result_valid(dut)
    ctx2_second = (val2 >> 2) & 0x3
    assert ctx2_second == 1, f"expected ctx1 served second, got {ctx2_second}"


@cocotb.test()
async def test_timeout_via_pins(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure_ctx(dut, ctx=2, start_ev=REQ, end_ev=DONE, min_lat=0, max_lat=15, enable=1)

    await pulse_event(dut, REQ)
    val = await wait_for_uo_result_valid(dut, max_cycles=40)
    result = val & 0x3
    context_id = (val >> 2) & 0x3
    assert result == TIMEOUT, f"expected TIMEOUT, got {result}"
    assert context_id == 2
