# [AXI] Outstanding 与 Backpressure：DV 图解与代码

在 AXI 中，**outstanding transaction** 表示“地址已经被接收、但对应事务还没有完成”的请求。本文把它简称为 **OT**。`OT`、`ot_count`、`ot_limit` 不是 AXI 协议信号，而是设计或验证环境常用的抽象：它们用来描述有限的请求跟踪资源。

对 DV 而言，关键不是假设每个设计都用同一种 OT 表，而是抓住三个可观察事实：

1. `AWVALID && AWREADY` 或 `ARVALID && ARREADY` 成功后，设计必须继续记住这笔请求。
2. 只有对应的完成事件才能释放这份跟踪资源：写是 `BVALID && BREADY`；读是 `RVALID && RREADY && RLAST`。
3. 当跟踪资源不足时，设计可以通过 `AWREADY`、`ARREADY` 形成 backpressure，阻止**新的地址握手**；已经完成的握手不能被撤销或遗失。

## 1. Outstanding 是什么，为什么需要它

如果每发一个 AXI 请求都等待响应再发下一个，下游 latency 会直接变成带宽损失。允许多笔请求同时在途，可以让地址通道持续工作，并把等待响应的时间隐藏在后续请求之下。

从 DV 角度，最简单的计数定义是：

```text
ot_count = 已接收、尚未完成的写事务数
         + 已接收、尚未完成的读事务数
```

这一定义是一个**验证模型**，不是 AXI 对内部实现的规定。某些实现会在地址握手时分配 entry，某些实现会增加 pipeline margin 或按读写、QoS、ID 分组。验证时应以接口可见的 handshake 和设计定义的容量策略为准。

[打开图 1：OT 生命周期](assets/axi-outstanding/01-ot-lifecycle.drawio)

![图 1：OT 生命周期](assets/axi-outstanding/01-ot-lifecycle.drawio)

图 1 的核心是“allocate 后不能丢、retire 前不能提前释放”。例如，写地址已经在 `AWVALID && AWREADY` 完成握手，即使之后 `WVALID` 的数据拍还没有全部到达，地址请求已经是一个需要持续追踪的对象。反过来，所有 `W` 数据拍传完也不等于写事务已经完成；对于本文的 OT 计数模型，必须等 `BVALID && BREADY` 的 write response handshake 才能 retire。

## 2. AXI 中何时分配、何时释放 OT

建议在 monitor 中把四个事件显式命名：

```systemverilog
aw_fire     = AWVALID && AWREADY;
ar_fire     = ARVALID && ARREADY;
b_fire      = BVALID  && BREADY;
r_last_fire = RVALID  && RREADY && RLAST;
```

写事务的 alloc 通常由 `aw_fire` 驱动，retire 由 `b_fire` 驱动。读事务的 alloc 通常由 `ar_fire` 驱动，retire 必须由 `r_last_fire` 驱动。读 burst 中每个 beat 都可能有 `RVALID && RREADY`，但只有带 `RLAST=1` 的最后一拍表示这一笔 read transaction 已完成。

[打开图 2：计数方程](assets/axi-outstanding/02-ot-counter.drawio)

![图 2：ot_count 方程](assets/axi-outstanding/02-ot-counter.drawio)

用于 scoreboard 的最小模型如下。它把读、写按 ID 分开计数，因此可以捕获“response 的 ID 没有对应 request”或“同一个 response 被重复 retire”两类常见问题。

```systemverilog
class axi_ot_reference_model #(int ID_WIDTH = 4, int OT_LIMIT = 16);
  typedef bit [ID_WIDTH-1:0] axi_id_t;
  int unsigned write_ot[axi_id_t];
  int unsigned read_ot[axi_id_t];
  int unsigned ot_count;

  function bit can_accept();
    return ot_count < OT_LIMIT;
  endfunction

  function void write_accept(axi_id_t awid);
    if (!can_accept()) $error("AW accepted while OT is full");
    else begin write_ot[awid]++; ot_count++; end
  endfunction

  function void write_retire(axi_id_t bid);
    if (!write_ot.exists(bid) || write_ot[bid] == 0)
      $error("BID has no matching AWID");
    else begin write_ot[bid]--; ot_count--; end
  endfunction
endclass
```

完整示例同时覆盖 `ARID`/`RID`、reset 和 invariant 检查：[`axi_ot_reference_model.sv`](snippets/axi_ot_reference_model.sv)。

## 3. `ot_count` 与 `ot_limit`：回压怎样产生

AXI 的 `VALID/READY` 握手机制允许 receiver 通过拉低 `READY` 延后接收新传输。若一个设计的 OT 资源有限，可以在资源满时拉低 `AWREADY`、`ARREADY`，让 address channel 停在当前未完成的传输上。这是设计的资源管理策略，不是协议要求所有 slave 都必须采用的固定阈值。

`OT_LIMIT` 的边界最容易出错：

- `ot_count == OT_LIMIT - 1`：下一笔允许接收的地址会占用最后一个 entry。
- `ot_count == OT_LIMIT`：不应再发生新的 `AW` 或 `AR` handshake。
- 一个 response retire 后：若资源已重新可用，地址通道应按设计策略恢复。

[打开图 3：阈值与回压](assets/axi-outstanding/03-threshold-backpressure.drawio)

![图 3：阈值与 backpressure](assets/axi-outstanding/03-threshold-backpressure.drawio)

注意 `AWVALID` 或 `ARVALID` 可以在 `READY=0` 时保持为 1。DV 不应该把“看到 VALID”误判成请求已经被接收；唯一的接收时刻是 `VALID && READY`。同样，backpressure 只影响之后的 handshake，不能取消之前已成功的 `AW` 或 `AR` handshake。

一个设计策略断言可以写成：

```systemverilog
assert property (@(posedge ACLK) disable iff (!ARESETn)
  (ot_count == OT_LIMIT) |-> !(AWVALID && AWREADY) &&
                            !(ARVALID && ARREADY));
```

这条 property 检查“OT 满时不接收新地址”。它是本设计的资源策略检查，不应被解释为 AXI 标准对每个接口的统一要求。

完整 assertions：[`axi_ot_sva.sv`](snippets/axi_ot_sva.sv)。

## 4. 长时间 backpressure：已经接收的请求不能丢

最有价值的压力场景不是只让 `AWREADY` 或 `ARREADY` 偶尔拉低，而是让 response 长时间延迟：例如连续接收多个 `AW`/`AR`，但暂时不产生 `BVALID` 或最后一个 `RVALID && RLAST`。这时 `ot_count` 持续上升，最终触及 `OT_LIMIT`。

[打开图 4：延迟响应时序](assets/axi-outstanding/04-long-response-delay.drawio)

![图 4：延迟响应导致 OT 累积](assets/axi-outstanding/04-long-response-delay.drawio)

该场景至少检查五件事：

1. 每一次 `AW`/`AR` handshake 都准确增加一次 OT。
2. response 未完成前，计数不能减少。
3. 到达 limit 后，不再接受新的地址 handshake。
4. upstream 仍保持 `AWVALID`/`ARVALID` 时，不能重复计算同一笔未握手请求。
5. 一个 `B` 或最后一个 `R` handshake 释放资源后，接口能恢复接收能力。

延迟 response 激励的通用片段如下。接口类型仅为示意，替换成 testbench 自己的 virtual interface 类型即可。

```systemverilog
task automatic send_b_after_delay(
  virtual axi_slave_vif vif,
  bit [ID_WIDTH-1:0] bid,
  int unsigned delay_cycles
);
  repeat (delay_cycles) @(posedge vif.ACLK);
  vif.BID    <= bid;
  vif.BRESP  <= 2'b00;
  vif.BVALID <= 1'b1;
  do @(posedge vif.ACLK); while (!vif.BREADY);
  vif.BVALID <= 1'b0;
endtask
```

完整 read/write 延迟 response 示例：[`axi_ot_delayed_response_seq.svh`](snippets/axi_ot_delayed_response_seq.svh)。

## 5. 读、写、ID 与乱序响应

读和写是独立的 AXI 通道，DV model 最好也把它们分开 tracking。写地址从 `AWID` 分配，写 response 用 `BID` retire；读地址从 `ARID` 分配，读 response 用 `RID` retire。

不同 ID 的事务可以以不同顺序完成，因此 checker 不能把全部 response 当成一个全局 FIFO。另一方面，验证仍需遵守适用 AXI 版本对同 ID 顺序与 read data burst 行为的规则。对于本文的“事务完成”计数，读 burst 只有在对应 `RID` 的 `RVALID && RREADY && RLAST` 发生时才释放一个 read OT。

[打开图 5：读写与 ID 匹配](assets/axi-outstanding/05-read-write-id.drawio)

![图 5：读写 OT 与 ID 匹配](assets/axi-outstanding/05-read-write-id.drawio)

一个监控器的顺序可以是：在同一采样边沿先处理 `B`/最后一拍 `R` 的 retire，再处理 `AW`/`AR` 的 alloc。这样在“OT 满但同周期恰好有一个 response 完成”的设计中，模型能表达同周期前进。关键不是这一种顺序永远正确，而是 monitor、scoreboard 与 RTL 的采样语义必须一致。

```systemverilog
if (vif.BVALID && vif.BREADY)
  model.write_retire(vif.BID);
if (vif.RVALID && vif.RREADY && vif.RLAST)
  model.read_retire(vif.RID);
if (vif.AWVALID && vif.AWREADY)
  model.write_accept(vif.AWID);
if (vif.ARVALID && vif.ARREADY)
  model.read_accept(vif.ARID);
```

完整 checker：[`axi_ot_checker.svh`](snippets/axi_ot_checker.svh)。

## 6. 同周期 alloc/retire 与 reset/flush

同一时钟边沿可能既有新地址被接收，也有旧事务完成。若刚好一个 alloc 和一个 retire，理想的计数关系是：

```text
ot_count_next = ot_count + 1 - 1 = ot_count
```

这个 corner case 常暴露两类 bug：计数器写入优先级错误，或 checker 分别在两个地方更新而漏掉其中一个事件。

[打开图 6：同周期 alloc/retire](assets/axi-outstanding/06-same-cycle-alloc-retire.drawio)

![图 6：同周期计数保持](assets/axi-outstanding/06-same-cycle-alloc-retire.drawio)

reset 与 flush 需要分开看待。`ARESETn=0` 是 AXI 接口 reset 的可观察条件；内部 tracking 在 reset 时如何清除，应按设计 reset 规格检查。flush 通常不是 AXI 的固定通道语义，其含义可能是等待未完成请求 drain、禁止新请求、丢弃特定上下文，或执行其他已定义策略。DV 的目标不是猜测 flush 应该怎么做，而是把设计声明的策略写成可检查的 expected behavior。

[打开图 7：reset/flush 收敛](assets/axi-outstanding/07-reset-flush.drawio)

![图 7：reset/flush 验证](assets/axi-outstanding/07-reset-flush.drawio)

最小检查包括：

- reset 后 `ot_count` 回到已定义的初始状态，通常为 0；
- reset/flush 之后不会收到可与旧 entry 错配的 `BID`/`RID`；
- 重新开始 traffic 后，新请求不会被旧 ID 或旧计数污染；
- 若 flush 定义为 drain，则 idle 条件必须等所有要求的 response 完成；若定义为 cancel，则取消时刻和可见响应必须符合规格。

## 7. DV 配方：激励、检查与 coverage

| 风险 | 激励 | 检查 | coverage |
| --- | --- | --- | --- |
| OT full 边界 | 连续发送 `AW` 或 `AR` 至 `OT_LIMIT` | full 后没有新的 address handshake | `ot_count`：`OT_LIMIT-1` → `OT_LIMIT` |
| 长 response delay | 延迟 `BVALID` 或最后一拍 `RVALID/RLAST` | 无提前 retire；response 后恢复接收 | delay 长度 × request type × depth |
| 错配 `BID`/`RID` | 发送不存在或已完成的 ID | checker 报 unmatched response | ID × read/write × response 顺序 |
| 同周期事件 | 同时发新地址并完成旧 response | `ot_count` 按净变化更新 | alloc/retire 组合 |
| reset/flush | OT 非零时拉低 `ARESETn` 或触发 flush | 无 entry 泄漏、无 stale response 匹配 | event 时的 depth × type |

coverage 不应只覆盖“是否到过 full”，还要覆盖到达 full 的路径。例如先累积 read、先累积 write、读写混合、response 长延迟、以及 full 状态下 upstream 持续保持 `AWVALID`/`ARVALID` 都可能触发不同 corner case。

```systemverilog
covergroup ot_cg @(posedge ACLK);
  cp_depth: coverpoint ot_count {
    bins empty    = {0};
    bins one_left = {OT_LIMIT - 1};
    bins full     = {OT_LIMIT};
  }
  cp_request: coverpoint {aw_fire, ar_fire} {
    bins write = {2'b10};
    bins read  = {2'b01};
    bins both  = {2'b11};
  }
  x_depth_request: cross cp_depth, cp_request;
endgroup
```

完整 coverage：[`axi_ot_coverage.sv`](snippets/axi_ot_coverage.sv)。

## 8. Debug checklist

遇到 OT overflow、unexpected backpressure 或 response mismatch 时，按下列顺序观察会比先盯计数器更有效：

1. 找出每一个 `AWVALID && AWREADY` 与 `ARVALID && ARREADY`，确认 request 是否真的被接收。
2. 找出匹配的 `BVALID && BREADY` 与 `RVALID && RREADY && RLAST`，确认事务何时真正完成。
3. 逐周期比较 `alloc`、`retire` 与 `ot_count` 的差分。
4. 确认 `AWREADY`/`ARREADY` 第一次被拉低的时刻是否正好符合资源策略。
5. 在 response retire 后确认接口是否按预期恢复，不会永久 backpressure。
6. 最后检查 response 类型与 ID 匹配；很多“计数错”其实是 `BID`/`RID` 匹配或 `RLAST` 判断错误。

## 9. 产物索引

- [OT reference model](snippets/axi_ot_reference_model.sv)
- [Delayed response stimulus](snippets/axi_ot_delayed_response_seq.svh)
- [Monitor/checker](snippets/axi_ot_checker.svh)
- [SVA](snippets/axi_ot_sva.sv)
- [Functional coverage](snippets/axi_ot_coverage.sv)
- [全部可编辑 draw.io 图](assets/axi-outstanding/)
