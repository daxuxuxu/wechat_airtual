## [PCIe] Ordering Rules：Relaxed Ordering 为什么会改变请求完成顺序

![封面](cover_pcie_ordering.png)

---

### 导读

性能优化常常要求 transaction 能并发甚至完成顺序变化，但软件和硬件又依赖某些关键顺序。Ordering Rules 就是在吞吐与可观察顺序之间划边界。

本文从 transaction attribute、ordering domain 与 bridge state 保存出发，解释 Relaxed Ordering 为什么会改变完成顺序，又为什么不能变成任意乱序。

---

### 前置概念速查

PCIe transaction 不一定严格按发出顺序完成。ordering rule 定义不同 request 之间哪些先后关系必须保留，哪些可以为了性能被放宽。

![机制流程](pcie_ordering-flow.png)

---

### 一、为什么 PCIe 需要 Ordering Rules

PCIe 是 packet-based fabric，不是一根所有 device 共享、严格排队的总线。不同 request 可能走向不同 target，经过不同 bridge buffer，或等待不同类型的 response。

如果所有 transaction 都严格按发出顺序执行，最快的 request 也必须等待最慢的 request，吞吐会迅速下降。Ordering Rules 的作用是划出边界：哪些先后关系是 software 可观察、必须保护的；哪些 request 没有依赖，可以为了性能并发或重排。

### 二、默认／严格顺序与 Relaxed Ordering

工程上常说的 **strict ordering**，通常指 PCIe 默认 ordering rule 要求保留的可观察先后关系，而不是一个独立的 TLP attribute。

当 transaction 没有声明 `Relaxed Ordering` 时，fabric 不能为了性能随意让后发 request 越过前发 request，特别是当两个 request 存在相同 address、读写依赖、同一 requester ordering domain 或 software 可观察的先后关系时。doorbell、descriptor publish、state update 都属于需要谨慎保护的场景。

`Relaxed Ordering` 是 transaction attribute。它允许没有依赖关系的 request 绕开长延迟或拥塞，提高并发吞吐，但不意味着任意乱序。request identity、address decode、Completion matching、data integrity、Function isolation 和必须保留的 dependency 仍然不能被破坏。

可以把两者理解为：**默认 ordering 优先保护先后关系；Relaxed Ordering 优先提高并发效率，但不得破坏必要 dependency。**

### 三、bridge 与 request tracker 为什么必须保存 attribute

bridge、switch 或 request tracker 若只保存 address、ID、tag，却丢失 transaction attribute，可能把本可重排的 request 错误串行化，也可能把必须保持顺序的 request 错误重排。

这类 bug 往往只在高并发、不同 latency target 或 completion reorder 场景出现。它表面像性能问题，实质可能已经破坏 software 对状态更新顺序的假设。

![Ordering attribute 伪代码](pcie_ordering-pseudocode.png)

### 四、DV 应如何验证

让多个 requester 同时对不同 address 发 request，再混入同 address 的 read/write。分别比较 default ordering 与 Relaxed Ordering path，确认 attribute 全程保持，且 completion 返回顺序符合允许范围。

scoreboard 不应默认使用单一 FIFO 来匹配所有 response。对于允许 reorder 的路径，应以 Requester ID、Tag、address range 和 transaction attribute 建立 request entry；对于不可重排的 dependency chain，则保留严格顺序 reference path。

覆盖 attribute preserve、same address read/write、different requester、completion reorder、reset 前后 ordering state 和 Relaxed Ordering enable/disable。

---

### 总结

Ordering 的验证重点不是要求所有 request 都按顺序完成，而是证明每一笔 request 的 attribute 被保留，只有协议允许的路径发生 reorder，不允许的 dependency 从未被打破。
