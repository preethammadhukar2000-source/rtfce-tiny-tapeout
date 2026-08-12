
// =====================================================================

// result_arbiter.v

//

// Serializes up to 3 simultaneous monitor completions onto a single

// 1-result-per-cycle output port. Fixed priority: Ctx0 > Ctx1 > Ctx2.

//

// Reused UNCHANGED in both baseline and RTFCE (D11) -- this is I/O

// serialization, not classification sharing, and must be identical

// in both designs for a fair comparison (see D10).

// =====================================================================

module result_arbiter (

    input  wire       clk,

    input  wire       rst_n,

    input  wire        result_valid_in0,

    input  wire [1:0]  result_code_in0,

    input  wire        result_valid_in1,

    input  wire [1:0]  result_code_in1,

    input  wire        result_valid_in2,

    input  wire [1:0]  result_code_in2,

    output reg  [1:0]  result,

    output reg  [1:0]  context_id,

    output reg         result_valid,

    output wire        busy

);

    reg       pend0, pend1, pend2;

    reg [1:0] res0,  res1,  res2;

    assign busy = pend0 | pend1 | pend2;

    always @(posedge clk or negedge rst_n) begin

        if (!rst_n) begin

            pend0 <= 1'b0; pend1 <= 1'b0; pend2 <= 1'b0;

            res0  <= 2'b00; res1 <= 2'b00; res2 <= 2'b00;

            result       <= 2'b00;

            context_id   <= 2'b00;

            result_valid <= 1'b0;

        end else begin

            result_valid <= 1'b0;  // default: 1-cycle pulse

            // Latch any newly-arrived results this cycle (independent of serving below)

            if (result_valid_in0) begin pend0 <= 1'b1; res0 <= result_code_in0; end

            if (result_valid_in1) begin pend1 <= 1'b1; res1 <= result_code_in1; end

            if (result_valid_in2) begin pend2 <= 1'b1; res2 <= result_code_in2; end

            // Serve one pending result per cycle, fixed priority

            if (pend0) begin

                result       <= res0;

                context_id   <= 2'd0;

                result_valid <= 1'b1;

                pend0        <= 1'b0;

            end else if (pend1) begin

                result       <= res1;

                context_id   <= 2'd1;

                result_valid <= 1'b1;

                pend1        <= 1'b0;

            end else if (pend2) begin

                result       <= res2;

                context_id   <= 2'd2;

                result_valid <= 1'b1;

                pend2        <= 1'b0;

            end

        end

    end

endmodule

