// =====================================================================
// shared_classifier_heavy.v  (D13 -- classifier-complexity experiment)
//
// Same PASS/EARLY/TIMEOUT classification as shared_classifier.v, PLUS
// a near_miss diagnostic: asserted when latched_latency falls within
// MARGIN cycles of either boundary. This roughly doubles the
// comparator/subtractor count relative to the base classifier,
// modeling a genuinely more complex shared resource for the
// baseline_v2 vs RTFCE_v2_heavy area-scaling comparison.
//
// Used ONLY in the _v2/_heavy design variants -- the primary v1.1/D12
// design continues to use the lightweight shared_classifier.v.
// =====================================================================

module shared_classifier_heavy #(
    parameter MARGIN = 5'd2
) (
    input  wire [4:0] latched_latency,
    input  wire [3:0] min_latency,
    input  wire [3:0] max_latency,
    output wire [1:0] result,     // 00=PASS 01=EARLY 10=TIMEOUT
    output wire        near_miss   // NEW: within MARGIN of a boundary
);

    wire is_early   = (latched_latency < {1'b0, min_latency});
    wire is_timeout = (latched_latency > {1'b0, max_latency});

    assign result = is_timeout ? 2'b10 :
                    is_early   ? 2'b01 :
                                 2'b00;

    // ---- near-miss / margin detection (the "heavy" half) ----
    wire [4:0] min_ext = {1'b0, min_latency};
    wire [4:0] max_ext = {1'b0, max_latency};

    // distance below min (only meaningful if latency < min, i.e. EARLY or approaching it)
    wire [4:0] dist_below_min = (min_ext > latched_latency) ? (min_ext - latched_latency) : 5'd0;
    // distance below max (only meaningful if latency <= max, i.e. PASS approaching TIMEOUT)
    wire [4:0] dist_below_max = (max_ext > latched_latency) ? (max_ext - latched_latency) : 5'd0;
    // distance above max (only meaningful if latency > max, i.e. TIMEOUT that just barely happened)
    wire [4:0] dist_above_max = (latched_latency > max_ext) ? (latched_latency - max_ext) : 5'd0;

    wire near_early_boundary   = is_early   && (dist_below_min <= MARGIN);
    wire near_timeout_boundary = !is_timeout && (dist_below_max <= MARGIN);
    wire near_timeout_just_hit = is_timeout && (dist_above_max <= MARGIN);

    assign near_miss = near_early_boundary || near_timeout_boundary || near_timeout_just_hit;

endmodule
