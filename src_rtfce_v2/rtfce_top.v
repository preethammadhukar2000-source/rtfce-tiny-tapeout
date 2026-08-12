// =====================================================================
// rtfce_top.v  (v2 -- adds rr_enable global control, D12)
//
// RTFCE optimized top-level: 3x monitor_ctx_rtfce + ONE shared
// classify_arbiter+shared_classifier pair (now supporting fixed
// priority OR round-robin, selectable) + result_arbiter (unchanged
// from baseline, D11).
//
// NOT tt_um-prefixed -- simulation/comparison vehicle. Winner gets
// renamed to tt_um_rtfce for final submission.
//
// D12: writes to addr_sel=3, byte_sel=0 (previously no-op) now set
// the global rr_enable register (bit 0 of write data).
// =====================================================================

`default_nettype none

module rtfce_top (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire        ena,
    input  wire        clk,
    input  wire        rst_n
);

    wire        strobe      = ui_in[0];
    wire        cfg_mode    = ui_in[1];
    wire        cfg_rw      = ui_in[2];
    wire        cfg_byte_sel= ui_in[3];
    wire [1:0]  addr_sel    = ui_in[5:4];
    wire [1:0]  event_code  = ui_in[7:6];

    wire        rst_n_int = rst_n & ena;

    wire cfg_write_pulse = cfg_mode & ~cfg_rw & strobe;
    wire ctx0_cfg_write  = cfg_write_pulse & (addr_sel == 2'd0);
    wire ctx1_cfg_write  = cfg_write_pulse & (addr_sel == 2'd1);
    wire ctx2_cfg_write  = cfg_write_pulse & (addr_sel == 2'd2);

    wire event_strobe = ~cfg_mode & strobe;

    // ---- D12: global rr_enable control register ----
    reg rr_enable;
    wire global_ctrl_write = cfg_write_pulse & (addr_sel == 2'd3) & ~cfg_byte_sel;
    always @(posedge clk or negedge rst_n_int) begin
        if (!rst_n_int)
            rr_enable <= 1'b0;   // default: fixed priority, matches v1.1 behavior
        else if (global_ctrl_write)
            rr_enable <= uio_in[0];
    end

    wire        pend0, pend1, pend2;
    wire [4:0]  lat0, lat1, lat2;
    wire [3:0]  min0, min1, min2;
    wire [3:0]  max0, max1, max2;
    wire        grant0, grant1, grant2;
    wire        busy0, busy1, busy2;
    wire [7:0]  cfg_rdata0, cfg_rdata1, cfg_rdata2;

    monitor_ctx_rtfce u_ctx0 (
        .clk(clk), .rst_n(rst_n_int),
        .cfg_write(ctx0_cfg_write), .cfg_byte_sel(cfg_byte_sel),
        .cfg_wdata(uio_in), .cfg_rdata(cfg_rdata0),
        .event_strobe(event_strobe), .event_code(event_code),
        .pend(pend0), .latched_latency_out(lat0),
        .min_latency_out(min0), .max_latency_out(max0),
        .grant(grant0), .busy(busy0)
    );

    monitor_ctx_rtfce u_ctx1 (
        .clk(clk), .rst_n(rst_n_int),
        .cfg_write(ctx1_cfg_write), .cfg_byte_sel(cfg_byte_sel),
        .cfg_wdata(uio_in), .cfg_rdata(cfg_rdata1),
        .event_strobe(event_strobe), .event_code(event_code),
        .pend(pend1), .latched_latency_out(lat1),
        .min_latency_out(min1), .max_latency_out(max1),
        .grant(grant1), .busy(busy1)
    );

    monitor_ctx_rtfce u_ctx2 (
        .clk(clk), .rst_n(rst_n_int),
        .cfg_write(ctx2_cfg_write), .cfg_byte_sel(cfg_byte_sel),
        .cfg_wdata(uio_in), .cfg_rdata(cfg_rdata2),
        .event_strobe(event_strobe), .event_code(event_code),
        .pend(pend2), .latched_latency_out(lat2),
        .min_latency_out(min2), .max_latency_out(max2),
        .grant(grant2), .busy(busy2)
    );

    wire [1:0] arb_result_pre;
    wire       arb_result_valid_pre;
    wire [1:0] arb_context_id_pre;
    wire       classify_busy;

    classify_arbiter u_classify_arbiter (
        .clk(clk), .rst_n(rst_n_int),
        .rr_enable(rr_enable),
        .pend0(pend0), .latency0(lat0), .min0(min0), .max0(max0),
        .pend1(pend1), .latency1(lat1), .min1(min1), .max1(max1),
        .pend2(pend2), .latency2(lat2), .min2(min2), .max2(max2),
        .grant0(grant0), .grant1(grant1), .grant2(grant2),
        .result(arb_result_pre), .context_id(arb_context_id_pre),
        .result_valid(arb_result_valid_pre), .busy(classify_busy)
    );

    wire [1:0] final_result;
    wire [1:0] final_context_id;
    wire       final_result_valid;
    wire       final_busy;

    result_arbiter u_result_arbiter (
        .clk(clk), .rst_n(rst_n_int),
        .result_valid_in0(grant0), .result_code_in0(arb_result_pre),
        .result_valid_in1(grant1), .result_code_in1(arb_result_pre),
        .result_valid_in2(grant2), .result_code_in2(arb_result_pre),
        .result(final_result), .context_id(final_context_id),
        .result_valid(final_result_valid), .busy(final_busy)
    );

    reg [7:0] success_count;
    reg [7:0] fault_count;
    wire      is_timeout = (final_result == 2'b10);

    always @(posedge clk or negedge rst_n_int) begin
        if (!rst_n_int) begin
            success_count <= 8'd0;
            fault_count   <= 8'd0;
        end else if (final_result_valid) begin
            if (is_timeout) begin
                if (fault_count != 8'hFF) fault_count <= fault_count + 8'd1;
            end else begin
                if (success_count != 8'hFF) success_count <= success_count + 8'd1;
            end
        end
    end

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

    reg [7:0] cfg_rdata_reg;
    wire      cfg_read_pulse = cfg_mode & cfg_rw & strobe;
    always @(posedge clk or negedge rst_n_int) begin
        if (!rst_n_int)
            cfg_rdata_reg <= 8'h00;
        else if (cfg_read_pulse)
            cfg_rdata_reg <= cfg_rdata_mux;
    end

    assign uio_out = cfg_rdata_reg;
    assign uio_oe  = (cfg_mode & cfg_rw) ? 8'hFF : 8'h00;

    assign uo_out[1:0] = final_result;
    assign uo_out[3:2] = final_context_id;
    assign uo_out[4]   = final_result_valid;
    assign uo_out[5]   = final_busy | classify_busy | busy0 | busy1 | busy2;
    assign uo_out[6]   = final_result_valid & is_timeout;
    assign uo_out[7]   = 1'b0;

endmodule
