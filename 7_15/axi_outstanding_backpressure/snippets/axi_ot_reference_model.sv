// Generic verification model; OT is an implementation abstraction, not an AXI signal.
class axi_ot_reference_model #(int ID_WIDTH = 4, int OT_LIMIT = 16);
  typedef bit [ID_WIDTH-1:0] axi_id_t;

  int unsigned write_ot[axi_id_t];
  int unsigned read_ot[axi_id_t];
  int unsigned ot_count;

  function new();
    reset();
  endfunction

  function void reset();
    write_ot.delete();
    read_ot.delete();
    ot_count = 0;
  endfunction

  function bit can_accept();
    return ot_count < OT_LIMIT;
  endfunction

  function void check_invariants(string where);
    if (ot_count > OT_LIMIT)
      $error("%s: ot_count=%0d exceeds OT_LIMIT=%0d", where, ot_count, OT_LIMIT);
  endfunction

  function void write_accept(axi_id_t awid);
    if (!can_accept()) begin
      $error("AW accepted while ot_count=%0d is full", ot_count);
      return;
    end
    write_ot[awid]++;
    ot_count++;
    check_invariants("write_accept");
  endfunction

  function void read_accept(axi_id_t arid);
    if (!can_accept()) begin
      $error("AR accepted while ot_count=%0d is full", ot_count);
      return;
    end
    read_ot[arid]++;
    ot_count++;
    check_invariants("read_accept");
  endfunction

  function void write_retire(axi_id_t bid);
    if (!write_ot.exists(bid) || write_ot[bid] == 0) begin
      $error("BID=%0h has no unmatched AWID", bid);
      return;
    end
    write_ot[bid]--;
    ot_count--;
    check_invariants("write_retire");
  endfunction

  function void read_retire(axi_id_t rid);
    if (!read_ot.exists(rid) || read_ot[rid] == 0) begin
      $error("RID=%0h has no unmatched ARID", rid);
      return;
    end
    read_ot[rid]--;
    ot_count--;
    check_invariants("read_retire");
  endfunction

  function int unsigned outstanding_for_id(axi_id_t id, bit is_write);
    return is_write ? write_ot[id] : read_ot[id];
  endfunction
endclass
