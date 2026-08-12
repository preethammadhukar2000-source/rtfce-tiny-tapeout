"""
Cocotb unit test for shared_classifier_heavy.v (D13).
Verifies base PASS/EARLY/TIMEOUT classification is unchanged from
shared_classifier.v, PLUS the new near_miss diagnostic at MARGIN=2.
"""

import cocotb
from cocotb.triggers import Timer

PASS, EARLY, TIMEOUT = 0, 1, 2
MARGIN = 2


async def settle():
    await Timer(1, unit="ns")


@cocotb.test()
async def test_base_classification_unchanged(dut):
    """Sanity: result classification must match shared_classifier.v exactly."""
    dut.min_latency.value = 4
    dut.max_latency.value = 9

    cases = [(2, EARLY), (4, PASS), (6, PASS), (9, PASS), (11, TIMEOUT)]
    for latency, expected in cases:
        dut.latched_latency.value = latency
        await settle()
        assert dut.result.value == expected, f"latency={latency}: expected {expected}"


@cocotb.test()
async def test_near_miss_approaching_timeout(dut):
    """latency within MARGIN below max (still PASS) -> near_miss=1."""
    dut.min_latency.value = 0
    dut.max_latency.value = 10

    # max=10, margin=2 -> latency 8,9,10 should be near_miss; latency 7 should not
    for latency in [8, 9, 10]:
        dut.latched_latency.value = latency
        await settle()
        assert dut.result.value == PASS
        assert dut.near_miss.value == 1, f"latency={latency} should be near_miss (approaching timeout)"

    dut.latched_latency.value = 7
    await settle()
    assert dut.near_miss.value == 0, "latency=7 is not within margin of max=10"


@cocotb.test()
async def test_near_miss_just_timed_out(dut):
    """latency within MARGIN above max (TIMEOUT) -> near_miss=1."""
    dut.min_latency.value = 0
    dut.max_latency.value = 10

    for latency in [11, 12]:
        dut.latched_latency.value = latency
        await settle()
        assert dut.result.value == TIMEOUT
        assert dut.near_miss.value == 1, f"latency={latency} is a near-miss TIMEOUT"

    dut.latched_latency.value = 15
    await settle()
    assert dut.result.value == TIMEOUT
    assert dut.near_miss.value == 0, "latency=15 is well past the margin, not a near miss"


@cocotb.test()
async def test_near_miss_approaching_early_boundary(dut):
    """latency within MARGIN below min (EARLY) -> near_miss=1."""
    dut.min_latency.value = 10
    dut.max_latency.value = 15

    for latency in [8, 9]:
        dut.latched_latency.value = latency
        await settle()
        assert dut.result.value == EARLY
        assert dut.near_miss.value == 1, f"latency={latency} is near the min boundary"

    dut.latched_latency.value = 3
    await settle()
    assert dut.result.value == EARLY
    assert dut.near_miss.value == 0, "latency=3 is well below the margin, not a near miss"


@cocotb.test()
async def test_no_near_miss_mid_range(dut):
    """A comfortably mid-range PASS should never be flagged as near_miss."""
    dut.min_latency.value = 0
    dut.max_latency.value = 15

    dut.latched_latency.value = 7
    await settle()
    assert dut.result.value == PASS
    assert dut.near_miss.value == 0
