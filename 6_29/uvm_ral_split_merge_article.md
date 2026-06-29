# UVM 验证环境中的两种 Merge 模式

## 从总线 Beat 合并到跨寄存器响应合并

*芯片验证 · UVM · Register Model · Monitor · Predictor · Merge*

---

> **系列导读**
>
> 本文是三篇系列文章的**番外篇**，聚焦于验证环境中反复出现的"Merge"概念：
> 1. reg model 基础原理与工程实践（**建议先读**）
> 2. Callback 机制：在读写流程中插入自定义逻辑
> 3. predict(DIRECT)：Lock bit 场景下的 scoreboard 误报修复
> 4. **本文**：两种 Merge——beat 合并与寄存器响应合并
>
> **前置知识**：建议先了解 UVM reg model 的 `desired`/`mirrored` 机制和 `uvm_reg_predictor` 的工作原理（见第一篇）。

---

**读完本文，你将理解**：

- 验证日志里"merge done"出现在两个完全不同的地方，各自解决什么问题
- Type 1：monitor 如何把物理接口上的多个 beat 拼装成一笔逻辑事务
- Type 2：RAL predictor 如何把拆分的寄存器子事务重新合并成完整响应
- 两种 Merge 在整个仿真流水中的位置和协作关系

---

**摘要**：在 hphost 验证环境的 `vcs_run.log` 中，"merge done"这个词出现在两个截然不同的上下文里。第一种出现在 `hphost_module_monitor.svh`，指的是把物理总线上多个时钟周期的 beat 拼成一笔完整的逻辑请求；第二种出现在 `hphost_ral_reg_predictor.svh`，指的是把 UVM RAL 针对多个寄存器的分批预测结果合并成一个完整的寄存器响应。两种 Merge 在流水线的不同层次各司其职，缺一不可。

---

## 零、全局视角：两种 Merge 在哪里

```
  IOHub 物理接口
       |
       |  多个 beat（HDR + DATA[0..N]）
       v
  ┌─────────────────────────────────┐
  │   hphost_module_monitor.svh     │
  │                                 │
  │   req_q[] + data_q[]            │
  │   beat by beat 累积             │──→ "read/write req merge done"
  │   最后一个 DATA beat 到达后     │       (Type 1)
  │   合并为一笔逻辑事务            │
  └──────────────┬──────────────────┘
                 |
                 v
  ┌──────────────────────────────────────────────────────┐
  │   hphost_module_predictor                            │
  │                                                      │
  │          ┌──────────────────────────────────────┐   │
  │          │   hphost_ral_reg_predictor.svh        │   │
  │          │                                      │   │
  │          │   split → UVM RAL → merge            │   │
  │          │   m_split_pending_q 追踪进度          │──→ "pending trans cleared"
  │          │   m_reg_array 累积各寄存器值           │       (Type 2)
  │          └──────────────────────────────────────┘   │
  └──────────────┬───────────────────────────────────────┘
                 |
                 v
        Scoreboard（期望值 vs 实际值比对）
```

**一句话区分**：

| | Type 1 | Type 2 |
|---|---|---|
| 所在文件 | `hphost_module_monitor.svh` | `hphost_ral_reg_predictor.svh` |
| 合并对象 | 物理接口上的多个 beat | 多个寄存器的预测子事务 |
| 触发条件 | 最后一个 DATA beat 到达 | m_split_pending_q 清空 |
| 日志关键词 | `read/write req merge done` | `pending trans cleared` |

---

## 一、Type 1 — Request Merge（hphost_module_monitor.svh）

### 1.1 为什么需要 Beat 合并

物理总线（IOHUB → HPHOST）上，一笔逻辑请求可能分多个时钟周期传输：

- **第 1 拍**：Header beat，携带地址、命令码、tag、VC 等控制信息
- **第 2–N 拍**：Data beat，每拍 128 bit，携带写数据（读请求没有 data beat）

Monitor 采样到的是原始物理信号，每拍看到的都是不完整的碎片。只有把所有 beat 拼在一起，才能得到一笔有意义的逻辑事务，才能送给 predictor 做预测和 scoreboard 做比对。

### 1.2 Beat 合并流程

```
  物理接口（IOHUB → HPHOST）
  ──────────────────────────────────────────────────────
  时钟周期：    1          2          3          4
               |          |          |          |
  Beat：   [HDR beat] [DATA[0]]  [DATA[1]]  [DATA[2]]
               |          |          |          |
               v          v          v          v
           req_q[0]   data_q[0]  data_q[1]  data_q[2]
           (unit=5ee  (128-bit)  (128-bit)  (128-bit)
            tag=78f
            _cmd=30)
                                              |
                                              v
                         ┌────────────────────────────────────┐
                         │       write req merge done         │
                         │  req_q[0]  data_q[0..2]            │
                         │  unit 5ee  tag 78f  _cmd 30  _vc 0 │
                         │  data is xxxxxxxx                  │
                         └────────────────────────────────────┘
                                    |
                                    v
                         hphost_module_predictor
                         （将完整事务送往 scoreboard）
```

Monitor 用两个队列分开积累：
- `req_q[]`：存 header beat（地址、命令、tag、VC）
- `data_q[]`：存 data beat（128-bit 宽，按拍顺序排列）

当最后一个 data beat 到达时，monitor 打印 merge done 日志，将 `req_q[0]` 和全部 `data_q` 拼成一笔逻辑事务上报。

### 1.3 命令码（_cmd）速查

| _cmd 值 | 事务类型 | 方向 |
|---|---|---|
| 03、04、13 | Read request | IOHub → HPHost |
| 28、29、2c–2e、30、31 | Write request | IOHub → HPHost |

读请求没有 data beat，header 到达即合并完成。写请求需要等到所有 data beat 到齐。

### 1.4 日志示例

```
# 读请求（header 即完整，无 data beat）
req_q[0] unit 296 tag 85b _cmd 4 _vc 0, read req merge done

# 写请求（等到最后一个 data beat 到达后）
req_q[0] data_q[0] unit 5ee tag 78f _cmd 30 _vc 0, write req merge done, data is xxxxxxxx
```

读请求日志只有 `req_q[0]`，写请求日志中能看到 `data_q[0]`（以及更多 data_q 项）——这就是两者的直观区别。

---

## 二、Type 2 — Register Read Merge（hphost_ral_reg_predictor.svh）

### 2.1 为什么需要寄存器响应合并

Type 1 Merge 完成后，一笔完整的逻辑事务被送到 predictor。如果这笔事务是一次覆盖多个物理寄存器的宽位读（例如 8 字节读跨两个 4 字节寄存器），UVM 内置的 `uvm_reg_predictor` 每次只能处理**一个寄存器**，必须把原始事务拆开分别预测，再把结果合并回来。

这就是 Type 2 Merge 的职责：**拆（Split）→ 预测（Predict）→ 合（Merge）**。

### 2.2 整体三段流水

```
  Type 1 Merge 输出的逻辑事务
       |
       |  hphost_bus_in (analysis imp)
       v
  +-------------------------------------------------+
  |         write_hphost_bus_in()   [line 67]       |
  |                                                 |
  |  (1) 克隆原始事务                               |
  |  (2) split_trans_into_per_reg_acc()             |
  |      将一笔多寄存器事务拆成 N 笔单寄存器事务   |
  |  (3) N 份克隆体压入 m_split_pending_q           |
  |  (4) 逐笔写入 bus_in -> UVM 内置 predictor      |
  +-------------------+-----------------------------+
                      |  N 笔单寄存器事务
                      v
  +-------------------------------------------------+
  |       uvm_reg_predictor（UVM 内置）             |
  |                                                 |
  |  对每笔 split_trans：                           |
  |    map.get_reg_by_offset()  -> 找到寄存器      |
  |    rg.predict()             -> 更新镜像         |
  |    回调 write_reg_ap_imp()  -> 通知结果         |
  +-------------------+-----------------------------+
                      |  N 次回调，每次一个寄存器
                      v
  +-------------------------------------------------+
  |        handle_rsp()   [line 106]                |
  |                                                 |
  |  每次回调：                                     |
  |    (1) pop m_split_pending_q（计数减一）        |
  |    (2) 取该寄存器 mirrored 值                   |
  |    (3) 字节移位后写入 m_reg_array[idx]          |
  |    (4) 若 pending 队列已空 -> 合并完成          |
  |        hphost_reg_ap.write(reg_item) -> Scbd    |
  +-------------------+-----------------------------+
                      |
                      v
          Scoreboard / RAS Checker
```

### 2.3 关键数据结构

| 变量 | 用途 |
|---|---|
| `m_split_pending_q` | 追踪"已发出但还没回调"的 split 事务，队列长度 = 剩余待合并数 |
| `m_reg_value` | 当前 DWORD 槽的累积合并值 |
| `m_reg_array[256]` | 所有 DWORD 槽的最终合并结果，`value[0]` 发给 scoreboard |
| `start_reg_offset` | 原始事务的基地址，用于计算数组下标：`(reg_offset - start_reg_offset) >> 2` |

### 2.4 拆分阶段：split_trans_into_per_reg_acc()

按字节遍历原始事务覆盖范围，找到每个寄存器后克隆一份事务，步进 `reg_width` 字节跳到下一个寄存器：

```systemverilog
for (uint64 i = 0; i < gtrans.get_size(); i++) begin
    rg = map.get_reg_by_offset(reg_offset + i, is_read);
    if (rg) begin
        real_reg  = get_real_reg(rg, kind);   // 透明处理 replica/indirect
        reg_width = real_reg.get_n_bytes();

        $cast(splitted_trans, _trans.clone());
        splitted_trans.set_addr(reg_addr + i);

        split_trans_q.push_back(splitted_trans);
        i = i + reg_width - 1;   // 跳过已处理字节
    end
end
```

### 2.5 合并阶段：字节对齐逻辑

**DWORD 对齐寄存器**（最常见，`reg_offset & 0x3 == 0`）：

```
直接：m_reg_value = reg_value
存入：m_reg_array[(reg_offset - start_reg_offset) >> 2]
```

**非 DWORD 对齐寄存器**（`reg_offset & 0x3 != 0`）：

```
需要左移：m_reg_value = m_reg_value + (reg_value << ((reg_offset & 0x3) * 8))
跨槽时从上一槽进位：m_reg_value = m_reg_array[idx - 1]
```

核心代码（第 141–149 行）：

```systemverilog
if ((reg_offset & 'h3) != 0) begin
    if (reg_offset - start_reg_offset >= 4)
        m_reg_value = m_reg_array[(reg_offset - start_reg_offset) >> 2 - 1];
    m_reg_value = m_reg_value + (reg_value << ((reg_offset & 'h3) * 8));
end else begin
    m_reg_value = reg_value;
end
m_reg_array[(reg_offset - start_reg_offset) >> 2] = m_reg_value;
```

### 2.6 待定队列状态机

```
初始         write_hphost_bus_in()        1st handle_rsp()    2nd handle_rsp()
  size=0  ────→  size=2 (push A, B)  ──→  size=1 (pop A)  ──→  size=0 (pop B)
                                                                      |
                                                             合并完成，发布结果
                                                             hphost_reg_ap.write()
```

队列里保存的是事务克隆体，每次 pop 时会做 `trans_offset_addr == reg_offset` 断言——顺序或地址不对会立即报错，不会静默合并出错误值。

### 2.7 写路径：Byte Enable 为 0 时的填充

写事务中 BE=0 的字节用当前镜像值填充，并强制 BE 置 1，保证 UVM RAL 接受完整写：

```
write_data  = [ 0x12, 0x34, 0x56, 0x78 ]
byte_enable = [  1,    0,    1,    0   ]
mirror      = 0xAABBCCDD

填充后送 RAL：[ 0x12, 0xCC, 0x56, 0xAA ]   BE = all-1
                ^      ^     ^     ^
              新值   镜像  新值  镜像
```

### 2.8 日志字段速查

| 日志字段 | 含义 |
|---|---|
| `real addr is N` | `start_reg_offset`，原始事务的基地址 |
| `register exist at offset=0xXXXX` | 在该字节偏移找到了寄存器，split 计数 +1 |
| `read back value` | `rg.get_mirrored_value()` 原始镜像值（未移位） |
| `merged read back value` | 移位累积后的 `m_reg_value` |
| `m_reg_index` | `reg_offset - start_reg_offset`（字节数，非槽号） |
| `rsp merged data[0]` | `m_reg_array[0]`，最终合并 DWORD[0] |
| `pending trans cleared` | 队列清空，Type 2 合并完成，结果发往 scoreboard |

### 2.9 两个特殊情况

**HPHST_FLUSH_DATA_DW0**：SMN 读该寄存器的值硬件无语义，predictor 强制返回 0，避免无意义的镜像值污染 scoreboard。

**未映射地址**：`get_reg_by_offset()` 返回 null 时，`gen_rsp_for_reserved_addr()` 直接构造 `value=0` 的假响应发给 scoreboard，跳过整个 Split-Merge 流程，防止 scoreboard 挂起。

---

## 三、总结

两种 Merge 处于流水线的不同层次，解决不同的问题：

**Type 1（monitor 层）**：把物理接口上碎片化的 beat 还原成人类可理解的逻辑事务。没有它，predictor 和 scoreboard 看到的只是没有意义的半截信号。

**Type 2（predictor 层）**：把 UVM RAL 对单个寄存器的分批预测结果重新组装成与原始总线事务等宽的响应。没有它，scoreboard 拿到的是残缺的、寄存器粒度的碎片，无法与总线级响应做正确比对。

两者串联：Type 1 的输出是 Type 2 的输入。一笔物理上的多 beat 写请求，先经过 monitor 的 beat 合并变成一笔逻辑写事务，再经过 predictor 的 split-merge 完成寄存器级别的预测，最终一个完整的预测结果送达 scoreboard。

下次看到 `vcs_run.log` 里的 merge 相关日志，先认清它属于哪一层：

```
write req merge done          <-- Type 1，monitor 层，beat 拼装完成
pending trans cleared         <-- Type 2，predictor 层，寄存器响应合并完成
```

---

*本文源码参考：*
*`src/verif/uvc/hphost_module_uvc/sv/hphost_module_monitor.svh`*
*`src/verif/uvc/hphost_reg_ral_uvc/sv/hphost_ral_reg_predictor.svh`*
*文档参考：`scripts/genie/merge_explanation.md`*
