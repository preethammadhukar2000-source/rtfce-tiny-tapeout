// =====================================================================
// monitor_ctx_rtfce.v
//
// RTFCE per-context module: same config registers, timer, and state
// machine as baseline monitor_ctx.v, but WITHOUT its own classifier.
// On end_match or timeout_hit, latches latency and enters DONE_PENDING
// for real (this state exists but is dead code in the baseline) --
// waits for a grant pulse from classify_arbiter before returning to
// IDLE. The actual classification happens externally in the shared
// classify_arbiter + shared_classifier pair.
//
// D8/D9 fixes carried over unchanged from baseline monitor_ctx.v.
// =====================================================================

module monitor_ctx_rtfce (
    input  wire       clk,
    input  wire       rst_n,

    // ---- configuration write/read (identical to baseline) ----
    input  wire        cfg_write,
    input  wire        cfg_byte_sel,
    input  wire [7:0]  cfg_wdata,
    output wire [7:0]  cfg_rdata,

    // ---- event bus (shared/broadcast) ----
    input  wire        event_strobe,
    input  wire [1:0]  event_code,

    // ---- arbiter interface (NEW vs baseline) ----
    output wire        pend,             // requesting classification
    output wire [4:0]  latched_latency_out,
    output wire [3:0]  min_latency_out,
    output wire [3:0]  max_latency_out,
    input  wire        grant,            // 1-cycle pulse: classification done, return to IDLE

    output wire        busy
);

    // ---- configuration registers (identical to baseline) ----
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

    // ---- state machine ----
    localparam IDLE         = 2'd0;
    localparam ARMED        = 2'd1;
    localparam DONE_PENDING = 2'd2;   // now load-bearing, unlike baseline

    reg [1:0] state;
    reg [4:0] timer;
    reg [4:0] latched_latency;

    assign busy = (state != IDLE);
    assign pend = (state == DONE_PENDING);
    assign latched_latency_out = latched_latency;
    assign min_latency_out     = min_latency;
    assign max_latency_out     = max_latency;

    wire start_match = enable && event_strobe && (event_code == start_event) && (state == IDLE);
    wire end_match   = enable && event_strobe && (event_code == end_event) && (state == ARMED);
    wire timeout_hit  = (state == ARMED) && (timer > {1'b0, max_latency});

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state           <= IDLE;
            timer           <= 5'd0;
            latched_latency <= 5'd0;
        end else begin
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
                        latched_latency <= timer;   // frozen here, never modified again
                        state           <= DONE_PENDING;
                    end else if (timeout_hit) begin
                        latched_latency <= timer;   // frozen here too -- classifier will see > max
                        state           <= DONE_PENDING;
                    end else begin
                        timer <= timer + 5'd1;
                    end
                end

                DONE_PENDING: begin
                    // latched_latency held constant here -- arbitration
                    // delay can never change the reported value
                    if (grant) begin
                        state <= IDLE;
                    end
                end

                default: state <= IDLE;
            endcase

            if (!enable && state != IDLE) begin
                state <= IDLE;
                timer <= 5'd0;
            end
        end
    end

endmodule
