"""
Baseline_v2 (heavy, duplicated) vs RTFCE_v2_heavy (heavy, shared)
equivalence test. Extends the original equivalence test to also
verify near_miss (D13) matches between designs.
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


async def pulse_event(dut, code):
    dut.ui_in.value = build_ui_in(strobe=1, cfg_mode=0, event_code=code)
    await RisingEdge(dut.clk)
    await ReadOnly()
    await NextTimeStep()
    dut.ui_in.value = build_ui_in(strobe=0, cfg_mode=0, event_code=0)


async def wait_for_both_and_compare(dut, max_cycles=40, label=""):
    baseline_seen = []
    rtfce_seen = []

    for _ in range(max_cycles):
        await RisingEdge(dut.clk)
        await ReadOnly()

        uo_b = int(dut.uo_out_baseline.value)
        uo_r = int(dut.uo_out_rtfce.value)

        if (uo_b >> 4) & 1:
            baseline_seen.append((uo_b & 0x3, (uo_b >> 2) & 0x3, (uo_b >> 7) & 1))
        if (uo_r >> 4) & 1:
            rtfce_seen.append((uo_r & 0x3, (uo_r >> 2) & 0x3, (uo_r >> 7) & 1))

        await NextTimeStep()

        if baseline_seen and rtfce_seen:
            break

    assert baseline_seen, f"[{label}] baseline never asserted result_valid"
    assert rtfce_seen, f"[{label}] rtfce never asserted result_valid"
    assert baseline_seen[0] == rtfce_seen[0], \
        f"[{label}] MISMATCH: baseline={baseline_seen[0]} rtfce={rtfce_seen[0]} (result, ctx, near_miss)"
    return baseline_seen[0]


@cocotb.test()
async def test_equiv_v2_pass_no_near_miss(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure_ctx(dut, ctx=0, start_ev=REQ, end_ev=DONE, min_lat=0, max_lat=15, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 7)
    await pulse_event(dut, DONE)

    result, ctx, nm = await wait_for_both_and_compare(dut, label="v2_pass_no_nm")
    assert result == PASS
    assert nm == 0


@cocotb.test()
async def test_equiv_v2_pass_near_timeout(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure_ctx(dut, ctx=1, start_ev=REQ, end_ev=DONE, min_lat=0, max_lat=10, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 9)
    await pulse_event(dut, DONE)

    result, ctx, nm = await wait_for_both_and_compare(dut, label="v2_pass_near_timeout")
    assert result == PASS
    assert nm == 1, "both designs must agree latency=9 (max=10) is a near miss"


@cocotb.test()
async def test_equiv_v2_timeout_near_miss(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure_ctx(dut, ctx=2, start_ev=REQ, end_ev=DONE, min_lat=0, max_lat=10, enable=1)

    await pulse_event(dut, REQ)
    result, ctx, nm = await wait_for_both_and_compare(dut, max_cycles=40, label="v2_timeout_nm")
    assert result == TIMEOUT
    assert nm == 1


@cocotb.test()
async def test_equiv_v2_early(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure_ctx(dut, ctx=0, start_ev=REQ, end_ev=DONE, min_lat=5, max_lat=10, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 2)
    await pulse_event(dut, DONE)

    result, ctx, nm = await wait_for_both_and_compare(dut, label="v2_early")
    assert result == EARLY
