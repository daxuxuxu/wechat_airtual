# NBIF PCIe 拓扑查询：从 is_bigapu() 到规范化接口

## 为什么你的拓扑判断代码可能不对

*芯片验证 · NBIF · PCIe 拓扑 · 代码规范*

---

**摘要**：NBIF 的 PCIe 拓扑由三个 Strap 共同决定，不同项目的组合各不相同。验证代码中曾大量使用 `is_bigapu()` 来区分拓扑类型，但这个接口有一个隐蔽的前提条件——它只在特定模式下有意义。本文梳理拓扑控制的底层逻辑，介绍规范化的替代接口，并给出迁移判断的具体依据。

---

## 零、背景：三个 Strap 决定拓扑

NBIF 的 PCIe 拓扑结构由三个 Strap 共同控制：

| Strap | 含义 |
|---|---|
| `STRAP_BIGAPU_MODE` | 是否启用 BigAPU 模式（多模式项目标志） |
| `STRAP_SWUS_SPT` | 是否支持 Switch Upstream Port |
| `STRAP_SWDS_SPT` | 是否支持 Switch Downstream Port |

这三个 Strap 的组合决定了芯片工作在哪种 PCIe 拓扑模式下。不同项目的默认值不同，但可以归纳为两种基本形态：

**RC+EP 模式**（APU / 集成 GPU）：`STRAP_SWUS_SPT=0, STRAP_SWDS_SPT=0`，没有 Switch，Root Complex 直接连接 Endpoint。

**US+DS+EP 模式**（DGPU / 独立 GPU）：`STRAP_SWUS_SPT=1, STRAP_SWDS_SPT=1`，有完整的 Switch 层级，US Port 连上游，DS Port 连下游 EP。

```
RC+EP 模式（无 Switch）        US+DS+EP 模式（有 Switch）

    Host CPU                        Host CPU
       |                               |
       |  PCIe Link                    |  PCIe Link
       |                               |
    EP Functions                   US Func (SWUS)
    (PF0, PF1, VF...)                  |
                                   DS Func (dwn_pf)
                                       |
                                   EP Functions
                                   (PF0, PF1, VF...)
```

---

## 一、is_bigapu() 的问题在哪里

`is_bigapu()` 读取的是 `STRAP_BIGAPU_MODE` 这个 Strap 的值。这个 Strap 的语义依赖于另一个 feature：只有当 `nbif_design.nbif0.rc == 2` 时，`STRAP_BIGAPU_MODE` 才有明确含义；当 `rc != 2` 时，这个 Strap 的值无关紧要。

但验证代码中大量的 `is_bigapu()` 调用**没有加 `rc == 2` 的前提检查**，直接用这个值来判断拓扑类型。这在只支持单一 PCIe 模式的项目上没有问题，但在多模式项目上会埋下隐患——项目可能在某个模式下 `STRAP_BIGAPU_MODE=1`，在另一个模式下需要不同的行为，而调用方完全没有感知。

更深层的问题是：**`is_bigapu()` 混淆了两个不同层次的概念**。

- 拓扑结构（有没有 Switch）应该用 `has_swus()` / `has_swds()` 这类接口来查询
- 项目能力（是否支持多模式、是否支持 RC）应该用 `proj_support_*()` 系列接口来查询
- `is_bigapu()` 则是把 Strap 的硬件值直接暴露给了调用方，调用方不得不自己理解这个值在当前上下文的含义

---

## 二、四种拓扑结构详解

理解了拓扑结构，才能选对替代接口。NBIF 实际存在四种拓扑形态，每种都有明确的硬件形态和使用场景。

---

### 2.1 RC+EP 拓扑

**使用场景**：集成 GPU（APU），芯片既作为 Root Complex 管理下挂设备，又以 EP 身份向上游主机暴露功能。

**Strap 特征**：`STRAP_SWUS_SPT=0, STRAP_SWDS_SPT=0`，`STRAP_BIGAPU_MODE` 取决于是否为多模式项目。

```
主机 CPU
   |
   | PCIe 链路（NBIF 作为 EP 响应主机）
   |
+--+---------------------------+
|  NBIF                        |
|                              |
|  EP Functions                |
|  (PF0 GFX, PF1 Audio, ...)   |
|                              |
|  Root Complex (RC)           |  <-- NBIF 自身也有 RC，管理下挂设备
|  |                           |
|  +-- 下游 PCIe 设备          |
+------------------------------+
```

**核心特点**：

- 对主机方向：NBIF 是 EP，响应主机的读写请求
- 对下游方向：NBIF 有自己的 RC，负责枚举和管理下挂的其他 PCIe 设备
- 无 Switch（无 US Func、无 DS Func）
- 验证环境中 `us_dev == null`，`dev_array` 里只有 EP 侧设备

**验证关注点**：EP 配置空间的正确性、RC 下游设备枚举流程、EP 和 RC 两个方向的事务路由不冲突。

---

### 2.2 EP Only 拓扑

**使用场景**：纯计算加速器或纯 EP 模式，芯片只作为 Endpoint 存在，没有 RC 能力，也没有 Switch。

**Strap 特征**：`STRAP_SWUS_SPT=0, STRAP_SWDS_SPT=0`，`STRAP_BIGAPU_MODE=0`，且 RC feature 不使能。

```
主机 CPU 或上游 RC
   |
   | PCIe 链路
   |
+--+---------------------------+
|  NBIF                        |
|                              |
|  EP Functions only           |
|  (PF0, PF1, VF...)           |
|                              |
|  无 RC，无 Switch             |
+------------------------------+
```

**核心特点**：

- NBIF 只有 EP 功能，角色单一
- 没有对下游的管理能力
- 拓扑最简单，不涉及路由层级
- 验证环境中 `us_dev == null`，无 DS 设备，只有 EP 功能对象

**与 RC+EP 的区别**：Strap 组合可能相同，但 RC feature 是否使能决定了 RC 侧逻辑是否存在。`has_rc()` 返回 false，`is_ep_only()` 返回 true。

**验证关注点**：EP 功能的完整性、BAR 配置、SR-IOV / MF-IOV 行为，以及各种错误响应场景。

---

### 2.3 US+DS+EP 拓扑（Switch 模式）

**使用场景**：独立 GPU（DGPU），芯片内部有完整的 PCIe Switch，主机通过 Switch 访问 EP 功能。

**Strap 特征**：`STRAP_SWUS_SPT=1, STRAP_SWDS_SPT=1`。

```
主机 CPU
   |
   | PCIe 链路（连接到 NBIF 的 US Port）
   |
+--+-------------------------------+
|  NBIF                            |
|                                  |
|  US Func (SWUS)                  |  <-- 面向主机的上游口
|  |   路由：EP -> 主机方向         |
|  |                               |
|  DS Func (dwn_pf)                |  <-- 面向 EP 的下游口
|  |   路由：主机 -> EP 方向        |
|  |                               |
|  +-- EP Functions                |
|       (PF0, PF1, VF...)          |
+----------------------------------+
```

**核心特点**：

- **US Func（SWUS）**：Switch 上游口，接收来自主机的事务并向下分发；汇聚 EP 的响应并向上转发
- **DS Func（dwn_pf）**：Switch 下游口，将主机事务路由到对应 EP；管理下游地址范围（MEM_BASE / MEM_LIMIT）
- **EP Functions**：实际工作的功能单元，挂在 DS 口下
- 验证环境中 `us_dev != null`，`dev_array` 里同时有 DS 设备和 EP 设备

**事务路径**：

```
主机发出读请求
  -> US Func 接收（检查地址是否在管辖范围）
    -> DS Func 转发（根据 MEM_BASE/LIMIT 路由到具体 EP）
      -> EP Function 处理并返回 Completion
    <- DS Func 回传
  <- US Func 回传给主机
```

**验证关注点**：US/DS 地址窗口配置（BASE/LIMIT 寄存器）、Switch 的事务转发正确性、ACS（访问控制服务）、DS 口的链路管理、US 和 EP 两套中断路径。

---

### 2.4 多模式拓扑

**使用场景**：同一颗芯片需要支持多种 PCIe 拓扑，根据系统配置在运行时切换，如在 APU 系统中以 RC+EP 工作、在服务器中以纯 EP 工作。

**Strap 特征**：`STRAP_BIGAPU_MODE=1`，表明该芯片支持多种模式，具体激活哪种由其他配置决定。

```
同一颗 NBIF 芯片，不同部署场景下的拓扑：

场景 A（APU 系统）：          场景 B（服务器 / 加速器）：

主机 CPU                      主机 CPU / 上游 RC
   |                               |
   |                               |
NBIF                          NBIF
  RC + EP Functions             EP Functions only
  （RC 管理下游设备）           （纯计算加速器）
```

**核心特点**：

- 硬件资源同时具备多种拓扑能力，但每次上电只激活其中一种
- `STRAP_BIGAPU_MODE=1` 是"这颗芯片支持多模式"的标志，而不是"当前工作在某种模式"的标志
- 当前实际工作在哪种拓扑，需要用 `has_rc()` / `is_ep_only()` 实时查询，而不是看 `STRAP_BIGAPU_MODE`

**这正是 is_bigapu() 最容易出错的地方**：对于多模式项目，`STRAP_BIGAPU_MODE=1` 只说明"有能力支持多模式"，并不等于"当前有 RC"。在 EP only 场景下 `is_bigapu()` 返回 true，但 `has_rc()` 返回 false，两者语义完全不同。

**验证关注点**：两种（或更多）拓扑分别完整覆盖，模式切换边界行为，寄存器在不同模式下的复位值和可访问性。

---

### 各拓扑对比速查

| 拓扑 | has_rc() | has_swus() | has_swds() | is_ep_only() | 典型场景 |
|---|---|---|---|---|---|
| RC+EP | true | false | false | false | 集成 GPU（APU） |
| EP Only | false | false | false | true | 纯计算加速器 |
| US+DS+EP | false | true | true | false | 独立 GPU（DGPU） |
| 多模式（当前 RC+EP）| true | false | false | false | 多模式项目 APU 模式 |
| 多模式（当前 EP Only）| false | false | false | true | 多模式项目加速器模式 |

注意：多模式项目的 `STRAP_BIGAPU_MODE` 在所有模式下都是 1，但拓扑查询接口的返回值随当前激活模式而变化。这就是为什么要用 `has_*()` 而不是 `is_bigapu()`。

---

## 三、规范化的替代接口

### 拓扑查询接口（优先使用）

这类接口直接描述当前运行时的拓扑状态，语义明确：

| 接口 | 含义 |
|---|---|
| `has_rc()` | 当前拓扑是否包含 Root Complex（RC 模式） |
| `has_swus()` | 当前拓扑是否包含 Switch Upstream Port |
| `has_swds()` | 当前拓扑是否包含 Switch Downstream Port |
| `is_ep_only()` | 当前是否纯 EP 模式（无 RC、无 Switch） |

这四个接口反映的是**当前实际配置**下的拓扑状态，与项目无关。大多数原 `is_bigapu()` 的使用场景都应该用这组接口替换。

**替换对应关系**：

- 原来用 `is_bigapu()` 来判断"有没有 RC"-> 改用 `has_rc()`
- 原来用 `is_bigapu()` 来判断"是不是有 Switch"-> 改用 `has_swus()` 或 `has_swds()`
- 原来用 `!is_bigapu()` 来判断"纯 EP 模式"-> 改用 `is_ep_only()`

### 项目能力查询接口（当拓扑接口不足以覆盖时使用）

这类接口反映的是**项目级别的能力声明**，而不是当前运行时的状态：

| 接口 | 含义 |
|---|---|
| `proj_support_rc()` | 该项目是否在任意模式下支持 RC |
| `proj_support_us()` | 该项目是否在任意模式下支持 US Port |
| `proj_support_swds()` | 该项目是否在任意模式下支持 Switch DS Port |
| `proj_support_multi_mode()` | 该项目是否支持多种 PCIe 模式切换 |

这类接口适合用在"根据项目能力决定是否跳过某段测试逻辑"的场景，而不是用来判断当前运行时的拓扑。

---

## 四、怎么判断该用哪个接口

一个简单的决策流程：

```
我的代码在做什么？
    |
    +-- 根据"当前跑的是哪种拓扑"来决定行为
    |       --> 用 has_rc() / has_swus() / has_swds() / is_ep_only()
    |
    +-- 根据"这个项目支不支持某种模式"来决定是否跳过
    |       --> 用 proj_support_rc() / proj_support_us() / proj_support_multi_mode()
    |
    +-- 既有运行时判断，又有项目级判断
            --> 分开写，不要合并成一个条件
```

**具体场景举例**：

场景 A：初始化 US Port 相关的寄存器。
-> 用 `has_swus()`，因为只有当前拓扑有 US Port 时才需要初始化，与项目无关。

场景 B：跳过某个只在 RC 模式下有意义的测试。
-> 用 `has_rc()`，当前配置有 RC 才跑这段逻辑。

场景 C：为多模式项目生成不同的测试配置。
-> 用 `proj_support_multi_mode()`，这是项目级别的能力判断。

场景 D：判断某段代码是否应该同时覆盖 RC 和 EP 两条路径。
-> 用 `proj_support_rc()` 结合 `is_ep_only()`，分别处理两个维度。

---

## 五、迁移时的注意事项

**is_bigapu() 会被收窄为内部接口**，迁移完成后它将不再对外暴露，调用方无法再直接使用。在此之前，需要对所有调用点逐一判断：

- 这个调用点真正需要的是"拓扑查询"还是"项目能力查询"？
- 如果是拓扑查询，选 `has_*()` 系列
- 如果是项目能力查询，选 `proj_support_*()` 系列
- 如果调用点的逻辑本身就不清晰，趁此机会梳理清楚再替换

**不要机械地替换**：不是把 `is_bigapu()` 全换成某一个固定的接口，而是根据每个调用点的具体语义选择最合适的替代。同一份代码里出现多处 `is_bigapu()`，可能需要换成不同的接口。

**多模式项目格外要注意**：对于支持 RC+EP 和 US+DS+EP 两种模式的项目，拓扑查询接口返回的是当前模式下的实际状态，每次跑测试时结果可能不同。不要把拓扑查询的结果缓存下来复用——在需要时实时查询。

---

## 六、总结

`STRAP_BIGAPU_MODE` 描述的是一个依赖前提条件的硬件 Strap 值，直接把它暴露给验证代码导致了语义模糊和潜在风险。

规范化之后，代码应该用两类接口分别处理两件事：

- **拓扑状态**：`has_rc()` / `has_swus()` / `has_swds()` / `is_ep_only()`，描述当前运行时的实际拓扑
- **项目能力**：`proj_support_rc()` / `proj_support_us()` / `proj_support_swds()` / `proj_support_multi_mode()`，描述该项目支持的能力范围

判断不清楚用哪个时，先问自己：这段代码在意的是"现在跑的是什么"还是"这个项目能跑什么"。前者用拓扑接口，后者用项目能力接口。
