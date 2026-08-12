// =====================================================================
// project.v  --  tt_um_rtfce
//
// Baseline top-level: 3x independent monitor_ctx instances + shared
// result_arbiter for I/O serialization only (NOT classification --
// see D10/D11). This is the fair-comparison baseline; RTFCE will
// reuse the same pin interface and arbiter, differing only in the
// internal classify/compare datapath.
//
// Pin map per spec v1.1, section 3/4/5/11.
// =====================================================================

`default_nettype none

module tt_um_rtfce_baseline (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire        ena,
    input  wire        clk,
    input  wire        rst_n
);

    // ---- decode control pins (section 4.1) ----
    wire        strobe      = ui_in[0];
    wire        cfg_mode    = ui_in[1];
    wire        cfg_rw      = ui_in[2];     // 0=write 1=read
    wire        cfg_byte_sel= ui_in[3];
    wire [1:0]  addr_sel    = ui_in[5:4];
    wire [1:0]  event_code  = ui_in[7:6];

    wire        rst_n_int = rst_n & ena;

    // ---- config write demux (only active in cfg_mode, rw=0) ----
    wire cfg_write_pulse = cfg_mode & ~cfg_rw & strobe;
    wire ctx0_cfg_write  = cfg_write_pulse & (addr_sel == 2'd0);
    wire ctx1_cfg_write  = cfg_write_pulse & (addr_sel == 2'd1);
    wire ctx2_cfg_write  = cfg_write_pulse & (addr_sel == 2'd2);

    // ---- event bus (only active in normal mode) ----
    wire event_strobe = ~cfg_mode & strobe;

    // ---- per-context result wires ----
    wire [1:0] res0, res1, res2;
    wire       valid0, valid1, valid2;
    wire       busy0, busy1, busy2;
    wire [7:0] cfg_rdata0, cfg_rdata1, cfg_rdata2;

    monitor_ctx u_ctx0 (
        .clk(clk), .rst_n(rst_n_int),
        .cfg_write(ctx0_cfg_write), .cfg_byte_sel(cfg_byte_sel),
        .cfg_wdata(uio_in), .cfg_rdata(cfg_rdata0),
        .event_strobe(event_strobe), .event_code(event_code),
        .result(res0), .result_valid(valid0), .busy(busy0)
    );

    monitor_ctx u_ctx1 (
        .clk(clk), .rst_n(rst_n_int),
        .cfg_write(ctx1_cfg_write), .cfg_byte_sel(cfg_byte_sel),
        .cfg_wdata(uio_in), .cfg_rdata(cfg_rdata1),
        .event_strobe(event_strobe), .event_code(event_code),
        .result(res1), .result_valid(valid1), .busy(busy1)
    );

    monitor_ctx u_ctx2 (
        .clk(clk), .rst_n(rst_n_int),
        .cfg_write(ctx2_cfg_write), .cfg_byte_sel(cfg_byte_sel),
        .cfg_wdata(uio_in), .cfg_rdata(cfg_rdata2),
        .event_strobe(event_strobe), .event_code(event_code),
        .result(res2), .result_valid(valid2), .busy(busy2)
    );

    // ---- shared I/O result serializer (D11 -- identical in RTFCE) ----
    wire [1:0] arb_result, arb_context_id;
    wire       arb_result_valid, arb_busy;

    result_arbiter u_arbiter (
        .clk(clk), .rst_n(rst_n_int),
        .result_valid_in0(valid0), .result_code_in0(res0),
        .result_valid_in1(valid1), .result_code_in1(res1),
        .result_valid_in2(valid2), .result_code_in2(res2),
        .result(arb_result), .context_id(arb_context_id),
        .result_valid(arb_result_valid), .busy(arb_busy)
    );

    // ---- global status counters (D4, saturating per section 26) ----
    reg [7:0] success_count;
    reg [7:0] fault_count;
    wire      is_timeout = (arb_result == 2'b10);

    always @(posedge clk or negedge rst_n_int) begin
        if (!rst_n_int) begin
            success_count <= 8'd0;
            fault_count   <= 8'd0;
        end else if (arb_result_valid) begin
            if (is_timeout) begin
                if (fault_count != 8'hFF) fault_count <= fault_count + 8'd1;
            end else begin
                if (success_count != 8'hFF) success_count <= success_count + 8'd1;
            end
        end
    end

    // ---- config readback mux (section 4.4) ----
    reg [7:0] cfg_rdata_mux;
    always @(*) begin
        case (addr_sel)
            2'd0: cfg_rdata_mux = cfg_rdata0;
            2'd1: cfg_rdata_mux = cfg_rdata1;
            2'd2: cfg_rdata_mux = cfg_rdata2;
            2'd3: cfg_rdata_mux = cfg_byte_sel ? fault_count : success_count;
            default: cfg_rdata_mux = 8'h00;
        endcase
    end

    // registered read, per D5 (1-cycle latency)
    reg [7:0] cfg_rdata_reg;
    wire      cfg_read_pulse = cfg_mode & cfg_rw & strobe;
    always @(posedge clk or negedge rst_n_int) begin
        if (!rst_n_int)
            cfg_rdata_reg <= 8'h00;
        else if (cfg_read_pulse)
            cfg_rdata_reg <= cfg_rdata_mux;
    end

    // ---- uio bus direction (section 4.2) ----
    assign uio_out = cfg_rdata_reg;
    assign uio_oe  = (cfg_mode & cfg_rw) ? 8'hFF : 8'h00;

    // ---- uo_out result/status bus (section 5) ----
    assign uo_out[1:0] = arb_result;
    assign uo_out[3:2] = arb_context_id;
    assign uo_out[4]   = arb_result_valid;
    assign uo_out[5]   = arb_busy | busy0 | busy1 | busy2;
    assign uo_out[6]   = arb_result_valid & is_timeout;
    assign uo_out[7]   = 1'b0;

endmodule
