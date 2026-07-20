## [PCIe] SR-IOV 与 SIOV：从 VF 到 Scalable Device Interface

![封面](cover_pcie_sriov_siov.png)

---

### 导读

SR-IOV 让一块 PCIe device 通过 PF 与 VF 向多个 VM 提供接近原生的 I/O 能力。但当虚拟接口数量继续增加时，每个 VF 都拥有独立 Configuration Space、BAR、MSI-X 等硬件状态，会让实现规模和软件枚举成本变高。

SIOV 的目标不是否定 SR-IOV，而是把虚拟化接口做得更轻量、更可扩展。

---

### 前置概念速查

PF 是管理 physical device 的 Function。VF 是 SR-IOV 中由 PF 创建的 Virtual Function，VF 对 software 看起来像独立 PCIe Function。

SIOV 使用 Scalable Device Interface，SDI，表示轻量级虚拟 device interface。它的目标是减少每个虚拟接口都复制完整 PCIe Function 状态的成本。

两者共同解决的是 I/O virtualization，但 software model、硬件状态和 scalability 取舍不同。

![SR-IOV 与 SIOV 的虚拟接口模型](sriov-siov-architecture.png)

---

### 一、SR-IOV：每个 VF 都像一个 PCIe Function

SR-IOV 的优势是 software 模型成熟。PF 负责 VF enable、resource provisioning 和管理面控制；每个 VF 有独立 identity、configuration view、BAR slice 和 interrupt resource。

这种模型容易被现有 hypervisor、driver 和 VM 理解，因为 VF 的行为接近普通 PCIe Function。

代价是每增加一个 VF，硬件往往需要维护更多 per-VF state。对于需要非常大量虚拟接口的 device，这种复制成本会成为 scalability 限制。

---

### 二、SIOV：把虚拟接口变得更轻

SIOV 的核心思路是使用 SDI 作为虚拟接口，而不是让每个接口都复制成完整传统 PCIe Function。

更多 control plane 工作由 virtualization software 与 PF 配合完成，device 更专注于高频 data path 的 context selection、request routing 和 resource isolation。

这使 SIOV 更适合大规模 virtualization 场景。但它也要求 software、IOMMU 和 device 对 interface identity、context 和 page-level resource 管理有更紧密的协作。

---

### 三、两者的核心差异

![SR-IOV 与 SIOV：核心差异](sriov-siov-compare.png)

SR-IOV 侧重“虚拟接口像真实 Function”。SIOV 侧重“虚拟接口足够轻量，能扩展到更多 context”。

这不是简单的新旧替换关系。选择哪种方式取决于 software ecosystem、virtual interface 数量、hardware state cost、interrupt model 与 address translation 需求。

---

### 四、DV 中最重要的不是枚举，而是隔离

SR-IOV 验证通常重点检查 VF enable、BDF／Routing ID、BAR slice、MSI-X、FLR 和 PF/VF isolation。

SIOV 验证则更强调 interface identity、context mapping、resource isolation、request route、translation state 与 software-managed control plane。

无论是哪种模型，核心问题都是同一个：一个 virtual interface 的 request、interrupt、memory access 或 error state 不能泄漏到另一个 interface。

![SR-IOV / SIOV DV checker 伪代码](sriov-siov-dv.png)

---

### 五、验证场景建议

覆盖 interface enable／disable、并发 request、resource quota、reset／FLR、interrupt isolation 和 error recovery。

对 SR-IOV，重点观察 PF 配置改变后 VF visibility 与 BAR route 是否同步变化。

对 SIOV，重点观察相同 address、不同 interface context 是否被正确隔离，以及 context invalidation、retry 或 reset 后的 state cleanup。

---

### 六、总结

SR-IOV 用完整 VF 提供成熟的软件兼容性。SIOV 用轻量 SDI 面向更大规模的虚拟接口。

> **SR-IOV 强调“像一个 Function”，SIOV 强调“像一个可扩展 context”。**

---

*本文根据 PCI-SIG 公开的 SIOV 概念资料与通用 PCIe 虚拟化验证方法整理。*
