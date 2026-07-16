## [PCIe] ATS、PASID 与 PRI：设备怎样访问进程级虚拟地址空间

![封面](cover_pcie_ats_pasid_pri.png)

---

### 导读

本文介绍 translation、address space identity 与 page request。

---

### 前置概念速查

ATS 让 device 请求 address translation。PASID 用于标识 process address space。PRI 用于在 translation 缺失时发起 page request。

![机制流程](pcie_ats_pasid_pri-flow.png)

---

### 一、为什么 device 需要虚拟地址语义

高性能 accelerator 或 DMA engine 需要与 software process 的地址空间协作。仅使用固定 physical address 会限制隔离、共享与虚拟化能力。

---

### 二、三个能力如何配合

PASID 先说明请求属于哪个 address space。ATS 用于获取 translation。PRI 在 page 不存在或 translation 无法完成时通知 software 处理。

---

### 三、DV 应覆盖什么

覆盖 capability enable、PASID matching、translation hit/miss、invalidations、page request、retry、reset/FLR 与 error reporting。

---

### 总结

PCIe Function 相关能力的难点，不只是 capability bit，而是 capability、control、transaction state 与 reset/error path 是否一致。
