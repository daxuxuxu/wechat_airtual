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

---

### 总结

PCIe Function 相关能力的难点，不只是 capability bit，而是 capability、control、transaction state 与 reset/error path 是否一致。
