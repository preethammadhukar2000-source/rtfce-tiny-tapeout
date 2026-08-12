// =====================================================================
// monitor_ctx_heavy.v (D13 -- classifier-complexity experiment)
//
// Same timer/config/state-machine as baseline monitor_ctx.v, but
// classifies using shared_classifier_heavy (with near_miss diagnostic)
// INSTANTIATED INDEPENDENTLY per context -- this is the baseline_v2
// building block: 3x duplicated HEAVY classifiers, for comparison
// against RTFCE_v2_heavy's single SHARED heavy classifier.
// =====================================================================

module monitor_ctx_heavy (
    input  wire       clk,
    input  wire       rst_n,

    input  wire        cfg_write,
    input  wire        cfg_byte_sel,
    input  wire [7:0]  cfg_wdata,
    output wire [7:0]  cfg_rdata,

    input  wire        event_strobe,
    input  wire [1:0]  event_code,

    output reg  [1:0]  result,
    output reg         near_miss,      // NEW (D13)
    output reg         result_valid,
    output wire        busy
);

    reg [1:0] start_event;
    reg [1:0] end_event;
    reg [3:0] min_latency;
    reg [3:0] max_latency;
    reg       enable;

    assign cfg_rdata = cfg_byte_sel
        ? {enable, 3'b000, max_latency}
        : {start_event, end_event, min_latency};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            start_event <= 2'b00;
            end_event   <= 2'b00;
            min_latency <= 4'h0;
            max_latency <= 4'h0;
            enable      <= 1'b0;
        end else if (cfg_write) begin
            if (cfg_byte_sel) begin
                enable      <= cfg_wdata[7];
                max_latency <= cfg_wdata[3:0];
            end else begin
                start_event <= cfg_wdata[7:6];
                end_event   <= cfg_wdata[5:4];
                min_latency <= cfg_wdata[3:0];
            end
        end
    end

    localparam IDLE  = 2'd0;
    localparam ARMED = 2'd1;

    reg [1:0] state;
    reg [4:0] timer;

    assign busy = (state != IDLE);

    wire start_match = enable && event_strobe && (event_code == start_event) && (state == IDLE);
    wire end_match   = enable && event_strobe && (event_code == end_event) && (state == ARMED);
    wire timeout_hit  = (state == ARMED) && (timer > {1'b0, max_latency});

    // ---- HEAVY classifier, instantiated independently per context ----
    wire [1:0] combi_result;
    wire       combi_near_miss;

    shared_classifier_heavy u_classifier (
        .latched_latency(timer),
        .min_latency(min_latency),
        .max_latency(max_latency),
        .result(combi_result),
        .near_miss(combi_near_miss)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state        <= IDLE;
            timer        <= 5'd0;
            result       <= 2'b00;
            near_miss    <= 1'b0;
            result_valid <= 1'b0;
        end else begin
            result_valid <= 1'b0;

            case (state)
                IDLE: begin
                    timer <= 5'd0;
                    if (start_match) begin
                        state <= ARMED;
                        timer <= 5'd0;
                    end
                end

                ARMED: begin
                    if (end_match) begin
                        result       <= combi_result;
                        near_miss    <= combi_near_miss;
                        result_valid <= 1'b1;
                        state        <= IDLE;
                    end else if (timeout_hit) begin
                        result       <= combi_result;
                        near_miss    <= combi_near_miss;
                        result_valid <= 1'b1;
                        state        <= IDLE;
                    end else begin
                        timer <= timer + 5'd1;
                    end
                end

                default: state <= IDLE;
            endcase

            if (!enable) begin
                state <= IDLE;
                timer <= 5'd0;
            end
        end
    end

endmodule
