## [PCIe] Completion 机制：Memory Read 发出后，Completion 怎样找到原始 Request

![封面](cover_pcie_completion.png)

---

### 导读

本文介绍 Requester ID、Tag、Byte Count、Lower Address 与 completion split。

---

### 前置概念速查

Memory Read 是 Non-Posted Request。Requester 发送 MRd 后必须等待 Completion。Requester ID 与 Tag 用于把 Completion 匹配回原始 Request。

![机制流程](pcie_completion-flow.png)

---

### 一、为什么一笔 Read 不一定只返回一笔 Completion

read request 可能因为 payload boundary、target response 或 implementation 约束被拆成多个 Completion with Data。Requester 必须按 Tag、Byte Count、Lower Address 与 data ordering 重新组装。

---

### 二、Tag 是 request 的身份凭证

同一个 Requester 可以同时发出多笔 MRd。Tag 让多个 outstanding read 可以并发，Completion 返回时才能准确找到等待它的 request entry。

---

### 三、DV 应覆盖什么

覆盖 completion split、out-of-order completion、unknown Tag、duplicate completion、Completion Timeout、reset 后 stale completion 与 tag reuse。

---

### 总结

PCIe Function 相关能力的难点，不只是 capability bit，而是 capability、control、transaction state 与 reset/error path 是否一致。
