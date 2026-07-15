// Replace axi_slave_vif with the virtual interface type used by the testbench.
class axi_ot_delayed_response_seq #(int ID_WIDTH = 4, int DATA_WIDTH = 32);
  typedef bit [ID_WIDTH-1:0] axi_id_t;
  typedef bit [DATA_WIDTH-1:0] axi_data_t;

  task automatic send_b_after_delay(
    virtual axi_slave_vif vif,
    axi_id_t bid,
    int unsigned delay_cycles
  );
    repeat (delay_cycles) @(posedge vif.ACLK);

    vif.BID    <= bid;
    vif.BRESP  <= 2'b00;
    vif.BVALID <= 1'b1;
    do @(posedge vif.ACLK); while (!vif.BREADY);
    vif.BVALID <= 1'b0;
  endtask

  task automatic send_r_burst_after_delay(
    virtual axi_slave_vif vif,
    axi_id_t rid,
    int unsigned beats,
    int unsigned delay_cycles
  );
    repeat (delay_cycles) @(posedge vif.ACLK);

    for (int unsigned beat = 0; beat < beats; beat++) begin
      vif.RID    <= rid;
      vif.RDATA  <= axi_data_t'(beat);
      vif.RRESP  <= 2'b00;
      vif.RLAST  <= (beat == beats - 1);
      vif.RVALID <= 1'b1;
      do @(posedge vif.ACLK); while (!vif.RREADY);
    end
    vif.RVALID <= 1'b0;
    vif.RLAST  <= 1'b0;
  endtask

  task automatic delay_response_randomly(
    virtual axi_slave_vif vif,
    axi_id_t id,
    bit is_write,
    int unsigned max_delay
  );
    int unsigned delay_cycles = $urandom_range(max_delay, 0);
    if (is_write)
      send_b_after_delay(vif, id, delay_cycles);
    else
      send_r_burst_after_delay(vif, id, 4, delay_cycles);
  endtask
endclass
