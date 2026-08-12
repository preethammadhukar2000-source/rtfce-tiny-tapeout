# RTFCE — Prior Art / Novelty Validation

**Status:** Completed. Searches performed via IEEE Xplore (institutional access) and Google Patents.

## Scope of the claim being validated

Per the frozen specification (v1.1) and its extensions (D12, D13), the claimed contribution is **not**:
- temporal monitoring itself
- latency checking itself
- protocol checking itself
- configurable hardware monitoring itself
- multiplexing or arbitration in isolation

The claimed contribution **is**: a multi-context temporal monitoring architecture in which each
monitoring context retains fully independent timing state (start/end event detection, timer,
armed/pending status) while classification (PASS/EARLY/TIMEOUT, plus the near-miss diagnostic
in D13) is performed by a single shared datapath, accessed via event-driven arbitration
(fixed-priority or round-robin, selectable — D12) such that arbitration delay never alters the
reported latency value.

## Patents specifically identified for authenticated review

### US 9,442,788 B2 — "Bus protocol checker, system on chip including the same, bus protocol checking method" (Samsung Electronics, filed 2014, granted 2016)

**What it does:** Describes SoC-level checkers attached to bus IPs that validate *bus protocol
compliance* (field widths, valid IDs, response codes on an AMBA/AXI-style bus) against
reconfigurable check-target/check-list registers, with an optional error-compensation unit that
can substitute corrected data onto the bus.

**Similarity:** Both involve a hardware "checker" with a reconfigurable environment-setting
register accessed via a system bus, and both use a generic internal signal set (their
check-start/check-end/error signals resemble our start-event/end-event/timeout signals in
spirit).

**Difference from RTFCE:**
- Domain is bus **protocol field compliance** (structural correctness of a transaction), not
  **temporal latency measurement** between two arbitrary events with a PASS/EARLY/TIMEOUT
  classification against configurable min/max bounds.
- Their "sub-check logics" each check a different *field* of a single bus signal sequentially;
  there is no independent per-context timer running in parallel, and no arbitration mechanism
  serializing access to a shared classification resource across multiple simultaneously-completing
  monitoring contexts.
- No mechanism analogous to RTFCE's core guarantee -- that arbitration delay cannot alter a
  captured latency value -- because the patent has no continuously-running timer construct at all.
- The error-compensation half of the patent (generating corrected or fake bus responses) has no
  analog in RTFCE.

**Conclusion:** No direct overlap with RTFCE's claimed architecture. Superficial keyword overlap
("checker," "reconfigurable," "environment setting register," "SoC") reflects a shared general
category (configurable on-chip monitoring hardware), not a matching mechanism.

### US 7,194,658 B2 — "Various methods and apparatuses for interfacing of a protocol monitor to protocol checkers and functional checkers" (Sonics, Inc., filed 2003, granted 2007)

**What it does:** Defines a **software programming interface** connecting functional-checker and
protocol-checker components to an interconnect monitor component, for verification tooling
purposes.

**Similarity:** Shares terminology ("protocol monitor," "checker") and the general verification
context.

**Difference from RTFCE:** This is a software/API specification for connecting verification IP
components together, not a hardware architecture. It does not describe timer logic, latency
classification, or resource-sharing arbitration of any kind.

**Conclusion:** No overlap. Different domain (verification-tool software interfacing vs.
synthesizable runtime hardware monitor).

## Broader keyword sweep (IEEE Xplore + Google Patents)

Search terms per the original project brief, each run independently:

| Search term | Representative results | Overlap with RTFCE's specific claim |
|---|---|---|
| temporal monitor hardware | Interrupt latency monitors, network latency monitors (US5944840A, US7127422B1, US7937470B2) | None -- these measure/report latency for logging or QoS purposes; no PASS/EARLY/TIMEOUT classification against configurable bounds, no multi-context sharing |
| latency monitor RTL | Same as above | None |
| shared comparator hardware / multi-context temporal monitor arbitration | Generic dynamic hardware resource arbitration (memory, bus, multi-threaded compute contexts) -- e.g. "Method and apparatus for dynamic hardware arbitration," US7133950B2 | Arbitration concept present, but for *resource access scheduling* (memory bandwidth, execution slots), not for serializing access to a *shared classification computation* while preserving independently-timed latency values |
| programmable hardware timing constraint checker | Design-time static timing analysis (STA) literature and EDA tooling (IEEE Xplore results, PLD timing-error detection patents) | None -- this entire cluster is design-time/EDA verification (checking a synthesized netlist against timing constraints before fabrication), fundamentally different from a runtime hardware monitor observing live events on a chip |
| hardware protocol monitor / configurable protocol checker | Overlaps with US9442788B2 above | Already addressed |
| resource sharing temporal monitor | No directly matching results | -- |
| event-driven temporal monitor | No directly matching results | -- |
| multi-channel latency monitor | Network/transaction latency monitors (financial systems, network devices) | None -- software/network layer, not synthesizable RTL hardware |

## Institutional / prior-work check

A related prior M.Tech internship report from the same department, describing an FSM-based
peripheral controller (address-generation logic, transfer-length register, read/write/
completion state machine), was reviewed for overlap. No overlap was found with RTFCE's
temporal-monitoring or resource-sharing claims -- the reviewed work addresses a different
problem domain (memory-access sequencing) with a different mechanism (no timer-based latency
classification, no shared-datapath arbitration).

The Tiny Tapeout historical project index (recent shuttle project lists, retrieved from the
department's documented tapeout track record) was reviewed against the same keyword list above;
no listed project matches the temporal-monitor-with-shared-classifier architecture.

## Conclusion

No directly matching implementation was identified in the prior-art search performed for this
project, across authenticated IEEE Xplore access, Google Patents, and the two specifically
flagged patents. The two patents identified early in the project (US 9,442,788 and US 7,194,658)
were reviewed in full and found to address different problems (bus protocol field compliance,
and verification-tool software interfacing, respectively) using different mechanisms (no
independent per-context timers, no shared-classifier arbitration with latency preservation).

This is a conservative, search-scope-limited conclusion, not a claim of absolute novelty. It
reflects the searches actually performed and documented above.
