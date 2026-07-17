## [PCIe] Power Management：D0、D3hot、D3cold 怎样影响 Function 行为

![封面](cover_pcie_power_management.png)

---

### 导读

本文介绍 Function power state、configuration 与 request visibility。

---

### 前置概念速查

PCIe power state 描述 Function 的可用程度。D0 通常表示 active state，D3hot 与 D3cold 表示更深的低功耗状态。

![机制流程](pcie_power_management-flow.png)

---

### 一、Power transition 不只是省电

Function 进入低功耗状态后，memory request、interrupt、configuration behavior 和 software visibility 都可能变化。power state transition 必须有明确的 quiesce 与 restore 规则。

---

### 二、Power state 与 reset 的区别

reset 关注 state initialization。power management 关注 activity reduction 与恢复。两者可能组合出现，但不能把一种语义当作另一种。

---

### 三、DV 应覆盖什么

覆盖 D-state transition、memory decode、MSI/MSI-X、PME、in-flight request、wake up、restore sequence 与 error path。

### 四、Power transition 的关键是 quiesce

进入低功耗状态前，Function 必须对新 request 建立明确的处理规则，并处理已经开始的 transaction。否则 transition 后可能留下 outstanding entry、未完成 DMA、pending interrupt 或不可恢复的 completion state。

恢复时也不能只把 power state 改回 active。需要确认 configuration、BAR decode、interrupt、queue 和 datapath 何时重新可用。

![Power transition 伪代码](pcie_power_management-pseudocode.png)

### 五、DV 的观察点

除了检查最终 power state，还应检查 transition 窗口。特别是 memory request、MSI-X、error event 与 FLR 同时发生时，设计是否能避免 deadlock、stale state 与重复上报。

---

### 总结

PCIe Function 相关能力的难点，不只是 capability bit，而是 capability、control、transaction state 与 reset/error path 是否一致。
