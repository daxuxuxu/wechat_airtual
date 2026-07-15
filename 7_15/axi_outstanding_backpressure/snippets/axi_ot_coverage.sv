module axi_ot_coverage #(
  parameter int OT_LIMIT = 16,
  parameter int ID_WIDTH = 4,
  parameter int OT_COUNT_WIDTH = $clog2(OT_LIMIT + 1)
) (
  input logic                       ACLK,
  input logic                       ARESETn,
  input logic                       AWVALID,
  input logic                       AWREADY,
  input logic [ID_WIDTH-1:0]        AWID,
  input logic                       ARVALID,
  input logic                       ARREADY,
  input logic [ID_WIDTH-1:0]        ARID,
  input logic                       BVALID,
  input logic                       BREADY,
  input logic                       RVALID,
  input logic                       RREADY,
  input logic                       RLAST,
  input logic [OT_COUNT_WIDTH-1:0] ot_count
);
  logic aw_fire, ar_fire, b_fire, r_last_fire;
  int unsigned backpressure_cycles;

  assign aw_fire     = AWVALID && AWREADY;
  assign ar_fire     = ARVALID && ARREADY;
  assign b_fire      = BVALID && BREADY;
  assign r_last_fire = RVALID && RREADY && RLAST;

  always_ff @(posedge ACLK or negedge ARESETn) begin
    if (!ARESETn)
      backpressure_cycles <= 0;
    else if ((AWVALID && !AWREADY) || (ARVALID && !ARREADY))
      backpressure_cycles <= backpressure_cycles + 1;
    else
      backpressure_cycles <= 0;
  end

  covergroup ot_cg @(posedge ACLK);
    option.per_instance = 1;
    cp_depth: coverpoint ot_count iff (ARESETn) {
      bins empty     = {0};
      bins one_left  = {OT_LIMIT - 1};
      bins full      = {OT_LIMIT};
    }
    cp_request: coverpoint {aw_fire, ar_fire} iff (ARESETn) {
      bins write = {2'b10};
      bins read  = {2'b01};
      bins both  = {2'b11};
    }
    cp_retire: coverpoint {b_fire, r_last_fire} iff (ARESETn) {
      bins write = {2'b10};
      bins read  = {2'b01};
      bins both  = {2'b11};
    }
    cp_id: coverpoint (aw_fire ? AWID : ARID) iff (aw_fire || ar_fire);
    cp_backpressure: coverpoint backpressure_cycles {
      bins one_cycle = {1};
      bins short     = {[2:4]};
      bins long      = {[5:$]};
    }
    x_depth_request: cross cp_depth, cp_request;
  endgroup

  ot_cg cg = new();
endmodule
