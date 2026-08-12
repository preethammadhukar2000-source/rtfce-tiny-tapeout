// =====================================================================
// result_arbiter_heavy.v (D13 -- classifier-complexity experiment)
//
// Same fixed-priority serialization as result_arbiter.v, but also
// carries near_miss alongside result/context_id, so it can reach
// uo_out[7] per D13. Used only in the baseline_v2 / RTFCE_v2_heavy
// variants -- the primary design continues to use result_arbiter.v
// unchanged.
// =====================================================================

module result_arbiter_heavy (
    input  wire       clk,
    input  wire       rst_n,

    input  wire        result_valid_in0,
    input  wire [1:0]  result_code_in0,
    input  wire        near_miss_in0,
    input  wire        result_valid_in1,
    input  wire [1:0]  result_code_in1,
    input  wire        near_miss_in1,
    input  wire        result_valid_in2,
    input  wire [1:0]  result_code_in2,
    input  wire        near_miss_in2,

    output reg  [1:0]  result,
    output reg  [1:0]  context_id,
    output reg         near_miss,
    output reg         result_valid,
    output wire        busy
);

    reg       pend0, pend1, pend2;
    reg [1:0] res0,  res1,  res2;
    reg       nm0,   nm1,   nm2;

    assign busy = pend0 | pend1 | pend2;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pend0 <= 1'b0; pend1 <= 1'b0; pend2 <= 1'b0;
            res0  <= 2'b00; res1 <= 2'b00; res2 <= 2'b00;
            nm0   <= 1'b0;  nm1  <= 1'b0;  nm2  <= 1'b0;
            result       <= 2'b00;
            context_id   <= 2'b00;
            near_miss    <= 1'b0;
            result_valid <= 1'b0;
        end else begin
            result_valid <= 1'b0;

            if (result_valid_in0) begin pend0 <= 1'b1; res0 <= result_code_in0; nm0 <= near_miss_in0; end
            if (result_valid_in1) begin pend1 <= 1'b1; res1 <= result_code_in1; nm1 <= near_miss_in1; end
            if (result_valid_in2) begin pend2 <= 1'b1; res2 <= result_code_in2; nm2 <= near_miss_in2; end

            if (pend0) begin
                result       <= res0;
                near_miss    <= nm0;
                context_id   <= 2'd0;
                result_valid <= 1'b1;
                pend0        <= 1'b0;
            end else if (pend1) begin
                result       <= res1;
                near_miss    <= nm1;
                context_id   <= 2'd1;
                result_valid <= 1'b1;
                pend1        <= 1'b0;
            end else if (pend2) begin
                result       <= res2;
                near_miss    <= nm2;
                context_id   <= 2'd2;
                result_valid <= 1'b1;
                pend2        <= 1'b0;
            end
        end
    end

endmodule
