// =====================================================================
// classify_arbiter.v  (v2 -- adds round-robin policy, D12)
//
// Routes DONE_PENDING contexts to the single shared_classifier
// instance, one context per cycle. Two selectable policies:
//   rr_enable=0: fixed priority Ctx0 > Ctx1 > Ctx2 (v1.1 default, unchanged)
//   rr_enable=1: round-robin, rotating starting after the last-served context
//
// Novelty note: policy is investigated as an explicit design parameter
// per the original project brief's open question (spec section 10).
// =====================================================================

module classify_arbiter (
    input  wire       clk,
    input  wire       rst_n,
    input  wire        rr_enable,   // NEW (D12): 0=fixed priority, 1=round-robin

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
    output reg  [1:0]  context_id,
    output reg         result_valid,
    output wire        busy
);

    assign busy = pend0 | pend1 | pend2;

    // ---- last-served pointer for round-robin (reset -> ctx0 served first) ----
    reg [1:0] last_served;   // 0,1,2 = last granted context; init 2 so first pick is ctx0

    // ---- combinational selection: fixed priority OR round-robin ----
    reg [1:0] sel_ctx;
    always @(*) begin
        if (!rr_enable) begin
            // fixed priority, unchanged from v1.1
            if (pend0)      sel_ctx = 2'd0;
            else if (pend1) sel_ctx = 2'd1;
            else if (pend2) sel_ctx = 2'd2;
            else            sel_ctx = 2'd3;
        end else begin
            // round-robin: check starting after last_served, wrap around
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
                default: begin // 2'd2 or reset value
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

    shared_classifier u_shared_classifier (
        .latched_latency(sel_latency),
        .min_latency(sel_min),
        .max_latency(sel_max),
        .result(classified_result)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            grant0       <= 1'b0;
            grant1       <= 1'b0;
            grant2       <= 1'b0;
            result       <= 2'b00;
            context_id   <= 2'b00;
            result_valid <= 1'b0;
            last_served  <= 2'd2;   // so first served (either policy) is ctx0
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
                    last_served  <= 2'd0;
                end
                2'd1: begin
                    result       <= classified_result;
                    context_id   <= 2'd1;
                    result_valid <= 1'b1;
                    grant1       <= 1'b1;
                    last_served  <= 2'd1;
                end
                2'd2: begin
                    result       <= classified_result;
                    context_id   <= 2'd2;
                    result_valid <= 1'b1;
                    grant2       <= 1'b1;
                    last_served  <= 2'd2;
                end
                default: ; // nothing pending
            endcase
        end
    end

endmodule
