# UVM RAL Predictor 的 Split-Merge 模式

## 跨寄存器总线事务的拆分、预测与合并

*芯片验证 · UVM · Register Model · Predictor · Split-Merge*

---

> **系列导读**
>
> 本文是三篇系列文章的**番外篇**，聚焦于工程实践中的一个具体难题：
> 1. reg model 基础原理与工程实践（**建议先读**）
> 2. Callback 机制：在读写流程中插入自定义逻辑
> 3. predict(DIRECT)：Lock bit 场景下的 scoreboard 误报修复
> 4. **本文**：Split-Merge——当一笔总线事务跨越多个寄存器时怎么办
>
> **前置知识**：阅读本文前，建议先了解 UVM reg model 的 `desired`/`mirrored` 机制、`uvm_reg_predictor` 的工作原理（见第一篇）。核心概念速查：
> - `mirrored`：reg model 对硬件当前状态的认知镜像，scoreboard 预测基于此
> - `uvm_reg_predictor`：UVM 内置的预测器，监听总线事务并调用 `rg.predict()` 更新镜像
> - `analysis port / imp`：UVM 组件间单向传播数据的机制，predictor 通过它接收事务、发布结果

---

**读完本文，你将理解**：

- 为什么 UVM 内置 `uvm_reg_predictor` 无法直接处理跨寄存器事务
- Split-Merge 模式的完整设计：拆分、预测、合并的三段流水
- `m_split_pending_q` 是如何充当"进度追踪器"的
- 非 DWORD 对齐寄存器的字节移位合并逻辑
- 写路径下 Byte Enable 为 0 时如何用镜像值填充保证 RAL 接受完整写
- 未映射地址的兜底处理

---

**摘要**：现代总线（如 AXI）支持跨越多个物理寄存器的单笔突发事务，但 UVM 内置的 `uvm_reg_predictor` 每次只能处理一个寄存器。`hphost_ral_reg_predictor` 通过 Split-Merge 模式解决这一矛盾：将原始事务拆分为若干单寄存器访问，分别送入 UVM RAL 完成预测，再将所有预测结果合并成一个与原始事务等宽的响应，发布给 scoreboard。理解这个模式，是读懂复杂验证环境中 `vcs_run.log` 的关键。

> **本文代码均为 SystemVerilog（SV），运行在 UVM 仿真环境中。**
> 代码片段来自 `hphost_ral_reg_predictor.svh`，省略了部分辅助细节，聚焦于核心逻辑。

---

## 零、一分钟背景：问题从哪里来

**总线事务的粒度不等于寄存器的粒度。**

REGIF 总线（如 AXI）允许一笔事务跨越多个物理寄存器。比如一次 8 字节的突发读，地址从 `0x6200` 开始，可能覆盖：

```
addr 0x6200  ->  REG_A  (4 bytes)
addr 0x6204  ->  REG_B  (4 bytes)
```

UVM 内置的 `uvm_reg_predictor` 是为**单寄存器访问**设计的：它接收一笔事务，查找对应的寄存器，调用 `rg.predict()` 更新镜像，再将 `uvm_reg_item` 发给 scoreboard。

一笔跨越两个寄存器的事务，它只能处理其中一个。

结果是：scoreboard 收到的预测值不完整，要么漏掉了高半段，要么拿到的是错误的寄存器镜像——两种情况都会导致误报或漏报。

**`hphost_ral_reg_predictor` 是对 `uvm_reg_predictor` 的封装和增强**，专门解决这个问题。它的核心设计叫做 **Split-Merge 模式**。

---

## 一、整体架构：三段流水

```
  REGIF Bus Monitor
       |
       |  hphost_bus_in (analysis imp)
       v
  +-------------------------------------------------+
  |         write_hphost_bus_in()   [line 67]       |
  |                                                 |
  |  (1) 克隆原始事务                               |
  |  (2) 调用 split_trans_into_per_reg_acc()        |
  |      将一笔多寄存器事务拆成 N 笔单寄存器事务   |
  |  (3) 把 N 份克隆体压入 m_split_pending_q        |
  |  (4) 逐笔写入 bus_in -> UVM 内置 predictor      |
  +-------------------+-----------------------------+
                      |  N 笔单寄存器事务
                      v
  +-------------------------------------------------+
  |       uvm_reg_predictor（UVM 内置）             |
  |                                                 |
  |  对每笔 split_trans：                           |
  |    map.get_reg_by_offset()  -> 找到对应寄存器  |
  |    rg.predict()             -> 更新 UVM 镜像   |
  |    回调 write_reg_ap_imp()  -> 通知我们结果    |
  +-------------------+-----------------------------+
                      |  N 次回调，每次一个寄存器
                      v
  +-------------------------------------------------+
  |        write_reg_ap_imp() -> handle_rsp()       |
  |                            [line 100 / 106]     |
  |                                                 |
  |  每次回调：                                     |
  |    (1) pop m_split_pending_q（计数减一）        |
  |    (2) 取该寄存器 mirrored 值                   |
  |    (3) 字节移位后写入 m_reg_array[idx]          |
  |    (4) 若 pending 队列已空 -> 合并完成          |
  |        reg_item.value = m_reg_array             |
  |        hphost_reg_ap.write(reg_item) -> Scbd    |
  +-------------------+-----------------------------+
                      |
                      v
          Scoreboard / RAS Checker
```

三段流水一句话概括：**拆（Split）-> 预测（Predict）-> 合（Merge）**。

---

## 二、关键数据结构

在 `hphost_ral_reg_predictor.svh` 第 37–47 行声明了以下几个核心变量：

| 变量 | 类型 | 用途 |
|---|---|---|
| `m_split_pending_q` | 事务队列 | 追踪"已发出但还没收到回调"的 split 事务，队列长度 = 剩余待合并数 |
| `m_original_trans_q` | 事务队列 | 保存原始事务，用于写路径的 BE 填充 |
| `wr_split_trans_q` | 事务队列 | 保存写路径 split 事务（含原始 byte enable） |
| `rd_split_trans_q` | 事务队列 | 保存读路径 split 事务 |
| `m_reg_value` | 64-bit | 当前 DWORD 槽的累积合并值 |
| `m_reg_array[256]` | 64-bit 数组 | 所有 DWORD 槽的最终合并结果 |
| `start_reg_offset` | uint64 | 原始事务的基地址（DWORD 边界），用于计算数组下标 |

**`m_reg_array` 的下标计算逻辑**：

```
start_reg_offset = 0x6200   // 原始事务的基地址

数组下标 = (当前寄存器偏移 - start_reg_offset) >> 2

offset 0x6200  ->  (0x6200 - 0x6200) >> 2 = 0  -> m_reg_array[0]
offset 0x6204  ->  (0x6204 - 0x6200) >> 2 = 1  -> m_reg_array[1]
offset 0x6208  ->  (0x6208 - 0x6200) >> 2 = 2  -> m_reg_array[2]
```

每个数组槽对应一个 DWORD（4 字节）。如果寄存器不是 DWORD 对齐的，它的字节会被移位后叠加到对应槽里——后面第四节详细讲这个。

---

## 三、拆分阶段：split_trans_into_per_reg_acc()

函数在第 177 行，核心逻辑如下：

```systemverilog
// 遍历原始事务覆盖的每个字节
for (uint64 i = 0; i < gtrans.get_size(); i++) begin
    rg = map.get_reg_by_offset(reg_offset + i, is_read);
    if (rg) begin
        real_reg = get_real_reg(rg, kind);  // 处理 replica/indirect 寄存器
        reg_width = real_reg.get_n_bytes();

        // 克隆一份事务，地址设为该寄存器的地址
        $cast(splitted_trans, _trans.clone());
        splitted_trans.set_addr(reg_addr + i);

        // 提取该寄存器对应字节范围内的 byte enable
        for (uint j = 0; j < real_reg.get_n_bytes(); j++)
            be.set_be(j, rd_be.get_be(i + j));

        split_trans_q.push_back(splitted_trans);
        i = i + reg_width - 1;  // 跳过已处理的字节，避免重复
    end
end
```

关键点有两个：

**1. 按字节查寄存器，按寄存器宽度跳步。** 不是每个字节都查一次然后丢弃重复的，而是找到寄存器后直接跳 `reg_width - 1` 字节，效率准确。

**2. `get_real_reg()` 透明处理 replica 和 indirect 寄存器。** 有些寄存器是"副本"（replica_reg）或"间接寻址"（indirect_data_reg），`get_real_reg()` 会穿透到真正的寄存器对象，保证后续的镜像读取和地址比对是正确的。

---

## 四、合并阶段：handle_rsp() 的字节对齐逻辑

每次 UVM 内置 predictor 完成一个寄存器的预测，都会回调 `write_reg_ap_imp()`，进而调用 `handle_rsp()`。这里是 Merge 的核心。

### 情形 A：DWORD 对齐的寄存器（最常见）

```
总线事务：MEM_RD @ 0x621C，size = 4 bytes

start_reg_offset = 0x621C

寄存器 HPHOST_SDP_DEBUG_COUNTER_CTRL：
  offset = 0x621C，width = 4 bytes

对齐检查：0x621C & 0x3 = 0  -> DWORD 对齐

合并计算（第 145-146 行）：
  m_reg_value = reg_value   // 无需移位，直接取镜像值

数组下标（第 149 行）：
  idx = (0x621C - 0x621C) >> 2 = 0
  m_reg_array[0] = m_reg_value
```

日志中看到的：

```
read back value        = 0x0000000000000000  <- get_mirrored_value() 原始值
merged read back value = 0x0000000000000000  <- m_reg_value（无移位，与前者相同）
m_reg_index            = 0                   <- (0x621C - 0x621C) = 0 字节偏移
```

### 情形 B：非 DWORD 对齐的寄存器（字节移位）

```
总线事务：MEM_RD @ 0x6200，size = 8 bytes
覆盖两个寄存器：
  REG_LO @ 0x6200  (4 bytes，DWORD 对齐)
  REG_HI @ 0x6205  (1 byte，非对齐：0x6205 & 0x3 = 1)

start_reg_offset = 0x6200

--- 第一次回调：REG_LO @ 0x6200 ---
  reg_value   = 0x00000012
  对齐检查：0x6200 & 0x3 = 0  -> 对齐
  m_reg_value = 0x00000012
  idx = (0x6200 - 0x6200) >> 2 = 0
  m_reg_array[0] = 0x00000012

--- 第二次回调：REG_HI @ 0x6205 ---
  reg_value   = 0x000000AB
  对齐检查：0x6205 & 0x3 = 1  -> 不对齐
  移位位数 = 1 * 8 = 8 bits

  因为 (0x6205 - 0x6200) = 5 >= 4，进入新的 DWORD 槽：
    idx = (0x6205 - 0x6200) >> 2 = 1
    m_reg_value = m_reg_array[0] = 0x00000012（从上一槽进位）

  m_reg_value = m_reg_value + (reg_value << 8)
              = 0x00000012 + (0x000000AB << 8)
              = 0x00000012 + 0x0000AB00
              = 0x0000AB12

  m_reg_array[1] = 0x0000AB12

  字节布局：
    Bit [15:8]  = 0xAB   <- REG_HI 的值
    Bit [7:0]   = 0x12   <- 从 m_reg_array[0] 进位的 REG_LO 低字节
```

核心代码（第 141–149 行）：

```systemverilog
if ((reg_offset & 'h3) != 0) begin
    // 非 DWORD 对齐：从上一槽取进位值，移位后叠加
    if (reg_offset - start_reg_offset >= 4)
        m_reg_value = m_reg_array[(reg_offset - start_reg_offset) >> 2 - 1];
    m_reg_value = m_reg_value + (reg_value << ((reg_offset & 'h3) * 8));
end else begin
    // DWORD 对齐：直接取镜像值，无需移位
    m_reg_value = reg_value;
end
m_reg_array[(reg_offset - start_reg_offset) >> 2] = m_reg_value;
```

**设计意图**：`m_reg_array` 中每个槽是一个 64-bit DWORD 的完整视图。如果一个寄存器在 DWORD 内有字节偏移，它的值要左移相应位数才能落到正确的字节位置上。而非对齐寄存器可能横跨两个 DWORD 槽，所以合并时需要"进位"——把上一槽的低字节带入当前槽。

---

## 五、待定队列：m_split_pending_q 的状态机

`m_split_pending_q` 是整个 Split-Merge 能够正确判断"所有拆分都处理完了"的关键。

```
初始状态
+--------------------+
|  m_split_pending_q |  size = 0
+--------------------+

write_hphost_bus_in() 执行后（2 个 split 入队）
+----------------------+
|  [split_A] [split_B] |  size = 2
+----------------------+

第 1 次 handle_rsp() 回调 -> pop_front()
+----------------------+
|             [split_B] |  size = 1
+----------------------+
-> size != 0，继续等待，不发布结果

第 2 次 handle_rsp() 回调 -> pop_front()
+--------------------+
|                    |  size = 0
+--------------------+
-> size == 0，合并完成！
   reg_item.value = m_reg_array
   hphost_reg_ap.write(reg_item)   // 通知 scoreboard
   重置：m_reg_value=0, m_reg_array.delete(), start_reg_offset=0
```

为什么用队列而不用计数器？因为队列里保存的是事务克隆体，`handle_rsp()` 可以从中取出对应的地址信息，做 `trans_offset_addr == reg_offset` 的断言验证——**顺序不对或者地址不匹配，立即报错**，而不是默默地合并出错误的值。

---

## 六、写路径：Byte Enable 为 0 时怎么办

读路径只需要从镜像取值然后移位合并。写路径多一个难题：**Byte Enable（字节使能）**。

总线事务允许只写部分字节（BE=0 的字节保持原值）。但 UVM RAL 的 `predict()` 接口期望接收的是完整的、有意义的写数据。如果直接把 BE=0 的字节对应位置填 0，RAL 会把寄存器那些字段更新为 0——与硬件行为不符。

`split_trans_into_per_reg_acc()` 的写路径（第 207–279 行）的做法：**用当前镜像值填充 BE=0 的字节，并强制把那些字节的 BE 置为 1。**

```
总线事务：MEM_WR @ 0x00B4，size = 4 bytes
  write_data  = [ 0x12, 0x34, 0x56, 0x78 ]
  byte_enable = [  1,    0,    1,    0   ]
                   ^           ^
                 有效         有效
                        ^           ^
                       屏蔽        屏蔽

当前镜像值：rg.get_mirrored_value() = 0xAABBCCDD

填充逻辑：
  j=0: BE[0]=1 -> 保留原始数据 0x12
  j=1: BE[1]=0 -> 从镜像取  0xCC（mirror[15:8]），并强制 BE[1]=1
  j=2: BE[2]=1 -> 保留原始数据 0x56
  j=3: BE[3]=0 -> 从镜像取  0xAA（mirror[31:24]），并强制 BE[3]=1

最终写入 UVM RAL 的数据：
  [ 0x12, 0xCC, 0x56, 0xAA ]   BE = all-1
     ^      ^     ^     ^
   新值   镜像  新值  镜像
```

这样 UVM RAL 看到的是"全字节有效的完整写"，镜像更新正确。Scoreboard 检查的是硬件实际应该写入的值，两者对齐。

日志中的线索：

```
[REG_ACCESS]: wr byte en is 0
[REG_ACCESS] trans type = WR, register exist at offset = 0x000000000000b4
[REG_PREDICT] Observed WRITE transaction to register ...RCC_AD_MISC5: value='h4
```

第一行说明遇到了 BE=0 的情况，后面的 predict 日志说明填充后 RAL 接受了完整写并更新了镜像。

---

## 七、两个特殊情况

### 7.1 HPHST_FLUSH_DATA_DW0 的硬编码清零

`handle_rsp()` 第 136–138 行有一处特判：

```systemverilog
if (rg.get_name() == "HPHST_FLUSH_DATA_DW0") begin
    reg_value = 0;  // SMN 对 FLUSH_DATA 寄存器的访问没有实际意义
end
```

SMN 从 `FLUSH_DATA` 寄存器读回的值在硬件上没有定义语义，predictor 直接固定返回 0，避免把无意义的镜像值传给 scoreboard 引发误报。这是一种**主动防御**的设计：比起让 scoreboard 对一个语义未定义的值做判断，预测器直接屏蔽掉噪声更稳健。

### 7.2 未映射地址的兜底：gen_rsp_for_reserved_addr()

如果遍历完所有字节，`map.get_reg_by_offset()` 始终返回 null（地址不在任何寄存器的映射范围内），拆分结果为空。这时不能让事务石沉大海，scoreboard 会挂起。

`gen_rsp_for_reserved_addr()`（第 337 行）直接构造一个 `value=0` 的假响应，跳过整个 Split-Merge 流程，直接发给 scoreboard：

```systemverilog
function void gen_rsp_for_reserved_addr(bit is_read);
    uvm_reg_item reg_item = new;
    reg_item.path     = UVM_PREDICT;
    reg_item.value[0] = 0;          // 保留地址，返回全零
    reg_item.kind     = is_read ? UVM_READ : UVM_WRITE;
    hphost_reg_ap.write(reg_item);  // 直接发布，不经过合并
endfunction
```

---

## 八、日志字段速查表

读 `vcs_run.log` 时，以下字段对应的代码位置和含义：

| 日志字段 | 来源变量 | 代码行 | 含义 |
|---|---|---|---|
| `real addr is N` | `reg_offset` | 200 | 原始事务的基地址，即 `start_reg_offset` |
| `register exist at offset=0xXXXX` | `reg_offset + i` | 317 | 在该字节偏移处找到了寄存器 |
| `push back to m_split_trans_q` | `split_trans_q.push_back()` | 321 | 一笔 split 加入队列，pending 计数 +1 |
| `Observed READ/WRITE transaction` | UVM 内置 | 245 | UVM RAL 已更新镜像 |
| `write_reg_ap_imp: write trans` | 回调入口 | 101 | handle_rsp() 即将被调用 |
| `read back value` | `rg.get_mirrored_value()` | 134 | 该寄存器的原始镜像值（未移位） |
| `merged read back value` | `m_reg_value` | 150 | 移位并累积后的合并值 |
| `m_reg_index` | `reg_offset - start_reg_offset` | 150 | 字节偏移量（注意：是字节数，不是 >> 2 后的槽号） |
| `rsp merged data[0]` | `m_reg_array[0]` | 162 | 最终合并结果的第 0 个 DWORD |
| `pending trans cleared` | `m_split_pending_q.size() == 0` | 171 | 所有 split 处理完毕，合并完成 |
| `write rsp reg_item to nbif_reg_ap` | `hphost_reg_ap.write()` | 172 | 合并结果发布给 scoreboard |

---

## 九、一个常见困惑：为什么日志里 m_reg_index 总是 0

在 `hphost_flush_hst_random_aper_14_hphost_all_rtl` 这个测试的日志里，每一条 `reg read` 的日志都显示 `m_reg_index=0`，并且 `read back value` 与 `merged read back value` 完全相同。

这并不是 bug，而是这个测试的访问模式决定的：

- 该测试的所有总线事务都是 **4 字节 DWORD 对齐的单寄存器访问**
- 拆分始终只产生 **1 笔** split 事务
- pending 队列的节奏是：0 -> 1 -> 0，每次访问都立刻完成
- `m_reg_array[0]` 是唯一被用到的槽
- 字节移位逻辑从未触发（走的是 `m_reg_value = reg_value` 的 else 分支）

Split-Merge 的完整机制全部存在，只是没有被这个测试激活。要触发非对齐多寄存器的合并路径，需要构造一个跨越两个寄存器边界的 8 字节读，或者访问一个字节偏移不为 0 的寄存器。

---

## 十、总结

Split-Merge 模式解决了"总线事务粒度与寄存器粒度不匹配"这一验证基础问题。它的优雅之处在于：

- **对 UVM RAL 完全透明**：UVM 内置 predictor 看到的永远是单寄存器事务，无需任何修改
- **状态追踪极简**：一个队列（`m_split_pending_q`）同时承担了计数器、地址验证、顺序保证三个职责
- **字节对齐问题本地化**：移位合并逻辑只在 `handle_rsp()` 一处，调试路径清晰
- **防御性兜底**：未映射地址和特殊寄存器都有明确的处理分支，不会让 scoreboard 挂起

下次在 `vcs_run.log` 里看到一连串 `[REG_ACCESS] push back to m_split_trans_q` 后跟着 `pending trans cleared`，就是 Split-Merge 在正常运转的证明。

---

*本文源码参考：`src/verif/uvc/hphost_reg_ral_uvc/sv/hphost_ral_reg_predictor.svh`*
*文档参考：`scripts/genie/merge_explanation.md`*
