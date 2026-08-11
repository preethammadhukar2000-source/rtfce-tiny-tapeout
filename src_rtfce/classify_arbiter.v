// =====================================================================
// classify_arbiter.v
//
// Routes DONE_PENDING contexts to the single shared_classifier
// instance, one context per cycle, fixed priority Ctx0 > Ctx1 > Ctx2.
// This is the arbitration half of the RTFCE optimization -- paired
// with shared_classifier.v, this replaces the 3x duplicated
// classify/compare logic from the baseline monitor_ctx.v.
//
// Each context's (latched_latency, min_latency, max_latency) is muxed
// combinationally into the ONE shared_classifier instance; the result
// is registered and a one-cycle grant pulse tells the winning context
// to return to IDLE (mirrors the DONE_PENDING->IDLE transition that
// exists but is unused in the baseline).
// =====================================================================

module classify_arbiter (
    input  wire       clk,
    input  wire       rst_n,

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

    output reg         grant0,   // 1-cycle pulse: ctx0's result was just classified
    output reg         grant1,
    output reg         grant2,

    output reg  [1:0]  result,
    output reg  [1:0]  context_id,
    output reg         result_valid,
    output wire        busy
);

    assign busy = pend0 | pend1 | pend2;

    // ---- combinational fixed-priority selection + mux into the ONE shared classifier ----
    reg [1:0] sel_ctx;  // 0,1,2 = context; 3 = none pending
    always @(*) begin
        if (pend0)      sel_ctx = 2'd0;
        else if (pend1) sel_ctx = 2'd1;
        else if (pend2) sel_ctx = 2'd2;
        else            sel_ctx = 2'd3;
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

    // The ONE shared classifier instance -- this is the actual sharing.
    shared_classifier u_shared_classifier (
        .latched_latency(sel_latency),
        .min_latency(sel_min),
        .max_latency(sel_max),
        .result(classified_result)
    );

    // ---- registered output + grant pulse (D5-style, 1-cycle latency) ----
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            grant0       <= 1'b0;
            grant1       <= 1'b0;
            grant2       <= 1'b0;
            result       <= 2'b00;
            context_id   <= 2'b00;
            result_valid <= 1'b0;
        end else begin
            grant0       <= 1'b0;
            grant1       <= 1'b0;
            grant2       <= 1'b0;
            result_valid <= 1'b0;

            case (sel_ctx)
                2'd0: begin
                    result       <= classified_result;
                    context_id   <= 2'd0;
                    result_valid <= 1'b1;
                    grant0       <= 1'b1;
                end
                2'd1: begin
                    result       <= classified_result;
                    context_id   <= 2'd1;
                    result_valid <= 1'b1;
                    grant1       <= 1'b1;
                end
                2'd2: begin
                    result       <= classified_result;
                    context_id   <= 2'd2;
                    result_valid <= 1'b1;
                    grant2       <= 1'b1;
                end
                default: ; // nothing pending, no action
            endcase
        end
    end

endmodule
