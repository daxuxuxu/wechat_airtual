# UVM 验证环境中的两种 Merge 模式

## 从总线 Beat 合并到跨寄存器响应合并

*芯片验证 · UVM · Register Model · Monitor · Predictor · Merge*

---

> **前置概念速查**：
> - `mirrored`：reg model 对硬件当前状态的认知镜像，scoreboard 预测基于此
> - `uvm_reg_predictor`：UVM 内置预测器，监听总线事务并调用 `rg.predict()` 更新镜像
> - `analysis port / imp`：UVM 组件间单向传播数据的机制

---

**读完本文，你将理解**：

- 验证日志里"merge done"出现在两个完全不同的地方，各自解决什么问题
- Type 1：monitor 如何把物理接口上的多个 beat 拼装成一笔逻辑事务
- Type 2：RAL predictor 如何把拆分的寄存器子事务重新合并成完整响应
- 两种 Merge 在整个仿真流水中的位置和协作关系

---

**摘要**：在复杂验证环境的仿真日志中，"merge done"这个词出现在两个截然不同的上下文里。第一种出现在 Monitor 组件，指的是把物理总线上多个时钟周期的 beat 拼成一笔完整的逻辑请求；第二种出现在 RAL Predictor 组件，指的是把 UVM RAL 针对多个寄存器的分批预测结果合并成一个完整的寄存器响应。两种 Merge 在流水线的不同层次各司其职，缺一不可。

---

## 零、全局视角：两种 Merge 在哪里

```
  总线物理接口
       |
       |  多个 beat（HDR + DATA[0..N]）
       v
  ┌──────────────────────────────────┐
  │         Module Monitor           │
  │                                  │
  │   req_q[] + data_q[]             │
  │   beat by beat 累积              │──→ "read/write req merge done"
  │   最后一个 DATA beat 到达后      │       (Type 1)
  │   合并为一笔逻辑事务             │
  └──────────────┬───────────────────┘
                 |
                 v
  ┌──────────────────────────────────────────────────┐
  │               Module Predictor                   │
  │                                                  │
  │          ┌───────────────────────────────────┐   │
  │          │        RAL Reg Predictor          │   │
  │          │                                   │   │
  │          │  split → UVM RAL → merge          │   │
  │          │  pending_q 追踪进度               │──→ "pending trans cleared"
  │          │  reg_array 累积各寄存器值          │       (Type 2)
  │          └───────────────────────────────────┘   │
  └──────────────┬───────────────────────────────────┘
                 |
                 v
        Scoreboard（期望值 vs 实际值比对）
```

**一句话区分**：

| | Type 1 | Type 2 |
|---|---|---|
| 所在组件 | Module Monitor | RAL Reg Predictor |
| 合并对象 | 物理接口上的多个 beat | 多个寄存器的预测子事务 |
| 触发条件 | 最后一个 DATA beat 到达 | pending_q 清空 |
| 日志关键词 | `read/write req merge done` | `pending trans cleared` |

---

## 一、Type 1 — Request Merge（Module Monitor）

### 1.1 为什么需要 Beat 合并

物理总线上，一笔逻辑请求可能分多个时钟周期传输：

- **第 1 拍**：Header beat，携带地址、命令码、tag、VC 等控制信息
- **第 2–N 拍**：Data beat，每拍固定位宽，携带写数据（读请求没有 data beat）

Monitor 采样到的是原始物理信号，每拍看到的都是不完整的碎片。只有把所有 beat 拼在一起，才能得到一笔有意义的逻辑事务，才能送给 predictor 做预测和 scoreboard 做比对。

### 1.2 Beat 合并流程

```
  总线物理接口
  ──────────────────────────────────────────────────────
  时钟周期：    1          2          3          4
               |          |          |          |
  Beat：   [HDR beat] [DATA[0]]  [DATA[1]]  [DATA[2]]
               |          |          |          |
               v          v          v          v
           req_q[0]   data_q[0]  data_q[1]  data_q[2]
           (地址/命令  (N-bit)    (N-bit)    (N-bit)
            /tag/vc)
                                              |
                                              v
                         ┌────────────────────────────────────┐
                         │       write req merge done         │
                         │   req_q[0]  +  data_q[0..N]        │
                         │   完整逻辑事务：地址、命令、数据    │
                         └────────────────────────────────────┘
                                    |
                                    v
                             Module Predictor
                         （将完整事务送往 scoreboard）
```

Monitor 用两个队列分开积累：
- `req_q[]`：存 header beat（地址、命令、tag、VC）
- `data_q[]`：存 data beat（固定位宽，按拍顺序排列）

当最后一个 data beat 到达时，monitor 打印 merge done 日志，将 `req_q[0]` 和全部 `data_q` 拼成一笔逻辑事务上报。

### 1.3 命令码（_cmd）

`_cmd` 字段编码了事务的操作类型。读命令和写命令各占一段不连续的编码空间，monitor 通过判断 `_cmd` 是否落在读范围或写范围来决定是否等待 data beat：

- **读命令**：无 data beat，header 到达后立即合并完成
- **写命令**：有 data beat，需等到所有 data beat 到齐才触发合并

具体编码值由协议规范定义，日志中可直接读取 `_cmd` 字段识别类型。

### 1.4 日志示例

日志会打印本次合并涉及的队列项和事务元信息，以 `read/write req merge done` 结尾作为合并完成的标志。

读请求只有 `req_q[0]`，无 `data_q` 项；写请求会同时列出 `req_q[0]` 和所有 `data_q` 项，并附上数据内容——这是两者在日志中最直观的区别。

---

## 二、Type 2 — Register Read Merge（RAL Reg Predictor）

### 2.1 为什么需要寄存器响应合并

Type 1 Merge 完成后，一笔完整的逻辑事务被送到 predictor。如果这笔事务是一次覆盖多个物理寄存器的宽位读（例如 8 字节读跨两个 4 字节寄存器），UVM 内置的 `uvm_reg_predictor` 每次只能处理**一个寄存器**，必须把原始事务拆开分别预测，再把结果合并回来。

这就是 Type 2 Merge 的职责：**拆（Split）→ 预测（Predict）→ 合（Merge）**。

### 2.2 整体三段流水

```
  Type 1 Merge 输出的逻辑事务
       |
       |  bus_in (analysis imp)
       v
  +-------------------------------------------------+
  |              write_bus_in()                     |
  |                                                 |
  |  (1) 克隆原始事务                               |
  |  (2) 按覆盖范围拆成 N 笔单寄存器子事务          |
  |  (3) N 份克隆体压入 pending_q                   |
  |  (4) 逐笔送入 UVM 内置 predictor                |
  +-------------------+-----------------------------+
                      |  N 笔单寄存器事务
                      v
  +-------------------------------------------------+
  |       uvm_reg_predictor（UVM 内置）             |
  |                                                 |
  |  对每笔子事务：                                 |
  |    按地址查找寄存器                             |
  |    rg.predict() -> 更新镜像                     |
  |    回调 handle_rsp() -> 通知结果                |
  +-------------------+-----------------------------+
                      |  N 次回调，每次一个寄存器
                      v
  +-------------------------------------------------+
  |                handle_rsp()                     |
  |                                                 |
  |  每次回调：                                     |
  |    (1) pop pending_q（计数减一）                |
  |    (2) 取该寄存器 mirrored 值                   |
  |    (3) 字节移位后写入 reg_array[idx]            |
  |    (4) 若 pending_q 已空 -> 合并完成            |
  |        reg_ap.write(reg_item) -> Scoreboard     |
  +-------------------+-----------------------------+
                      |
                      v
          Scoreboard / Checker
```

### 2.3 关键数据结构

| 变量 | 用途 |
|---|---|
| `pending_q` | 追踪"已发出但还没回调"的子事务，队列长度 = 剩余待合并数 |
| `reg_value` | 当前 DWORD 槽的累积合并值 |
| `reg_array[]` | 所有 DWORD 槽的最终合并结果，按槽发给 scoreboard |
| `start_reg_offset` | 原始事务的基地址，用于计算数组下标：`(reg_offset - start_reg_offset) >> 2` |

### 2.4 拆分阶段

按字节遍历原始事务覆盖范围，找到每个寄存器后克隆一份子事务，跳过该寄存器已覆盖的字节，继续向后查找：

```
for 每个字节 i in 事务覆盖范围:
    rg = 按地址查找寄存器(base + i)
    if rg 存在:
        克隆子事务，地址设为 rg 的地址
        push 到 split_trans_q
        i 跳过 rg 的宽度（避免重复处理）
```

`get_real_reg()` 会透明穿透 replica 和 indirect 类型的寄存器，保证后续操作拿到的是真实寄存器对象。

### 2.5 合并阶段：字节对齐逻辑

**DWORD 对齐寄存器**（最常见，寄存器地址低 2 位为 0）：

```
reg_value  = mirrored_value          // 无需移位
reg_array[槽号] = reg_value
```

**非 DWORD 对齐寄存器**（寄存器地址低 2 位非零）：

寄存器起始字节不在 DWORD 边界上，其值需要左移 `(偏移字节数 × 8)` 位才能落到正确的位置。若同时跨越两个 DWORD 槽，还需要从上一槽进位：

```
shift    = (reg_offset & 0x3) * 8
reg_value = 上一槽进位值 + (mirrored_value << shift)
reg_array[槽号] = reg_value
```

直观理解：`reg_array` 里每个槽代表总线响应中一个完整 DWORD 的字节视图，非对齐寄存器的字节需要"移到它应该在的位置"才能拼成正确的响应。

### 2.6 待定队列状态机

```
初始         write_bus_in()           第 1 次回调           第 2 次回调
  size=0  ──→  size=2 (push A, B)  ──→  size=1 (pop A)  ──→  size=0 (pop B)
                                                                    |
                                                           合并完成，发布结果
                                                           reg_ap.write(reg_item)
```

队列里保存的是子事务克隆体，每次 pop 时会做地址断言——顺序或地址不对会立即报错，不会静默合并出错误值。

### 2.7 写路径：Byte Enable 为 0 时的填充

写事务允许只写部分字节（BE=0 的字节硬件保持原值）。但 UVM RAL 的 `predict()` 需要接收完整的写数据才能正确更新镜像。

做法：**用当前镜像值填充 BE=0 的字节，并强制将这些字节的 BE 置为 1**，使 UVM RAL 看到的始终是全字节有效的完整写。

```
原始写数据：  [ 新值,  屏蔽,  新值,  屏蔽 ]
byte_enable：  [  1,     0,    1,     0  ]
当前镜像值：  [ --,   镜像B, --,   镜像D ]

填充后送 RAL：[ 新值, 镜像B, 新值, 镜像D ]   BE = all-1
```

### 2.8 日志字段速查

| 日志字段 | 含义 |
|---|---|
| 事务基地址 | 原始事务的起始地址，即 `start_reg_offset` |
| 寄存器命中提示 | 在某字节偏移找到了寄存器，split 计数 +1 |
| `read back value` | 当前子事务对应寄存器的原始镜像值（未移位） |
| `merged read back value` | 移位累积后的合并值 |
| 字节偏移量 | `reg_offset - start_reg_offset`，用于定位槽号 |
| `pending trans cleared` | pending_q 清空，Type 2 合并完成，结果发往 scoreboard |

### 2.9 两个特殊情况

**无语义寄存器**：某些寄存器在特定访问路径下硬件无明确语义，predictor 强制将其值置 0，避免无意义的镜像值污染 scoreboard 比对结果。

**未映射地址**：地址查找返回空时，直接构造全零假响应发给 scoreboard，跳过整个 Split-Merge 流程，防止 scoreboard 挂起。

---

## 三、总结

两种 Merge 处于流水线的不同层次，解决不同的问题：

**Type 1（Monitor 层）**：把物理接口上碎片化的 beat 还原成人类可理解的逻辑事务。没有它，predictor 和 scoreboard 看到的只是没有意义的半截信号。

**Type 2（RAL Predictor 层）**：把 UVM RAL 对单个寄存器的分批预测结果重新组装成与原始总线事务等宽的响应。没有它，scoreboard 拿到的是残缺的、寄存器粒度的碎片，无法与总线级响应做正确比对。

两者串联：Type 1 的输出是 Type 2 的输入。一笔物理上的多 beat 写请求，先经过 monitor 的 beat 合并变成一笔逻辑写事务，再经过 predictor 的 split-merge 完成寄存器级别的预测，最终一个完整的预测结果送达 scoreboard。

下次看到仿真日志里的 merge 相关输出，先认清它属于哪一层：

```
write req merge done      <-- Type 1，Monitor 层，beat 拼装完成
pending trans cleared     <-- Type 2，RAL Predictor 层，寄存器响应合并完成
```
