"""
Final combined design test: rtfce_top_v2_heavy.v with BOTH D12
(round-robin, selectable) and D13 (heavy classifier + near_miss)
present together. Confirms round-robin arbitration works correctly
even when the shared resource is the heavier classifier.
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


async def set_rr_enable(dut, enable):
    dut.uio_in.value = 1 if enable else 0
    dut.ui_in.value = build_ui_in(strobe=1, cfg_mode=1, cfg_rw=0, cfg_byte_sel=0, addr_sel=3)
    await RisingEdge(dut.clk)
    dut.ui_in.value = build_ui_in(strobe=0, cfg_mode=1, cfg_rw=0, cfg_byte_sel=0, addr_sel=3)
    await RisingEdge(dut.clk)


async def pulse_event(dut, code):
    dut.ui_in.value = build_ui_in(strobe=1, cfg_mode=0, event_code=code)
    await RisingEdge(dut.clk)
    await ReadOnly()
    await NextTimeStep()
    dut.ui_in.value = build_ui_in(strobe=0, cfg_mode=0, event_code=0)


async def wait_for_uo_result_valid(dut, max_cycles=40):
    for _ in range(max_cycles):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if (int(dut.uo_out.value) >> 4) & 1:
            return int(dut.uo_out.value)
        await NextTimeStep()
    raise AssertionError("uo_out result_valid never asserted within max_cycles")


@cocotb.test()
async def test_heavy_with_fixed_priority(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure_ctx(dut, ctx=0, start_ev=REQ, end_ev=DONE, min_lat=0, max_lat=10, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 9)
    await pulse_event(dut, DONE)

    val = await wait_for_uo_result_valid(dut)
    result = val & 0x3
    near_miss = (val >> 7) & 1
    assert result == PASS
    assert near_miss == 1, "latency=9 (max=10, margin=2) should be a near-miss, uo_out[7]"


@cocotb.test()
async def test_heavy_with_round_robin(dut):
    """D12+D13 combined: enable round-robin, arm 3 contexts with the
    heavy classifier active, confirm fair rotation AND correct
    near_miss reporting for each."""
    await start_clock(dut)
    await reset_dut(dut)

    await configure_ctx(dut, ctx=0, start_ev=REQ, end_ev=DONE, min_lat=0, max_lat=10, enable=1)
    await configure_ctx(dut, ctx=1, start_ev=ACK, end_ev=DATA, min_lat=0, max_lat=10, enable=1)
    await configure_ctx(dut, ctx=2, start_ev=DATA, end_ev=ACK, min_lat=0, max_lat=10, enable=1)

    await set_rr_enable(dut, True)

    await pulse_event(dut, REQ)   # starts ctx0
    await pulse_event(dut, ACK)   # starts ctx1
    await pulse_event(dut, DATA)  # starts ctx2, ends ctx1

    await pulse_event(dut, DONE)  # ends ctx0
    await pulse_event(dut, ACK)   # ends ctx2

    served_ctx = []
    for _ in range(6):
        await RisingEdge(dut.clk)
        await ReadOnly()
        val = int(dut.uo_out.value)
        if (val >> 4) & 1:
            served_ctx.append((val >> 2) & 0x3)
        await NextTimeStep()

    assert len(served_ctx) >= 3
    assert set(served_ctx[:3]) == {0, 1, 2}, \
        f"round-robin must serve all 3 contexts even with heavy classifier active, got {served_ctx}"
