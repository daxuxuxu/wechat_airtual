module axi_ot_sva #(
  parameter int OT_LIMIT = 16,
  parameter int OT_COUNT_WIDTH = $clog2(OT_LIMIT + 1)
) (
  input logic                       ACLK,
  input logic                       ARESETn,
  input logic                       AWVALID,
  input logic                       AWREADY,
  input logic                       ARVALID,
  input logic                       ARREADY,
  input logic                       BVALID,
  input logic                       BREADY,
  input logic                       RVALID,
  input logic                       RREADY,
  input logic                       RLAST,
  input logic [OT_COUNT_WIDTH-1:0] ot_count
);
  logic aw_fire, ar_fire, b_fire, r_last_fire;

  assign aw_fire      = AWVALID && AWREADY;
  assign ar_fire      = ARVALID && ARREADY;
  assign b_fire       = BVALID && BREADY;
  assign r_last_fire  = RVALID && RREADY && RLAST;

  // This is a design policy assertion, not an AXI protocol requirement.
  assert property (@(posedge ACLK) disable iff (!ARESETn)
    (ot_count == OT_LIMIT) |-> !aw_fire && !ar_fire);

  assert property (@(posedge ACLK) disable iff (!ARESETn)
    ot_count <= OT_LIMIT);

  // With no entry allocated, a completed response indicates a tracking mismatch.
  assert property (@(posedge ACLK) disable iff (!ARESETn)
    (ot_count == 0) |-> !b_fire && !r_last_fire);

  // One new request and one completed request leave a saturated count unchanged.
  assert property (@(posedge ACLK) disable iff (!ARESETn)
    ((aw_fire ^ ar_fire) && (b_fire ^ r_last_fire))
      |=> ot_count == $past(ot_count));
endmodule
