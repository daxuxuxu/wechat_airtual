# PCIe Function 层级详解

## PF 与 VF 的关系、SR-IOV 与 MF-IOV 的异同

*芯片验证 · PCIe · 虚拟化*

---

> **前置概念速查**
>
> - **PCIe EP**（Endpoint）：挂在 PCIe 链路末端的设备，如 GPU、网卡、NVMe 控制器
> - **BDF**：Bus:Device:Function，PCIe 的三级寻址，唯一标识总线上的一个 Function
> - **Config Space**：每个 Function 独立拥有的配置空间，软件通过 BDF 访问
> - **Hypervisor / VM**：虚拟化场景下的宿主软件与虚拟机

---

**读完本文，你将理解**：

- PCIe 里 Function 是什么，为什么它是软件交互的最小粒度
- PF 和 VF 各自的职责，以及它们之间的从属关系
- SR-IOV 的标准工作流程
- MF-IOV 与 SR-IOV 的核心区别：重映射 vs 原生 VF
- 验证环境中如何建模这套层级关系

---

**摘要**：在 PCIe 设备虚拟化领域，PF 和 VF 是绕不开的两个概念。PF 是真实存在于硬件上的功能单元，而 VF 是由 PF 派生出的轻量级虚拟功能——它有独立的配置空间和 BAR，但共享 PF 的物理资源。实现这一派生关系的机制有两种：业界标准的 SR-IOV，以及更激进的 MF-IOV。理解它们的设计逻辑，是理解现代多功能 PCIe 设备行为的基础。

---

## 零、从一个设备说起：Function 是什么

PCIe 用 **BDF（Bus:Device:Function）** 三元组唯一标识总线上的一个逻辑单元。其中 Function 是软件实际交互的最小粒度——每个 Function 有独立的配置空间、BAR（Base Address Register）、中断向量，以及独立的读写权限控制。

一个物理 PCIe 设备可以暴露多个 Function，操作系统看到的是这些 Function，而不是"物理卡"本身。这种抽象让一张物理网卡可以同时被多个虚拟机独占使用。

```
PCIe 总线上的视图（OS/Hypervisor 视角）
──────────────────────────────────────────────────
BDF: [Bus 01] [Dev 00] [Func 0]  ← PF0   (物理功能)
BDF: [Bus 01] [Dev 00] [Func 1]  ← PF1   (物理功能)
BDF: [Bus 01] [Dev 00] [Func 2]  ← VF0   (虚拟功能，PF0 派生)
BDF: [Bus 01] [Dev 00] [Func 3]  ← VF1   (虚拟功能，PF0 派生)
BDF: [Bus 01] [Dev 00] [Func 4]  ← VF2   (虚拟功能，PF0 派生)
──────────────────────────────────────────────────
每个 Function 有独立的 Config Space 和 BAR 空间
软件通过 BDF 寻址，感知不到"它们其实共用一块硅"
```

---

## 一、PF（Physical Function）

PF 是设备上真正具备完整硬件资源的功能单元，是一切虚拟化的起点。

**PF 的核心能力**：PF 拥有完整的配置空间，包含 SR-IOV Extended Capability，通过写寄存器控制 VF 的创建数量和使能状态。PF 负责设备的初始化、资源分配、驱动加载和复位控制。

- 拥有完整的 PCIe 配置空间（含 Capabilities 链表）
- 拥有自己的 BAR 空间（MMIO 寄存器、framebuffer 等）
- 负责派生和管理 VF：控制 VF 数量、VF 使能、VF 复位
- 驱动运行在 Host 或 Hypervisor 层，对整个设备有完整控制权

**PF 的关键寄存器字段**：

| 寄存器字段 | 含义 |
|---|---|
| `SRIOV_VF_ENABLE` | 置 1 后 VF 开始对外可见 |
| `SRIOV_NUM_VFS` | 当前实际创建的 VF 数量（不超过硬件上限） |
| `SRIOV_FIRST_VF_OFFSET` | 第一个 VF 相对于 PF 的 Routing ID 偏移 |
| `SRIOV_VF_STRIDE` | 相邻 VF 之间的 Routing ID 步长 |
| `Mem Access Enable` | 控制该 Function 的 BAR 内存访问是否使能 |

---

## 二、VF（Virtual Function）

VF 是由 PF 派生出的轻量级功能单元。它有独立的配置空间和 BAR，但**不拥有独立的物理资源**——所有 VF 共享同一 PF 的硬件引擎，只是在寻址和权限上被隔离开来。

**VF 的本质：资源隔离，而非资源复制。** VF 的配置空间极简，只包含必要的 Capabilities。VF 的 BAR 是 PF BAR 空间的一个分片，每个 VF 拿到固定大小的切片，互相不重叠。这种设计让一块物理 GPU 的 framebuffer 可以被切成多份，分别映射给不同的虚拟机。

### VF 的 Routing ID（BDF）如何计算

VF 没有独立的 Device Number，它的 Routing ID 由 PF 的路由信息加上偏移量计算得来：

```
// VF Routing ID 计算
vf_route_id = pf_route_id
            + sriov_first_vf_offset    // 第一个 VF 相对 PF 的偏移
            + vf_id * sriov_vf_stride  // 后续 VF 按步长递增

// ARI 模式（Function 字段扩展为 8 bit，不再有 Dev 字段）：
route_id = bus_num << 8 | func_num

// 非 ARI 模式：
route_id = bus_num << 8 | dev_num << 3 | func_num
```

### VF 的可见性控制

VF 在以下条件同时满足时才对系统可见：

- `SRIOV_VF_ENABLE = 1`：PF 的 SR-IOV 使能位置起
- `vf_id < SRIOV_NUM_VFS`：该 VF 的序号在当前配置的 VF 数量范围内

---

## 三、SR-IOV：标准的单根虚拟化

SR-IOV（Single Root I/O Virtualization）是 PCI-SIG 定义的标准规范，允许一个 PCIe 设备的单个 PF 派生出多个 VF，每个 VF 可以独立分配给一个虚拟机。

```
SR-IOV 功能层级
──────────────────────────────────────────────────
                   PCIe Device
                        │
         ┌──────────────┼──────────────┐
         │              │              │
        PF0            PF1            PF2
   (func_id=0)    (func_id=1)    (func_id=2)
         │
         │  SRIOV_VF_ENABLE=1
         │  SRIOV_NUM_VFS=N
         │
  ┌──────┼──────┬──────┐
  │      │      │      │
 VF0    VF1    VF2   VF(N-1)
(pf=0) (pf=0) (pf=0)  (pf=0)
  │      │      │      │
 VM0    VM1    VM2   VM(N-1)  ← 每个 VM 独占一个 VF
──────────────────────────────────────────────────
VF 有独立 Config Space 和 BAR 切片
PF 保留完整管理权，VF 只有数据面访问权
```

**SR-IOV 的工作流程**：

- **枚举阶段**：OS/Hypervisor 发现 PF，读取 SR-IOV Extended Capability，获知 VF 的数量上限和 BAR 布局
- **资源分配**：Hypervisor 为所有 VF 的 BAR 空间分配物理内存地址，写入 PF 的 VF BAR 寄存器
- **使能**：写 `SRIOV_NUM_VFS` 设置创建数量，写 `SRIOV_VF_ENABLE=1` 使 VF 开始对外可见
- **分配**：Hypervisor 将每个 VF 的 Routing ID 分配给指定 VM，VM 通过 VF 直接访问硬件

> **关键约束**：SR-IOV 标准要求 VF 的数量和 BAR 大小在硬件设计时就固定，不能动态改变。这也是 Resize BAR 等机制存在的原因——在固定框架内提供有限的灵活性。

---

## 四、MF-IOV：重映射的虚拟功能

MF-IOV（Multi-Function I/O Virtualization）是一种不同的虚拟化路径。它的核心思想是：**不把 VF 暴露为 VF，而是把它们重映射（remap）为普通的 PCIe Function**，让 OS 看起来像是有多个独立的 PF。

**MF-IOV 的本质区别**：SR-IOV 的 VF 需要操作系统/Hypervisor 有 SR-IOV 感知能力。MF-IOV 把 VF 重新包装成普通 Function，操作系统用标准 PCIe 枚举流程就能发现它们，无需额外的 SR-IOV 驱动支持。

```
MF-IOV 功能层级
──────────────────────────────────────────────────
                   PCIe Device（硬件内部）
                          │
           ┌──────────────┼──────────────┐
           │              │              │
          PF0            PF1      [VF bank]
     (mfiov_spt=1)                (mfiov_vf_support=N)
           │
           │  重映射（remap）
           │
   ┌───────┼────────┬──────────┐
   │       │        │          │
  F2      F3       F4    ...  F(N+1)   ← OS 看到的是普通 Function
(mfiov_func=1)                         ← 硬件上是 PF0 的重映射 VF
(mfiov_pf_index=0)
(mfiov_vf_index=0,1,2...)

OS 视图：看到多个独立的 Function，无 VF 概念
硬件内部：F2-F(N+1) 实际是 PF0 的 VF，共享 PF0 的物理引擎
──────────────────────────────────────────────────
```

**MF-IOV 的关键属性**：

| 属性字段 | 含义 |
|---|---|
| `mfiov_spt` | 该 PF 是否支持 MFIOV（能否派生重映射 VF） |
| `mfiov_func` | 该 Function 是否是一个被重映射的 VF（=1 表示是） |
| `mfiov_pf_index` | 该重映射 VF 逻辑上归属的 PF 序号 |
| `mfiov_vf_index` | 该重映射 VF 对应的 VF 槽位号 |
| `mfiov_vf_support` | 该 PF 最多可重映射的 VF 数量 |

**MF-IOV 模式下的特殊行为**：

- 调用获取 SRIOV VF 数量的接口返回 0：MFIOV 模式下没有标准 SR-IOV VF
- 重映射 Function 有独立的 BAR 和配置空间，但资源仍来自原 PF 的物理池
- Resize BAR 的寄存器路径与 SR-IOV VF 共用同一套控制寄存器
- 验证环境中通过专用接口区分普通 PF 和重映射 VF

---

## 五、SR-IOV vs MF-IOV：横向对比

| 维度 | SR-IOV | MF-IOV |
|---|---|---|
| 标准归属 | PCI-SIG 业界标准 | 厂商私有扩展 |
| VF 对 OS 的呈现 | VF 类型 Function | 普通 PF 类型 Function |
| OS 感知要求 | 需要 SR-IOV 驱动支持 | 标准 PCIe 枚举即可 |
| VF 数量控制 | 软件写寄存器动态设置 | 硬件固定，枚举时已确定 |
| 共存关系 | MFIOV 模式下 SRIOV VF 数量为 0 | SRIOV 模式下无 MFIOV Function |
| 典型场景 | 网卡、NVMe 的标准虚拟化 | 需兼容遗留 OS 的 GPU 等场景 |

两种机制互斥：芯片设计时选定其中一种，验证环境通过全局模式开关切换整体行为——同一套硬件，在 SRIOV 模式下 VF 以 VF 身份暴露，在 MFIOV 模式下 VF 被重映射为普通 Function，两条路径的寄存器访问逻辑和验证序列完全不同。

---

## 六、在验证环境中的体现

验证环境用一套对象树描述设备的 Function 层级，完整建模了 PF、VF 和 MFIOV Function 的关系：

```
验证环境对象树
──────────────────────────────────────────────────
hphost_info
└── dev_array[设备序号]
      └── ep_dev（EP 设备）
            ├── pfs[]   ← 所有 PF 的描述对象
            │     ├── pfs[0]  is_vf=0（普通 PF）
            │     │     ├── sriov_spt / mfiov_spt（支持标志）
            │     │     ├── vf_support       ← SRIOV 最大 VF 数
            │     │     └── mfiov_vf_support  ← MFIOV 最大重映射数
            │     └── pfs[1]  is_vf=0
            │           └── mfiov_func=1     ← 这是重映射 VF
            │               mfiov_pf_index=0  ← 归属 PF0
            │               mfiov_vf_index=0  ← 对应 VF 槽位 0
            └── vfs[]   ← SRIOV 模式下的所有 VF
                  ├── vfs[0]  is_vf=1, vf_id=0, pf_func_id=0
                  └── vfs[1]  is_vf=1, vf_id=1, pf_func_id=0
```

**关键判断接口**：

| 接口 | 含义 |
|---|---|
| `is_vf()` | 当前 Function 是否是 SR-IOV VF |
| `is_mfiov_func()` | 当前 Function 是否是重映射 VF（MFIOV） |
| `has_vf()` | 当前 PF 是否派生了 VF（MFIOV 模式下恒为 false） |
| `get_sriov_vf_support_num()` | MFIOV 模式返回 0，SRIOV 模式返回最大 VF 数 |
| `is_vf_visible()` | 综合 VF_ENABLE 和 NUM_VFS 判断 VF 当前是否可见 |
| `get_captured_route_id()` | 根据 ARI 模式动态计算 BDF Routing ID |

顶层的 `is_mfiov_mode()` 读取全局特性标志，决定整个验证环境当前处于 SRIOV 还是 MFIOV 配置。两种模式下的对象树形态不同，验证序列的行为也随之切换。

---

## 七、总结

**PF 是根，VF 是叶。** PF 持有完整的管理权限和物理资源，VF 是由 PF 派生的隔离视图。没有 PF 就没有 VF——PF 控制 VF 的生命周期、数量和可见性。

**SR-IOV 是标准路径。** VF 以 VF 身份暴露给 OS，需要 SR-IOV 感知的软件栈。VF 的 Routing ID 由 PF + offset + stride 计算，受 `SRIOV_NUM_VFS` 和 `VF_ENABLE` 联合控制可见性。

**MF-IOV 是重映射路径。** VF 被重映射为普通 PCIe Function，对 OS 完全透明。两种模式互斥：MFIOV 模式下 SRIOV VF 数量为 0，验证环境通过全局模式开关切换整体行为。

**验证关注点**：重点关注 VF 可见性边界（NUM_VFS、VF_ENABLE）、Routing ID 计算的正确性（offset + stride）、MFIOV 重映射关系的一致性（mfiov_pf_index / mfiov_vf_index），以及两种模式下 BAR 空间分配的正确性。
