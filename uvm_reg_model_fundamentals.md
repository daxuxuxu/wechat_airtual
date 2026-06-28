# UVM 寄存器模型（Register Model）

## 从基础原理到工程实践

*芯片验证 · UVM · Register Model · Scoreboard*

---

> **系列导读**
>
> 本文是三篇系列文章的**第一篇**，建议按以下顺序阅读：
> 1. 📖 **本文**：reg model 基础原理与工程实践（从这里开始）
> 2. 📖 Callback 机制：如何在读写流程中插入自定义逻辑
> 3. 📖 predict(DIRECT)：Lock bit 场景下的 scoreboard 误报修复
>
> **适合读者**：了解基本数字电路和 SystemVerilog 语法，但对 UVM 验证框架接触不多的工程师。

---

**读完本文，你将理解**：

- reg model 解决了什么问题、为什么需要它
- desired 和 mirrored 为什么要分成两个值
- set/write/read/predict 各自的边界在哪里
- auto-predict 什么时候会出错
- Adapter 如何连接 reg model 与总线 UVC

---

**摘要**：UVM 寄存器模型（reg model）是现代芯片验证中不可或缺的基础设施。本文不只介绍它提供了什么，更着重解释每一个设计决策背后的动机——为什么需要 desired/mirrored 双值，为什么要区分 set/write，为什么 auto-predict 会失效，为什么需要 predict(DIRECT)。理解这些"为什么"，才能在面对复杂验证场景时做出正确的技术选择。

> **本文代码均为 SystemVerilog（SV），运行在 UVM 仿真环境中。**
> 代码片段省略了部分细节（如 `status` 参数、`env` 路径），聚焦于核心概念。

---

## 零、一分钟背景：芯片验证在做什么

**芯片验证**：在芯片流片前，用仿真手段证明 RTL 设计的行为与规格一致。简单说就是：用 SW 写测试，驱动 RTL，检查输出是否符合预期。

**UVM**（Universal Verification Methodology）：一套验证框架，提供了 driver、monitor、scoreboard、sequence 等标准组件，避免每个项目从零搭建验证环境。

**Scoreboard**：验证中的"裁判"。它接收两路数据——monitor 捕获的"硬件实际行为"和 predictor 计算的"期望行为"——比较两者，不一致则报错。Scoreboard 的预测值准确与否，决定了验证的可信度。

**UVC**（UVM Verification Component）：针对某种总线协议（如 PCIe、SMN、APB）封装的验证组件，包含 driver（发激励）和 monitor（捕获响应）。

---

## 一、为什么需要 Register Model

### 没有 reg model 时的痛点

假设不使用 reg model，验证寄存器访问的典型代码是：

```
// 直接调用总线 UVC
bus_driver.write(addr=0x1000, data=0xA5);
bus_monitor.wait_response();
bus_driver.read(addr=0x1000, data=read_val);
assert(read_val == 0xA5);
```

这在单个测试中尚可接受。但当测试规模扩大时，三个问题接踵而至：

**问题 1：预测值难以管理。** Scoreboard 需要知道"此刻寄存器应该是什么值"，以便与硬件返回值比较。随着测试流程复杂化，寄存器经历多次读写、复位、条件跳转，手动追踪每个寄存器的期望值极易出错——错误的预测比没有预测更危险，它会放过真正的 bug。

**问题 2：地址和字段分散在代码里。** 同一寄存器的地址和字段定义散落在不同的测试文件中。当规格变更时，需要逐一修改，遗漏任何一处都会引入隐蔽错误。

**问题 3：访问语义无法表达。** "写 1 清零"字段和"只读"字段在总线层面看起来都是一次写操作，但预期的硬件响应完全不同。没有地方承载这些语义，scoreboard 无法自动区分。

**reg model 的价值**：将寄存器结构（字段、地址、访问类型、复位值）编码为可复用的对象，提供统一访问接口，并自动维护每个寄存器的"软件认知状态"，为 scoreboard 提供持续准确的预测基准。

---

## 二、三个值：desired、mirrored 与 HW 实际值

这是理解 reg model 的核心，也是最容易被忽视的地方。很多文章只讲 desired 和 mirrored 两个值，但实际上存在**三个独立的值**：

| 值 | 含义 | 存在于 | 访问方式 |
|---|---|---|---|
| **desired** | 软件期望写入的值 | reg model（软件侧） | `set()` 写，`get()` 读 |
| **mirrored** | 软件认为 HW 当前持有的值 | reg model（软件侧） | `get_mirrored_value()` 读 |
| **HW 实际值** | 寄存器里真实存储的值 | 硬件寄存器 | 只能通过 frontdoor read 或 backdoor peek 观测 |

**mirrored 不是 HW 实际值，它是 reg model 对 HW 实际值的最优近似。** 在大多数正常情况下两者相同，但一旦出现写入被拒绝、外部修改、复位等情况，它们就会发生偏离。

### 三者的独立性

初学者容易把 mirrored 和 HW 实际值混为一谈。一个说明三者独立的场景：

```
初始状态：desired = A，mirrored = A，HW 实际值 = A（三者对齐）

执行 set(~A)：
  desired  = ~A   （只改了 desired）
  mirrored = A    （未变）
  HW 实际值 = A   （未走总线，HW 未变）

执行 write(~A)，LOCK=1 拒绝：
  desired  = ~A   （write 前 set 的）
  mirrored = ~A   （auto-predict 错误更新）
  HW 实际值 = A   （LOCK 保护，实际未写入）

三者完全不同！
```

### desired：软件意图

通过 `set()` 修改，通过 `get()` 读取。**修改 desired 不触发任何总线事务**，是纯软件侧操作，不影响 mirrored，更不影响 HW 实际值。

### mirrored：软件对 HW 的认知

通过 auto-predict（下一节详述）或 `predict()` 更新。**mirrored 只是 reg model 的猜测，不是 HW 的事实。** Scoreboard 的 predictor 从 mirrored 生成预期值——mirrored 准确，预测就准确；mirrored 失步，预测就失效。

### HW 实际值：唯一的客观事实

**HW 实际值无法被 reg model 直接查询**，只能通过以下方式观测：

- `read(UVM_FRONTDOOR)`：发起总线读，HW 返回实际值，auto-predict 用返回值更新 mirrored
- `peek()`（backdoor read）：通过 HDL 路径直接读 RTL 信号，同样更新 mirrored

正因如此，mirrored 的正确性依赖两件事：一是 auto-predict 的假设（写入被 HW 接受）成立，二是 read/peek 操作及时同步。

### predict(DIRECT) 的定位

`predict(DIRECT)` 的语义是：**"我已经通过某种方式知道 HW 实际值是什么（如复位后 = 0，如 Lock 拒绝了写入所以仍是原值），直接把这个已知值写入 mirrored，不需要经过总线。"** 它绕过 auto-predict 和所有 Callback，是在"已知 HW 实际值但不想或不能发起总线读"时同步 mirrored 的唯一正确工具。

---

## 三、为什么 set/write 要分开设计

初学者常见的困惑：既然最终都要写寄存器，为什么不直接调用 `write()`，还要有 `set()`？

### `set()` 解决的问题：原子性配置

寄存器通常包含多个字段，它们应该作为一个整体被配置——不能让硬件在一个字段已更新、另一个字段尚未更新时，中途响应一个访问请求。

```
// 错误做法：两次写，硬件可能在中间状态被采样
write(field_A, value_A);   // 硬件现在是"field_A 已更新，field_B 未更新"
write(field_B, value_B);   // 硬件现在才完整

// 正确做法：set 积攒意图，write 一次原子写入
field_A.set(value_A);      // 只改 desired，不走总线
field_B.set(value_B);      // 只改 desired，不走总线
reg.write(status, reg.get(), FRONTDOOR);  // 一次总线事务写入两个字段
```

`set()` 是"积攒意图"的工具，`write()` 是"提交执行"的动作。两者配合实现原子性配置。

### `get()` vs `get_mirrored_value()`：意图还是现实

```
get()                  // 返回 desired（我想要的）
get_mirrored_value()   // 返回 mirrored（HW 实际的）
```

两者在 `write()` 完成后通常相同，但在 `set()` 之后、`write()` 之前存在差异。Scoreboard predictor 应该读 mirrored（硬件现实），而不是 desired（软件意图）。混用会导致在这个窗口期产生错误预测。

---

## 四、为什么需要 auto-predict，以及它为什么会失效

### auto-predict 解决的问题

如果没有 auto-predict，scoreboard 的 predictor 需要手动跟踪每一次寄存器写操作并更新期望值。在一个有数百个寄存器、数千次访问的测试中，这几乎不可能做到。

auto-predict 的设计思路是：**每次 frontdoor write 完成后，自动根据字段的 access 类型计算新的 mirrored 值**，无需人工干预。

**执行过程**：`write(reg, value)` 完成 → auto-predict 触发 → 对每个字段按 access 类型计算新值 → mirrored 更新完成，scoreboard 可以使用。

各 access 类型的计算规则：

- **RW 字段**：`mirrored = value[field_bits]`
- **RO 字段**：`mirrored` 不变（写入被忽略）
- **W1C 字段**：`mirrored &= ~value[field_bits]`

### auto-predict 的根本局限：它假设写入一定成功

auto-predict 建立在一个隐含假设上：**硬件接受了这次写入**。

对于 `RW` 字段，这个假设在正常情况下成立。但在以下场景中，假设被打破：

- **Lock 保护**：字段被锁定后，任何写入都被硬件静默拒绝
- **运行时条件写保护**：只有在特定状态下，写入才会生效
- **电源域隔离**：某些 domain 掉电时，写入被丢弃

在这些场景中，auto-predict 仍然照常更新 mirrored，导致 mirrored 反映的是"软件写了什么"而非"硬件实际接受了什么"——两者之间的分歧是 reg model 中最常见的 scoreboard 误报根源。

---

## 五、为什么需要 predict(DIRECT)

当 auto-predict 因上述原因产生了错误的 mirrored 值，需要一种方式来修正它。

### 为什么不用 write() 修正

`write()` 会再次发起总线事务，产生 scoreboard 监控的新事件，而我们只想修正模型内部状态，不想产生额外的总线流量。而且如果问题是 Lock 保护导致的，再发一次 write 同样会被拒绝，mirrored 仍然是错的。

### 为什么不用 set() 修正

`set()` 只改 desired，不改 mirrored。Scoreboard predictor 读的是 mirrored，`set()` 改了也没用。

### predict(DIRECT) 的精确语义

```systemverilog
void'(field.predict(correct_val, .kind(UVM_PREDICT_DIRECT)));
```

- **不走总线**：不产生任何总线事务
- **不触发 Callback**：完全绕过 Callback 调用链（包括 lock_keep 等保护性 Callback）
- **直接设置 mirrored**：无条件将 mirrored 强制为指定值
- **不影响 desired**：desired 保持原值不变

这使得 `predict(DIRECT)` 成为"强制同步模型状态到已知的硬件实际值"的唯一正确工具：

```
// Lock 保护场景下的正确处理
write(reg, ~orig_val);                    // 总线写，HW 拒绝
                                          // auto-predict: mirrored = ~orig_val（错误）
predict(DIRECT, orig_val);               // 强制修正: mirrored = orig_val（正确）
read(reg, readback);                      // 读回，MONITOR=orig，PREDICTOR=orig → MATCH ✓
```

还有一个典型场景：硬件复位后，寄存器清零，但 mirrored 残留旧值。此时 `predict(DIRECT, reset_value)` 是将模型重新与硬件同步的标准手段。如果改用普通的 `predict(WRITE/READ)`，lock_keep 等 Callback 可能阻止 mirrored 被清零——因为这些 Callback 正是为了防止 mirrored 被意外修改而设计的。DIRECT 绕过所有 Callback，表达的正是"我明确知道硬件的实际状态，强制同步"这一意图。

---

## 六、Adapter：为什么需要它，以及它做了什么

### 根本问题：两套语言之间的鸿沟

reg model 说的是一种通用语言：

```
uvm_reg_bus_op {
    kind:    READ / WRITE
    addr:    物理地址
    data:    读写数据
    n_bits:  位宽
    byte_en: 字节使能
    status:  操作结果
}
```

但 DUT 的总线 UVC 说的是协议特定的语言——PCIe 的 CFG_WR/CFG_RD、SMN 的 MEM_WR/MEM_RD、APB 的 PSEL+PENABLE 握手……这些协议在帧格式、地址编码、控制信号上各不相同，reg model 无法直接与它们对话。

**Adapter 存在的根本理由**：在 reg model 的通用操作语言和总线 UVC 的协议特定语言之间充当翻译官，使同一套 reg model 定义可以被不同的总线协议驱动，只需更换 Adapter 而不需要修改寄存器定义。

> **类比**：就像 USB 转接头——两端的物理接口不同（USB-A vs USB-C），但传输的数据是同一份。Adapter 不改变"要做什么"，只改变"用什么格式表达"。

### reg2bus()：从意图到行动

**reg2bus 执行过程**：

1. reg model 发起 `write(addr=0x1000, data=0xA5)`，调用 `reg2bus()`
2. 输入：`uvm_reg_bus_op {kind=WRITE, addr=0x1000, data=0xA5}`
3. 判断目标地址空间（PCIe Config Space？SMN MEM 空间？）
4. 构造协议特定的 bus transaction（如 `CFG_WR_TYPE0, byte_enable=0xF, tag=0x01`）
5. 返回 bus sequencer 可发送的 `sequence_item`

`reg2bus()` 的核心工作是**编码**：将 reg model 描述的"意图"（我要写这个地址的这个数据）转化为总线协议能够理解的具体帧格式。

在这个过程中，Adapter 还需要解决几个实际问题：

- **选择正确的事务类型**：同一个 `UVM_WRITE` 意图，根据目标地址空间（Config Space / Memory Space / IO Space）需要映射到不同的总线命令
- **计算字节使能**：`n_bits` 和访问偏移决定哪些字节有效
- **填充协议特定字段**：总线 ID、安全属性、流量类型等 reg model 层面无感知的字段，由 Adapter 填充合理的默认值或从扩展对象中读取

### bus2reg()：从响应到认知

写操作完成、读操作返回数据——总线 monitor 捕获到这些事件，但 reg model 不知道发生了什么。`bus2reg()` 负责将 monitor 捕获的总线事务翻译回 reg model 能理解的结果：

**bus2reg 执行过程**：

1. monitor 捕获到总线事务（写响应 / 读完成帧），调用 `bus2reg()`
2. 输入：协议特定的 `bus_item`
3. 从帧格式中解析：addr（物理地址）、data（读操作返回数据）、kind（READ/WRITE 完成）、status（成功 / UR / CA / timeout）
4. 填充 `uvm_reg_bus_op rw`（ref 参数）并返回
5. reg model 收到结果，触发 auto-predict，更新 mirrored

**为什么写操作也需要 bus2reg？** 即使是写操作，reg model 也需要知道"这次写是否真正被 DUT 接受"。如果总线返回了 Unsupported Request 或 Completer Abort，reg model 应该将 `rw.status` 设为对应的错误码，而不是盲目执行 auto-predict 更新 mirrored。bus2reg 正是这个反馈通道的实现点。

### 完整的数据流

**去程**：`reg.write(value)` → `reg2bus()` 生成总线事务 → bus_sequencer → driver → DUT

**回程**：DUT 响应 → monitor 捕获 → `bus2reg()` → reg model 更新 mirrored → predictor → scoreboard 比对

这条流水线揭示了 Adapter 的两个关键角色：

1. **去程（reg2bus）**：将 reg model 的操作意图转化为驱动 DUT 的真实总线事务
2. **回程（bus2reg）**：将 DUT 的总线响应转化为 reg model 的状态更新输入，同时为 scoreboard predictor 提供事务地址和数据，完成预测比对

### 一个 Adapter，多套总线

这个设计的优雅之处在于解耦：寄存器定义不需要知道它将被哪种总线访问；总线 UVC 不需要知道有 reg model 存在。两者通过 Adapter 在运行时绑定。同一个寄存器块可以注册多个 map，每个 map 关联不同的 Adapter 和不同的总线 UVC：

```
同一寄存器块：
  PCIe Config Space Map → PCIe Adapter → PCIe Sequencer
  SMN Map               → SMN Adapter  → SMN Sequencer
  APB Map               → APB Adapter  → APB Sequencer
```

测试代码通过 `write(..., map=smn_map)` 指定走哪条路，其余全部由框架自动处理。

---

## 七、为什么要区分 Frontdoor 和 Backdoor（续）

### Frontdoor 的价值：完整的验证覆盖

Frontdoor 访问经过完整的总线路径：地址解码、总线协议、权限检查、硬件逻辑……每一个环节都有可能存在 bug。Frontdoor 访问让 monitor 捕获到真实的总线事务，scoreboard 才能验证这一整条路径是否正确。

验证的核心价值在于发现真实存在的 bug。如果跳过总线路径直接访问硬件，地址解码错误、权限检查缺失、总线仲裁问题就永远不会被发现。

### Backdoor 存在的理由：仿真效率

Frontdoor 访问需要真实的总线时序：仲裁、握手、响应……一个复杂的访问可能消耗数百个时钟周期。当需要在仿真开始阶段预置几千个寄存器时，全部走 Frontdoor 会消耗大量仿真时间，而这些初始化本身不是被测对象。

Backdoor 通过 HDL 路径直接读写 RTL 信号，**零仿真时间**完成，是初始化和 debug 场景的高效工具。

### 选择原则

不是"Frontdoor 好 Backdoor 坏"，而是根据目的选择：

| 目的 | 推荐方式 | 原因 |
|---|---|---|
| 验证总线协议和地址解码 | Frontdoor | 需要真实总线路径 |
| 验证寄存器权限控制 | Frontdoor | 需要经过权限检查逻辑 |
| 仿真开始阶段的批量初始化 | Backdoor | 不是被测对象，避免消耗仿真时间 |
| debug 时快速查询寄存器状态 | Backdoor | 零时间，不影响仿真进程 |
| 强制注入异常状态 | Backdoor | 绕过正常访问路径是目的本身 |

---

## 八、为什么 Callback 是必要的补充

### reg model 静态定义的局限

寄存器定义（字段名、位宽、access 类型、复位值）在编译时确定，描述的是静态属性。但硬件的许多行为是运行时动态决定的：

- 一个字段被置 1 后，该寄存器的所有字段都变为只读——这个"保护状态"依赖运行时的值，无法在静态定义中表达
- 写入某个控制字段，会联动触发另一个状态字段的变化——这是 side effect，也不在静态定义范围内
- 特定访问序列才能解锁某寄存器的写权限——这是访问约束，依赖访问历史

**Callback 的存在价值**：在不修改寄存器类定义的前提下，向访问流程注入运行时逻辑，弥补静态定义的表达能力不足。

### Callback 与 predict(DIRECT) 的互补关系

这两者解决的是同一个问题（mirrored 准确性）的不同子场景：

- **Callback（post_predict hook）**：在正常访问流程中拦截并修正 auto-predict 的结果。适合"每次写操作后都需要维护某种约束"的持续性规则。

- **predict(DIRECT)**：在需要强制同步的特定时刻（复位后、破坏性测试后）绕过所有规则，直接写入已知正确值。适合"我明确知道此刻硬件的实际状态"的一次性同步。

两者的关系是：Callback 负责正常流程中的持续守卫，predict(DIRECT) 是在守卫无法正确工作时的手动强制介入。

---

## 九、为什么需要双模式查询

### 问题：同一个查询接口，在不同阶段需要不同的数据源

考虑一个查询"某配置的当前基地址"的接口。在不同阶段，这个问题的正确答案来自不同的地方：

**初始化阶段**：寄存器尚未写入硬件。此时调用 `read()` 会得到复位值（因为 HW 还没被配置），不是期望的答案。正确的答案在软件模型中——是经过预计算的期望配置（desired）。

**运行阶段**：寄存器已写入硬件。此时软件模型计算的 desired 可能已经过时（硬件可能有写保护、字段截断等行为使实际写入值与 desired 不同）。正确的答案是 mirrored——反映硬件实际接受的值。

### 解决方案：状态标志内聚判断

一种成熟的设计模式是引入一个阶段标志：

```
phase = INIT:  查询返回 desired（预计算的期望配置）
phase = LIVE:  查询返回 mirrored（硬件实际状态）
```

标志在 `write()` 完成后切换到 LIVE。上层调用方不需要关心当前处于哪个阶段，查询函数内部自动选择正确的数据源。

**这个模式的核心价值是降低认知负担**：没有它，每个调用方在每次查询前都需要判断"现在是初始化阶段还是运行阶段"——这种判断逻辑散落在代码各处，极易遗漏或出错。将判断内聚在查询函数内部，是封装的正确做法。

---

## 十、多轮测试中的 mirror 管理

### 为什么多轮测试比单轮更难

单轮测试中，仿真开始时所有寄存器从复位值出发，mirrored 与硬件完全同步。整个测试流程线性推进，只要 write/read 操作正确维护 mirrored，同步状态就能保持。

多轮测试（带复位的循环）引入了新的挑战：**每次硬件复位将 RTL 寄存器清零，但 reg model 的 mirrored 不会随复位自动归零**。

```
第 1 轮：write(reg, A) → mirrored = A
         → 复位 → HW: reg = reset_val，mirrored 仍 = A  ← 分叉！

第 2 轮：read(reg) → MONITOR = reset_val，PREDICTOR = A → 误报
```

### 正确的处理方式

每次复位后，需要显式将 mirrored 同步到复位值：

```systemverilog
// 方式 A：predict(DIRECT) 强制同步到复位值
void'(field.predict(field.get_reset(), .kind(UVM_PREDICT_DIRECT)));

// 方式 B：backdoor read 同步实际硬件值
reg.peek(status, val);  // 自动更新 mirrored 为 RTL 实际值
```

**为什么要用 predict(DIRECT) 而不是普通 predict？** 如果寄存器上有 lock_keep 等 Callback，普通的 predict(WRITE/READ) 会触发它们，可能阻止 mirrored 被清零。DIRECT 专门用于"我比 Callback 更了解当前实际状态"的场景，强制覆盖任何约束。

### stale mirror 的连锁效应

如果某轮跳过了某个寄存器的重新编程，该寄存器的 mirrored 会残留上一轮的值，而硬件已被复位为初始值。这种"stale mirror"会在下一次该寄存器被访问时引发 scoreboard 误报，且往往发生在距离问题根因很远的代码位置，极难追踪。

防范 stale mirror 的最可靠方式：**复位后系统性地重置所有被关注寄存器的 mirrored**，而不是依赖"这个寄存器应该在后面某处被重新编程"的假设。

---

## 十一、Field 访问类型：为什么要有这么多种

直觉上，一个寄存器字段要么"可读写"，要么"只读"，为什么 UVM 要定义十几种 access 类型？

答案是：不同的访问类型描述的是硬件对写操作的不同响应语义，每种语义都对应真实存在的硬件设计需求：

| Access 类型 | 存在理由 | 硬件场景 |
|---|---|---|
| `RW` | 最基础的读写 | 普通配置寄存器 |
| `RO` | 硬件生成的状态，不应被软件覆写 | 硬件版本号、采样信号 |
| `W1C` | 软件通过"写1"主动清除硬件置位的标志 | 中断状态、错误标志 |
| `W1S` | 软件通过"写1"置位，硬件通过其他条件清除 | 软件请求触发位 |
| `WO` | 触发动作，不需要/不允许读回 | 命令字、软件触发 |
| `RC` | 读操作本身就是清除动作 | 自清状态寄存器 |
| `W0C` | 写0清零（与W1C对称） | 某些特殊清除语义 |

access 类型不只影响 auto-predict 的计算规则，还影响覆盖率收集（是否收集"写1清零的覆盖"）和形式验证约束（RO 字段是否被写入应该是一个 violation）。

---

## 十二、与 Scoreboard 集成的架构

reg model 与 scoreboard 的集成通过 adapter 和 predictor 完成，形成一条完整的预测流水线：

**预测流水线**（以 write 操作为例）：

1. **Test Code** 调用 `reg.write(value)`
2. **Register Model** 生成总线请求，同时更新 mirrored
3. 请求经 **Bus Sequencer → Driver → Bus** 到达 **DUT**
4. DUT 响应被 **Monitor** 捕获，送入 **Predictor**
5. Predictor 从 reg model 读取 mirrored 作为预期值，与 Monitor 数据一起送入 **Scoreboard**
6. Scoreboard 比较预期与实际，输出 PASS / FAIL

**Predictor 的职责**：监听 monitor 发出的总线事务，从 reg model 读取 mirrored 生成预期响应，送入 scoreboard。

**核心推论**：scoreboard 的准确性完全依赖 mirrored 的准确性。mirrored 任何时刻的错误，都会在该寄存器下一次被 scoreboard 监控的读操作中体现为误报（或漏报）。这是为什么 reg model 正确性如此关键——它不只是一个访问封装，更是 scoreboard 功能的基础。

---

## 十三、结语

UVM reg model 的每一个设计决策都有其解决的具体问题：

- **desired/mirrored 双值**：因为软件意图和硬件现实天然分离，需要两个维度的信息
- **set()/write() 分离**：因为原子性配置需要先积攒意图、后一次性提交
- **auto-predict**：因为手动跟踪每次写操作对 scoreboard 的影响不可扩展
- **predict(DIRECT)**：因为 auto-predict 有"写入一定成功"的假设，现实中这个假设常被打破
- **Frontdoor/Backdoor 并存**：因为验证覆盖性和仿真效率是两个不同维度的需求
- **Callback**：因为静态 access 类型无法表达运行时动态行为
- **双模式查询**：因为同一个接口在不同阶段需要来自不同数据源的答案

理解这些"为什么"，在遇到具体问题时，答案往往自然浮现——而不是在记忆了一堆 API 用法之后，仍然不知道在这个场景下该用哪个。

---

---

## 附录：术语速查

| 术语 | 一句话定义 |
|---|---|
| `desired` | reg model 中"软件期望写入"的值，`set()` 修改，不触发总线 |
| `mirrored` | reg model 中"软件认为 HW 当前持有"的值，scoreboard 预测基于此 |
| `auto-predict` | `write()`/`read()` 完成后，reg model 自动更新 mirrored 的机制 |
| `predict(DIRECT)` | 强制设置 mirrored，绕过所有 Callback，不走总线 |
| `frontdoor` | 通过真实总线路径访问寄存器，scoreboard 可监控 |
| `backdoor` | 通过 HDL 路径直接读写 RTL 信号，零仿真时间，scoreboard 不感知 |
| `Adapter` | 实现 `reg2bus()`/`bus2reg()`，在通用操作与协议帧之间转换 |
| `Callback` | 注册到 reg model 的 hook 函数，在读写流程各阶段插入自定义逻辑 |
| `UVC` | 针对某总线协议封装的验证组件（driver + monitor） |
| `Scoreboard` | 比较"期望行为"与"实际行为"的验证裁判组件 |
| `access type` | 字段的读写语义（RW/RO/W1C 等），决定 auto-predict 的计算规则 |

---

## 思考题

读完本文，尝试回答以下问题来检验理解：

1. `set(value)` 和 `write(value)` 各自会改变 desired 和 mirrored 中的哪一个？两者都改变时，仿真时间有变化吗？

2. 如果对一个 `RO` 字段调用 `write()`，mirrored 会变吗？如果是运行时 Lock 保护的 `RW` 字段，mirrored 又会怎样？两者的区别在哪里？

3. 硬件复位后，你想把某寄存器的 mirrored 归零，但该寄存器上有一个 lock_keep Callback 阻止 mirrored 被清零。你会选择哪种方法，为什么？

4. `bus2reg()` 只在读操作时有意义吗？写操作时它做了什么，为什么写操作也需要它？

---

## 参考答案

**1.** `set(value)` 只改变 desired，不改变 mirrored，不产生总线事务，仿真时间不推进。`write(value)` 同时改变 desired 和 mirrored（通过 auto-predict），会产生真实总线事务，仿真时间向前推进。

**2.** 对 `RO` 字段调用 `write()`：auto-predict 检查到 access 类型为 RO，**不更新 mirrored**，mirrored 保持原值——这是 UVM 内置的正确处理，不需要额外干预。对运行时 Lock 保护的 `RW` 字段调用 `write()`：UVM 不知道字段被动态锁定，auto-predict 仍然**错误地更新 mirrored** 为写入值，与硬件实际值产生失步。区别在于：RO 是编译期静态属性，UVM 认识它；Lock 保护是运行时条件，UVM 无感知。

**3.** 应选择 `predict(UVM_PREDICT_DIRECT, 0)`。普通的 `predict(WRITE)` 或 `predict(READ)` 会触发 Callback 调用链，lock_keep Callback 会阻止清零。只有 `UVM_PREDICT_DIRECT` 完全绕过所有 Callback，无条件将 mirrored 强制设为指定值。

**4.** 写操作同样需要 `bus2reg()`。其作用是将总线的写响应（完成帧）翻译回 reg model 可理解的格式，填充 `rw.status`。若总线返回错误（如 Unsupported Request），`bus2reg()` 将 status 设为非 OK，reg model 收到后可以跳过 auto-predict 或报告错误，而不是盲目将 mirrored 更新为一个被硬件拒绝的值。

---

> **配套阅读**
>
> - **Callback 机制**：如何通过 hook 在读写流程中拦截并修正 auto-predict 的结果
> - **predict(DIRECT) 的精确语义**：Lock bit 场景下的 scoreboard 误报根因与修复

---

*本文内容仅供参考，如有错误或不当之处，欢迎指正。*
