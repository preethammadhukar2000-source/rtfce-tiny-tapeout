// =====================================================================
// shared_classifier.v
//
// Pure combinational PASS/EARLY/TIMEOUT classifier. This is the ONE
// piece of logic that RTFCE shares across all 3 contexts via
// classify_arbiter -- in baseline, this same comparison exists
// independently inside each of the 3 monitor_ctx instances (x3
// duplication). This is the actual research contribution.
//
// Works uniformly for both normal completion and timeout cases:
// a context that times out (no end event within max_latency) enters
// DONE_PENDING with latched_latency already > max_latency, so the
// same two-comparison logic below classifies it correctly as TIMEOUT
// without any special-case branch.
//
// Boundary rules (must match monitor_ctx.v exactly, spec section 13/14):
//   latched_latency  < min_latency  -> EARLY
//   latched_latency == min_latency  -> PASS
//   latched_latency == max_latency  -> PASS
//   latched_latency  > max_latency  -> TIMEOUT
// =====================================================================

module shared_classifier (
    input  wire [4:0] latched_latency,
    input  wire [3:0] min_latency,
    input  wire [3:0] max_latency,
    output wire [1:0] result   // 00=PASS 01=EARLY 10=TIMEOUT
);

    wire is_early   = (latched_latency < {1'b0, min_latency});
    wire is_timeout = (latched_latency > {1'b0, max_latency});

    assign result = is_timeout ? 2'b10 :
                    is_early   ? 2'b01 :
                                 2'b00;

endmodule
