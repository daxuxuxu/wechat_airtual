## [AXI] Outstanding 与 Backpressure：request tracker 为什么不能只看 ready

---

### 导读

今天排查过一种很常见的现象：上游地址通道还在持续发请求，下游 response 却迟迟不回来。表面看只是 `AWREADY` 或 `ARREADY` 拉低了，真正的问题其实是 request tracker 里的 outstanding entry 已经快满了。

AXI outstanding 的核心不是“计数器加一减一”这么简单，而是要回答一件事：**这笔请求从什么时候开始占资源，到什么时候才能确定地释放资源？**

---

### 一、Outstanding 是 request 的生命周期，不是一个瞬时信号

对 bridge 或 request tracker 来说，一笔 request 在 address handshake 成功后就已经被环境接收。它可能还在等待下游服务、等待 response，或者等待最后一拍 read data。

只有 response 真正完成后，这个 entry 才能 retire。read transaction 的释放点通常是接收 `RVALID`、`RREADY` 与 `RLAST` 同时成立的最后一拍。write transaction 的释放点则是 `BVALID` 与 `BREADY` handshake。

![OT 生命周期](assets/axi-outstanding/01-ot-lifecycle.drawio)

因此，`ot_count` 描述的是“仍然需要系统负责的 request 数量”。它不是总线当前有多少 `VALID`，也不是下游当前有多少 stall。

---

### 二、Allocate 与 retire 必须分别观察

最稳妥的建模方式，是把两个事件拆开。

allocate event 来自新的 address handshake。写请求通常观察 `AWVALID && AWREADY`，读请求观察 `ARVALID && ARREADY`。

retire event 来自最终 response handshake。write 观察 `BVALID && BREADY`。read 则必须等到 `RVALID && RREADY && RLAST`，不能在第一拍 read data 到来时提前释放。

![ot_count 方程](assets/axi-outstanding/02-ot-counter.drawio)

这也是 scoreboard、reference model 和 assertion 最容易产生分歧的地方。如果一个 checker 在 read burst 第一拍就把 OT 减一，它会在长 burst 下错误地允许更多 request 进入。

---

### 三、Backpressure 的本质是保护 tracker 容量

当 `ot_count` 接近或达到 `ot_limit`，上游必须被 backpressure。对 AXI 来说，最直接的动作是把 address channel 的 `AWREADY` 或 `ARREADY` 拉低，阻止新的 request handshake。

![阈值与 backpressure](assets/axi-outstanding/03-threshold-backpressure.drawio)

这里最重要的规则是：**只阻止新的 request，不影响已经接收的 request。**

一旦 address handshake 已经成功，后续即使 tracker 接近 full，也必须继续接收对应的 write data，并最终处理 response。否则就会出现 request 被接收了一半、状态却无法完成的死锁。

---

### 四、长 response delay 最容易暴露容量与释放点错误

最有效的压力场景不是持续发送 request，而是持续发送 request 的同时故意延迟 response。

![延迟 response 导致 OT 累积](assets/axi-outstanding/04-long-response-delay.drawio)

当下游把 `BVALID` 或最后一拍 `RVALID/RLAST` 拖延时，OT 应持续累积。达到 limit 后，上游 address handshake 必须停止。response 恢复后，entry retire，ready 再逐步恢复。

如果 ready 在 response 真正 handshake 前恢复，说明 tracker 可能提前 retire。若 ready 在 response 完成后仍然不恢复，则可能存在 entry 泄漏。

---

### 五、ID 决定 response 属于谁，OT depth 决定还能收多少

`ot_count` 解决的是容量问题，ID matching 解决的是归属问题。两者不能混为一谈。

对于并发 request，bridge 或 checker 应记录每笔 request 的 type、ID 和完成状态。write address 的 `AWID`、read address 的 `ARID` 在 request 进入时建立归属；response 返回时，`BID` 或 `RID` 必须能匹配一个仍处于 outstanding 状态的 entry。

![读写 OT 与 ID 匹配](assets/axi-outstanding/05-read-write-id.drawio)

DV 中要特别覆盖不同 ID 的 response reorder、重复 ID、未知 ID response，以及同一 ID 的 request／response 顺序约束。只测试“单 ID、按顺序返回”通常不足以证明 tracker 正确。

---

### 六、同周期 allocate 与 retire，计数应看净变化

一个 cycle 内可以同时接收新 request，也可以完成旧 response。这时不能简单地先加一、再减一，或者依赖代码书写顺序。

![同周期计数保持](assets/axi-outstanding/06-same-cycle-alloc-retire.drawio)

正确语义是净变化：只有 allocate 时增加，只有 retire 时减少，同时发生时保持不变。这一条通常应该同时出现在 RTL、reference model、assertion 与 coverage 的定义中。

---

### 七、Reset 与 flush：最怕 stale response

当 reset 或 flush 到来时，仍在 tracker 中的 outstanding entry 必须被清理。之后返回的旧 response 不能再匹配到新的 request。

![reset 与 flush 验证](assets/axi-outstanding/07-reset-flush.drawio)

一个关键测试是：OT 非零时触发 reset，随后重新发起 request，再注入旧 response。checker 应把它识别为 stale response，而不是误匹配到 reset 后复用的 ID。

---

### 八、DV 验证应该抓住哪些观察点

第一，确认 full 边界。`ot_count` 从 `ot_limit - 1` 进入 `ot_limit` 时，下一笔 address request 必须被挡住。

第二，确认 response delay。延迟 write response 或 read burst 最后一拍，检查 OT 不会提前释放。

第三，确认 ID matching。不同 ID 并发、response reorder、未知 ID 与 reset 后 stale response 都应有明确 checker 行为。

第四，确认同周期净变化。alloc 与 retire 同时发生时，`ot_count`、ready 与 coverage 不能出现一个 cycle 的假波动。

第五，确认 reset／flush。所有 entry 清理后，新的 traffic 可以恢复，旧 response 不会污染新事务。

---

### 九、总结

Outstanding 的本质是 request lifecycle tracking。backpressure 的本质是保护有限 tracker capacity。ID matching 的本质是保证 response 不会归属错误。

> **判断口诀：address handshake 时 allocate，最终 response handshake 时 retire；limit 满时挡新请求，已接收请求必须走到完成。**

---

*本文以通用 AXI 与 bridge request tracker 语义整理，不依赖特定实现。*
