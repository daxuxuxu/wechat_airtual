// The checker samples only completed AXI handshakes.
class axi_ot_checker #(int ID_WIDTH = 4, int OT_LIMIT = 16);
  typedef bit [ID_WIDTH-1:0] axi_id_t;

  axi_ot_reference_model #(ID_WIDTH, OT_LIMIT) model;

  function new();
    model = new();
  endfunction

  task automatic sample_cycle(virtual axi_monitor_vif vif);
    @(posedge vif.ACLK);

    if (!vif.ARESETn) begin
      model.reset();
      return;
    end

    // Retire before allocate so a full table may make forward progress.
    if (vif.BVALID && vif.BREADY)
      model.write_retire(axi_id_t'(vif.BID));

    if (vif.RVALID && vif.RREADY && vif.RLAST)
      model.read_retire(axi_id_t'(vif.RID));

    if (vif.AWVALID && vif.AWREADY)
      model.write_accept(axi_id_t'(vif.AWID));

    if (vif.ARVALID && vif.ARREADY)
      model.read_accept(axi_id_t'(vif.ARID));
  endtask

  function void check_ready_policy(
    bit awvalid,
    bit awready,
    bit arvalid,
    bit arready
  );
    if (model.ot_count >= OT_LIMIT) begin
      if (awvalid && awready)
        $error("AW handshake occurred with no available OT entry");
      if (arvalid && arready)
        $error("AR handshake occurred with no available OT entry");
    end
  endfunction

  function int unsigned outstanding_count();
    return model.ot_count;
  endfunction
endclass
