module monitor_ctx (
    input  wire       clk,
    input  wire       rst_n,

    input  wire        cfg_write,
    input  wire        cfg_byte_sel,
    input  wire [7:0]  cfg_wdata,
    output wire [7:0]  cfg_rdata,

    input  wire        event_strobe,
    input  wire [1:0]  event_code,

    output reg  [1:0]  result,
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

    localparam IDLE         = 2'd0;
    localparam ARMED        = 2'd1;
    localparam DONE_PENDING = 2'd2;

    reg [1:0] state;
    reg [4:0] timer;
    reg [4:0] latched_latency;

    assign busy = (state != IDLE);

    wire start_match = enable && event_strobe && (event_code == start_event);
    wire end_match   = enable && event_strobe && (event_code == end_event) && (state == ARMED);
    wire timeout_hit  = (state == ARMED) && (timer > {1'b0, max_latency});

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state           <= IDLE;
            timer           <= 5'd0;
            latched_latency <= 5'd0;
            result          <= 2'b00;
            result_valid    <= 1'b0;
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
                        latched_latency <= timer;
                        result_valid    <= 1'b1;
                        result          <= (timer < {1'b0, min_latency}) ? 2'b01 :
                                           2'b00;
                        state           <= IDLE;
                    end else if (timeout_hit) begin
                        result_valid <= 1'b1;
                        result       <= 2'b10;
                        state        <= IDLE;
                    end else begin
                        timer <= timer + 5'd1;
                    end
                end

                DONE_PENDING: begin
                    state <= IDLE;
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
