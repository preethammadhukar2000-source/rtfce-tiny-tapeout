"""
Cocotb unit test for shared_classifier.v (pure combinational).
Exhaustively checks the min/max boundary rules that must match
monitor_ctx.v exactly for baseline/RTFCE equivalence to hold.
"""

import cocotb
from cocotb.triggers import Timer

PASS, EARLY, TIMEOUT = 0, 1, 2


async def settle():
    """Allow combinational logic to propagate."""
    await Timer(1, unit="ns")


@cocotb.test()
async def test_pass_mid(dut):
    dut.latched_latency.value = 5
    dut.min_latency.value = 3
    dut.max_latency.value = 10
    await settle()
    assert dut.result.value == PASS


@cocotb.test()
async def test_pass_boundary_min(dut):
    dut.latched_latency.value = 3
    dut.min_latency.value = 3
    dut.max_latency.value = 10
    await settle()
    assert dut.result.value == PASS, "latency == min must be PASS"


@cocotb.test()
async def test_pass_boundary_max(dut):
    dut.latched_latency.value = 10
    dut.min_latency.value = 3
    dut.max_latency.value = 10
    await settle()
    assert dut.result.value == PASS, "latency == max must be PASS (end event wins)"


@cocotb.test()
async def test_early(dut):
    dut.latched_latency.value = 2
    dut.min_latency.value = 3
    dut.max_latency.value = 10
    await settle()
    assert dut.result.value == EARLY


@cocotb.test()
async def test_early_boundary(dut):
    dut.latched_latency.value = 2
    dut.min_latency.value = 3
    dut.max_latency.value = 10
    await settle()
    assert dut.result.value == EARLY, "latency == min-1 must be EARLY"


@cocotb.test()
async def test_timeout(dut):
    dut.latched_latency.value = 11
    dut.min_latency.value = 3
    dut.max_latency.value = 10
    await settle()
    assert dut.result.value == TIMEOUT


@cocotb.test()
async def test_timeout_max15_regression(dut):
    """D8 regression: max_latency=15 requires latched_latency to reach
    16, which only fits because latched_latency is 5 bits wide."""
    dut.latched_latency.value = 16
    dut.min_latency.value = 0
    dut.max_latency.value = 15
    await settle()
    assert dut.result.value == TIMEOUT, "TIMEOUT must fire correctly at max_latency=15"


@cocotb.test()
async def test_min_zero_max_zero(dut):
    """Edge case: both bounds at 0 -- only latency==0 is PASS."""
    dut.min_latency.value = 0
    dut.max_latency.value = 0

    dut.latched_latency.value = 0
    await settle()
    assert dut.result.value == PASS, "latency=0 with min=max=0 must be PASS"

    dut.latched_latency.value = 1
    await settle()
    assert dut.result.value == TIMEOUT, "latency=1 with max=0 must be TIMEOUT"


@cocotb.test()
async def test_exhaustive_sweep(dut):
    """Sweep a representative range of (latency, min, max) combos and
    verify against a Python reference model matching spec section 13."""
    dut.min_latency.value = 4
    dut.max_latency.value = 9

    for latency in range(0, 20):
        dut.latched_latency.value = latency
        await settle()

        if latency < 4:
            expected = EARLY
        elif latency <= 9:
            expected = PASS
        else:
            expected = TIMEOUT

        actual = int(dut.result.value)
        assert actual == expected, \
            f"latency={latency}: expected {expected}, got {actual}"
