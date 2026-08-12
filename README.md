![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg) ![](../../workflows/fpga/badge.svg)

# RTFCE -- Reconfigurable Temporal Fault/Constraint Engine

**Tiny Tapeout submission, SkyWater 130nm, TTSKY26c shuttle**

- [Read the full project documentation](docs/info.md)
- [Architecture and design decision log](docs/)

## What is this?

RTFCE is a multi-context temporal latency monitor: it watches for configurable start and end
events, measures the number of clock cycles between them per monitoring context, and classifies
each measurement as PASS, EARLY, or TIMEOUT against configurable minimum and maximum bounds.

Three independent monitoring contexts run in parallel, each with its own timer and
configuration. Rather than duplicating the classification logic three times, RTFCE shares a
single classification datapath across all three contexts via an arbiter -- with a hard
correctness guarantee that arbitration delay can never alter a context's reported latency.

**Research contribution:** this project implements both a fully-duplicated baseline and the
RTFCE shared-classifier architecture, physically synthesizes and implements both through the
full SkyWater 130nm LibreLane flow, and measures the real area/timing tradeoff across two
classifier complexity levels and two arbitration policies (fixed-priority and round-robin). The
full baseline-vs-optimized comparison, including the honest finding that resource sharing's
benefit scales with classifier complexity, is documented in `docs/`.

## Design summary

- **Top module:** `tt_um_rtfce`
- **Real device count:** 782 standard cells (post-LVS, SkyWater 130nm sky130_fd_sc_hd)
- **Clock:** 50 MHz (20ns period)
- **Verified:** DRC, LVS, and Antenna checks clean via LibreLane 3.0.7 (local) and Tiny Tapeout's
  own CI pipeline
- **Verification:** cocotb regression covering configuration, all classification boundary cases,
  multi-context arbitration under both policies, and the near-miss diagnostic

## What is Tiny Tapeout?

Tiny Tapeout is an educational project that aims to make it easier and cheaper than ever to get
your digital and analog designs manufactured on a real chip.

To learn more, visit https://tinytapeout.com.

## Resources

- [FAQ](https://tinytapeout.com/faq/)
- [Digital design lessons](https://tinytapeout.com/digital_design/)
- [Build your design locally](https://www.tinytapeout.com/guides/local-hardening/)
