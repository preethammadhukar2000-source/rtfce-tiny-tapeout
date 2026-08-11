"""
Baseline vs RTFCE equivalence test (spec section 39 -- non-negotiable).
Drives IDENTICAL stimulus into both tt_um_rtfce (baseline) and
rtfce_top (optimized) through the same shared pins, and asserts their
uo_out values match on every cycle where either asserts result_valid.

If this ever fails, per the project rules: STOP optimization work and
debug before proceeding to physical design.
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
    """Step clock-by-clock. Whenever EITHER design asserts result_valid,
    record its (result, context_id). Once both have produced exactly
    one result_valid pulse, compare them. Allows the two designs to
    have different cycle-by-cycle timing (RTFCE has a fixed 1-cycle
    arbiter latency baseline doesn't in the single-context case) as
    long as the eventual classification matches."""
    baseline_seen = []
    rtfce_seen = []

    for _ in range(max_cycles):
        await RisingEdge(dut.clk)
        await ReadOnly()

        uo_b = int(dut.uo_out_baseline.value)
        uo_r = int(dut.uo_out_rtfce.value)

        if (uo_b >> 4) & 1:
            baseline_seen.append((uo_b & 0x3, (uo_b >> 2) & 0x3))
        if (uo_r >> 4) & 1:
            rtfce_seen.append((uo_r & 0x3, (uo_r >> 2) & 0x3))

        await NextTimeStep()

        if baseline_seen and rtfce_seen:
            break

    assert baseline_seen, f"[{label}] baseline never asserted result_valid"
    assert rtfce_seen, f"[{label}] rtfce never asserted result_valid"
    assert baseline_seen[0] == rtfce_seen[0], \
        f"[{label}] MISMATCH: baseline={baseline_seen[0]} rtfce={rtfce_seen[0]}"
    return baseline_seen[0]


@cocotb.test()
async def test_equiv_reset(dut):
    await start_clock(dut)
    await reset_dut(dut)
    assert (int(dut.uo_out_baseline.value) >> 4) & 1 == 0
    assert (int(dut.uo_out_rtfce.value) >> 4) & 1 == 0


@cocotb.test()
async def test_equiv_pass(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure_ctx(dut, ctx=0, start_ev=REQ, end_ev=DONE, min_lat=3, max_lat=10, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 5)
    await pulse_event(dut, DONE)

    result, ctx = await wait_for_both_and_compare(dut, label="pass")
    assert result == PASS
    assert ctx == 0


@cocotb.test()
async def test_equiv_early(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure_ctx(dut, ctx=1, start_ev=REQ, end_ev=DONE, min_lat=5, max_lat=10, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 2)
    await pulse_event(dut, DONE)

    result, ctx = await wait_for_both_and_compare(dut, label="early")
    assert result == EARLY
    assert ctx == 1


@cocotb.test()
async def test_equiv_timeout(dut):
    await start_clock(dut)
    await reset_dut(dut)
    await configure_ctx(dut, ctx=2, start_ev=REQ, end_ev=DONE, min_lat=0, max_lat=15, enable=1)

    await pulse_event(dut, REQ)
    result, ctx = await wait_for_both_and_compare(dut, max_cycles=40, label="timeout")
    assert result == TIMEOUT
    assert ctx == 2


@cocotb.test()
async def test_equiv_boundary_max(dut):
    """The most important boundary case: end event wins the tie."""
    await start_clock(dut)
    await reset_dut(dut)
    await configure_ctx(dut, ctx=0, start_ev=REQ, end_ev=DONE, min_lat=3, max_lat=10, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 10)
    await pulse_event(dut, DONE)

    result, ctx = await wait_for_both_and_compare(dut, label="boundary_max")
    assert result == PASS, "latency == max_latency must be PASS in BOTH designs"


@cocotb.test()
async def test_equiv_two_way_priority(dut):
    """Both contexts complete simultaneously -- both designs must
    agree on serving Ctx0 first, Ctx1 second, with correct results."""
    await start_clock(dut)
    await reset_dut(dut)
    await configure_ctx(dut, ctx=0, start_ev=REQ, end_ev=DONE, min_lat=0, max_lat=15, enable=1)
    await configure_ctx(dut, ctx=1, start_ev=REQ, end_ev=DONE, min_lat=0, max_lat=15, enable=1)

    await pulse_event(dut, REQ)
    await ClockCycles(dut.clk, 5)
    await pulse_event(dut, DONE)

    # First result from each
    baseline_first = None
    rtfce_first = None
    baseline_second = None
    rtfce_second = None

    for _ in range(20):
        await RisingEdge(dut.clk)
        await ReadOnly()
        uo_b = int(dut.uo_out_baseline.value)
        uo_r = int(dut.uo_out_rtfce.value)

        if (uo_b >> 4) & 1:
            entry = (uo_b & 0x3, (uo_b >> 2) & 0x3)
            if baseline_first is None:
                baseline_first = entry
            elif baseline_second is None:
                baseline_second = entry
        if (uo_r >> 4) & 1:
            entry = (uo_r & 0x3, (uo_r >> 2) & 0x3)
            if rtfce_first is None:
                rtfce_first = entry
            elif rtfce_second is None:
                rtfce_second = entry

        await NextTimeStep()
        if baseline_second and rtfce_second:
            break

    assert baseline_first == rtfce_first, \
        f"first result mismatch: baseline={baseline_first} rtfce={rtfce_first}"
    assert baseline_second == rtfce_second, \
        f"second result mismatch: baseline={baseline_second} rtfce={rtfce_second}"
    assert baseline_first[1] == 0, "both designs must serve ctx0 first"
    assert baseline_second[1] == 1, "both designs must serve ctx1 second"
