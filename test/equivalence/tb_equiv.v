`default_nettype none
`timescale 1ns / 1ps

// Instantiates BOTH baseline (tt_um_rtfce_baseline) and optimized (rtfce_top)
// designs, driven by the SAME shared input pins, with separate output
// pins for each -- so a single testbench can compare their behavior
// cycle-by-cycle against identical stimulus (spec section 39).

module tb_equiv ();
  initial begin
    $dumpfile("tb_equiv.fst");
    $dumpvars(0, tb_equiv);
    #1;
  end

  reg clk;
  reg rst_n;
  reg ena;
  reg [7:0] ui_in;
  reg [7:0] uio_in;

  wire [7:0] uo_out_baseline;
  wire [7:0] uio_out_baseline;
  wire [7:0] uio_oe_baseline;

  wire [7:0] uo_out_rtfce;
  wire [7:0] uio_out_rtfce;
  wire [7:0] uio_oe_rtfce;

  tt_um_rtfce_baseline dut_baseline (
      .ui_in  (ui_in),
      .uo_out (uo_out_baseline),
      .uio_in (uio_in),
      .uio_out(uio_out_baseline),
      .uio_oe (uio_oe_baseline),
      .ena    (ena),
      .clk    (clk),
      .rst_n  (rst_n)
  );

  rtfce_top dut_rtfce (
      .ui_in  (ui_in),
      .uo_out (uo_out_rtfce),
      .uio_in (uio_in),
      .uio_out(uio_out_rtfce),
      .uio_oe (uio_oe_rtfce),
      .ena    (ena),
      .clk    (clk),
      .rst_n  (rst_n)
  );

endmodule
