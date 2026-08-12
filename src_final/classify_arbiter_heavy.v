// =====================================================================
// classify_arbiter_heavy.v (D13 -- classifier-complexity experiment)
//
// Same structure as classify_arbiter.v (v2, with rr_enable/D12), but
// routes to the ONE SHARED shared_classifier_heavy instance instead
// of shared_classifier -- this is the actual "sharing" being measured
// in the crossover-point experiment: one heavy classifier shared
// across 3 contexts, vs 3 heavy classifiers duplicated (project_v2.v).
// =====================================================================

module classify_arbiter_heavy (
    input  wire       clk,
    input  wire       rst_n,
    input  wire        rr_enable,

    input  wire        pend0,
    input  wire [4:0]  latency0,
    input  wire [3:0]  min0,
    input  wire [3:0]  max0,

    input  wire        pend1,
    input  wire [4:0]  latency1,
    input  wire [3:0]  min1,
    input  wire [3:0]  max1,

    input  wire        pend2,
    input  wire [4:0]  latency2,
    input  wire [3:0]  min2,
    input  wire [3:0]  max2,

    output reg         grant0,
    output reg         grant1,
    output reg         grant2,

    output reg  [1:0]  result,
    output reg          near_miss,
    output reg  [1:0]  context_id,
    output reg         result_valid,
    output wire        busy
);

    assign busy = pend0 | pend1 | pend2;

    reg [1:0] last_served;

    reg [1:0] sel_ctx;
    always @(*) begin
        if (!rr_enable) begin
            if (pend0)      sel_ctx = 2'd0;
            else if (pend1) sel_ctx = 2'd1;
            else if (pend2) sel_ctx = 2'd2;
            else            sel_ctx = 2'd3;
        end else begin
            case (last_served)
                2'd0: begin
                    if (pend1)      sel_ctx = 2'd1;
                    else if (pend2) sel_ctx = 2'd2;
                    else if (pend0) sel_ctx = 2'd0;
                    else            sel_ctx = 2'd3;
                end
                2'd1: begin
                    if (pend2)      sel_ctx = 2'd2;
                    else if (pend0) sel_ctx = 2'd0;
                    else if (pend1) sel_ctx = 2'd1;
                    else            sel_ctx = 2'd3;
                end
                default: begin
                    if (pend0)      sel_ctx = 2'd0;
                    else if (pend1) sel_ctx = 2'd1;
                    else if (pend2) sel_ctx = 2'd2;
                    else            sel_ctx = 2'd3;
                end
            endcase
        end
    end

    wire [4:0] sel_latency = (sel_ctx == 2'd0) ? latency0 :
                              (sel_ctx == 2'd1) ? latency1 :
                              (sel_ctx == 2'd2) ? latency2 : 5'd0;
    wire [3:0] sel_min     = (sel_ctx == 2'd0) ? min0 :
                              (sel_ctx == 2'd1) ? min1 :
                              (sel_ctx == 2'd2) ? min2 : 4'd0;
    wire [3:0] sel_max     = (sel_ctx == 2'd0) ? max0 :
                              (sel_ctx == 2'd1) ? max1 :
                              (sel_ctx == 2'd2) ? max2 : 4'd0;

    wire [1:0] classified_result;
    wire       classified_near_miss;

    // The ONE shared HEAVY classifier -- this is the actual sharing being measured.
    shared_classifier_heavy u_shared_classifier_heavy (
        .latched_latency(sel_latency),
        .min_latency(sel_min),
        .max_latency(sel_max),
        .result(classified_result),
        .near_miss(classified_near_miss)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            grant0       <= 1'b0;
            grant1       <= 1'b0;
            grant2       <= 1'b0;
            result       <= 2'b00;
            near_miss    <= 1'b0;
            context_id   <= 2'b00;
            result_valid <= 1'b0;
            last_served  <= 2'd2;
        end else begin
            grant0       <= 1'b0;
            grant1       <= 1'b0;
            grant2       <= 1'b0;
            result_valid <= 1'b0;

            case (sel_ctx)
                2'd0: begin
                    result       <= classified_result;
                    near_miss    <= classified_near_miss;
                    context_id   <= 2'd0;
                    result_valid <= 1'b1;
                    grant0       <= 1'b1;
                    last_served  <= 2'd0;
                end
                2'd1: begin
                    result       <= classified_result;
                    near_miss    <= classified_near_miss;
                    context_id   <= 2'd1;
                    result_valid <= 1'b1;
                    grant1       <= 1'b1;
                    last_served  <= 2'd1;
                end
                2'd2: begin
                    result       <= classified_result;
                    near_miss    <= classified_near_miss;
                    context_id   <= 2'd2;
                    result_valid <= 1'b1;
                    grant2       <= 1'b1;
                    last_served  <= 2'd2;
                end
                default: ;
            endcase
        end
    end

endmodule
