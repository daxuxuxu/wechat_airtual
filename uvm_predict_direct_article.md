# UVM Reg Model Mirror 失步

## Lock Bit 场景下的 Scoreboard 误报分析与修复

*芯片验证 · UVM · Scoreboard · 寄存器模型*

---

> **系列导读**
>
> 本文是三篇系列文章的**第三篇**：
> 1. 📖 reg model 基础原理与工程实践（**建议先读**，理解 desired/mirrored/auto-predict）
> 2. 📖 Callback 机制（**建议先读**，理解 lock_keep Callback 的作用）
> 3. 📖 **本文**：predict(DIRECT) 的精确语义与应用场景
>
> **前置知识速查**：
> - `mirrored`：reg model 对 HW 当前状态的认知，scoreboard 预测基于此
> - `auto-predict`：`write()` 后自动更新 mirrored，假设写入一定成功
> - `lock_keep Callback`：字段被置 1 后，阻止 mirrored 被清零的 hook

---

**读完本文，你将理解**：

- 为什么 Lock bit 测试会产生 scoreboard 误报（而硬件其实没有 bug）
- auto-predict 在哪个步骤产生了错误的 mirrored
- 为什么 `set()` 和 `write()` 都不能解决这个问题
- `predict(UVM_PREDICT_DIRECT)` 的精确语义和正确用法

---

**摘要**：在验证 Lock bit 保护机制时，测试代码需要主动向已上锁的寄存器执行写入，再读回确认硬件是否拒绝了修改。然而，UVM reg model 的 auto-predict 机制在完成 frontdoor write 后会无条件更新镜像值，完全不感知硬件是否因 Lock 而拒绝了写入。这导致寄存器模型镜像与硬件实际值永久失步，使后续读操作触发 scoreboard 误报。本文分析该现象的形成机制，并给出 `predict(UVM_PREDICT_DIRECT)` 修复方案。

---

## 一、Lock Bit 的保护逻辑

在芯片设计中，某些寄存器配置需要一次性写入、不可在运行时修改。典型做法是设置一个 **Lock bit**：

- 初始状态：`LOCK = 0`，寄存器可正常读写
- 配置完成后：软件将 `LOCK` 置 1
- LOCK=1 之后：硬件对该 entry 的所有写操作静默拒绝，寄存器值保持不变
- 唯一清零方式：硬件复位（register write 无法清除 LOCK）

验证这个机制的标准测试模式是：

```
// CHK_LOCK 测试流程
① read  orig_val          // 读取锁定后的当前值
② write ~orig_val         // 尝试写入反值（期望被硬件拒绝）
③ read  readback          // 读回确认
④ assert readback == orig_val  // 期望：值未变，保护生效
```

逻辑完全正确——但在 UVM 环境中，Step ② 和 Step ③ 之间藏着一个陷阱。

---

## 二、UVM Reg Model 的 auto-predict

理解问题之前，需要先澄清 UVM reg model 中两个容易混淆的概念：

| 字段 | 含义 | 更新时机 |
|---|---|---|
| `desired` | 软件期望写入的值 | `set()` 调用后 |
| `mirrored` | 模型认为硬件当前持有的值 | `write()` / `read()` 完成后 |

**auto-predict** 是 frontdoor write 完成后 UVM 自动执行的逻辑：

```
// write(UVM_FRONTDOOR, value) 完成后，UVM 自动执行：
mirrored = desired = value
```

关键问题：**auto-predict 假设所有 frontdoor write 都被硬件接受**。它不检查、也无从感知硬件是否因 Lock 而拒绝了写入。

这里需要特别区分：`access = "RO"` 的静态只读字段不会有这个问题——UVM 在定义阶段就知道该字段不可写，auto-predict 会正确跳过 mirrored 更新。Lock bit 保护是**运行时动态条件**，UVM reg model 在定义阶段无从得知，因此 auto-predict 无法正确处理。

---

## 三、失步的形成过程

以下是 CHK_LOCK 执行时，mirrored 与硬件实际值之间的状态演变：

```
Step ①：read(reg, orig_val)
   硬件持有值：A
   auto-predict：mirrored = A          ← 同步 ✓

Step ②：write(reg, ~A)                // 写入反值，测试 Lock 保护
   硬件：LOCK=1，拒绝写入，值仍 = A
   auto-predict：mirrored = ~A         ← 失步！
   （auto-predict 不知道硬件拒绝了写入）

Step ③：read(reg, readback)
   硬件返回：A（Lock 保护有效，值未变）
   Scoreboard 监控到此次读操作：
     MONITOR  （来自硬件）  = A
     PREDICTOR（来自 mirrored）= ~A    ← 不一致！
     → UVM_ERROR: RD_DATA Mismatched  ← 误报！
        （仿真日志中会出现类似：
         UVM_ERROR scoreboard.svh: RD_DATA Mismatched!
         MONITOR_TRANS 'hA  Mismatched with PREDICTOR_TRANS 'h5A）
   read 完成后 auto-predict：mirrored = A（恢复）
   但 error 已经报出，无法撤回
```

> **Step ③ 的 scoreboard 误报是一个"虚假错误"——硬件行为完全正确，Lock 保护正常工作。是 reg model 镜像与硬件现实的短暂失步，导致 scoreboard 误判为 bug。**

---

## 四、跨循环的扩散：stale mirror

在带复位的多轮测试中，mirror 失步问题还会跨循环扩散，形成更难排查的误报。

假设测试结构如下：

```
第 1 轮：编程寄存器 = A → LOCK=1 → CHK_LOCK → 复位
第 2 轮：重新编程 → LOCK=1 → CHK_LOCK → 复位
...
```

关键在于：**硬件复位将所有寄存器清零，但 UVM reg model 的 mirrored 不会随复位自动归零**。

如果第 2 轮省略了某个寄存器的重新编程（例如因条件跳过了 BASE 写入），则：

- 硬件：复位后该寄存器 = 0
- mirrored：仍残留第 1 轮编程的值 A（stale mirror）

此时 CHK_LOCK 的 Step ① 读取原值：

```
MONITOR  （硬件）= 0
PREDICTOR（mirrored）= A（残留自第 1 轮）
→ 误报！（甚至还没执行破坏性写入就已经报错）
```

这是两个相互关联但独立的问题：

- **根因 A**：复位后寄存器归零，但某些代码路径跳过了重新编程，导致 mirrored 与硬件长期不同步
- **根因 B**：CHK_LOCK 的破坏性写入触发 auto-predict，使 mirrored 短暂更新为错误值

根因 A 是根因 B 在多轮测试中的放大器，需要分别修复。

---

## 五、为什么 set() 不够用

直觉上，Step ② 写入反值后再调用 `set(orig_val)` 把 desired 恢复，似乎可以解决问题。但这是错误的。

| 方法 | 修改 desired | 修改 mirrored | 产生总线事务 | 触发 Scoreboard |
|---|---|---|---|---|
| `set(A)` | ✓ | ✗ | ✗ | ✗ |
| `write(A)` | ✓ | ✓（auto）| ✓ | ✓ |
| `predict(DIRECT, A)` | ✗ | **✓（强制）** | ✗ | ✗ |

Scoreboard 的 predictor 读取的是 `mirrored`，而 `set()` 只改 `desired`，不影响 `mirrored`，所以无法解决问题。

此处我们需要的操作语义是：**只更新 mirrored，不产生总线事务，不触发 scoreboard，且不受任何 callback 约束**。`predict(UVM_PREDICT_DIRECT)` 正是为此设计。

---

## 六、修复：predict(UVM_PREDICT_DIRECT)

`UVM_PREDICT_DIRECT` 无条件强制设置 mirrored，完全绕过 access 约束、callback 链和总线层。修复方法是在破坏性写入之后、读回验证之前立即调用它：

```systemverilog
// Step ①：读取锁定后的原值
reg_handle.read(status, orig_val, UVM_FRONTDOOR);
//   → mirrored 被 auto-predict 更新为 orig_val

// Step ②：写入破坏值（硬件因 Lock 拒绝，auto-predict 失步）
reg_handle.write(status, ~orig_val, UVM_FRONTDOOR);
//   → HW：Lock=1，拒绝写入，值仍 = orig_val
//   → auto-predict：mirrored = ~orig_val  ← 错误！

// Step ②.5：立即恢复 mirrored ← 关键修复
// Lock 已拒绝写入，硬件实际持有的仍是 orig_val
// void'(...) 表示丢弃 predict() 的返回值（bit：1=成功，0=失败）
void'(reg_handle.predict(orig_val, .kind(UVM_PREDICT_DIRECT)));
//   → mirrored = orig_val  ← 恢复正确 ✓

// Step ③：读回验证（此时 mirrored 已恢复，scoreboard 不误报）
reg_handle.read(status, readback, UVM_FRONTDOOR);
//   → MONITOR = HW = orig_val
//   → PREDICTOR = mirrored = orig_val  → MATCH ✓

// Step ④：断言 Lock 保护生效
assert(readback == orig_val);
```

修复后的状态演变：

```
Step ①: read  → mirrored = A，MONITOR=A，PREDICTOR=A    MATCH ✓
Step ②: write ~A → HW 拒绝，auto-predict: mirrored=~A   临时失步
Step ②.5: predict(DIRECT, A) → mirrored = A              立即恢复 ✓
Step ③: read  → HW返回A，MONITOR=A，PREDICTOR=A          MATCH ✓ 不误报
Step ④: assert readback==orig_val                         PASS ✓ Lock 验证通过
```

---

## 七、关于 void'() 的语义

`predict()` 返回 `bit`（1=成功，0=失败）。`void'(...)` 是 SystemVerilog 中显式丢弃返回值的写法，用于告知编译器"我知道有返回值，但不使用"，避免 warning：

```systemverilog
// 标准写法：丢弃返回值
void'(reg_handle.predict(orig_val, .kind(UVM_PREDICT_DIRECT)));

// 如需 debug 阶段检查是否成功：
if (!reg_handle.predict(orig_val, .kind(UVM_PREDICT_DIRECT)))
   `uvm_error("REG_CHK", "predict(DIRECT) failed")
```

---

## 八、结语

auto-predict 是 UVM reg model 在"写入一定成功"假设下的便捷机制。Lock bit 测试刻意制造了一个"写入被拒绝"的场景，突破了这个假设，auto-predict 的盲目更新就变成了错误的来源。

这个问题的本质不是硬件 bug，也不是 scoreboard 逻辑错误，而是**验证基础设施的使用场景超出了 auto-predict 的设计边界**。理解这个边界，在每次"可能被 Lock 拒绝的写入"之后补充一行 `predict(DIRECT)`，就能根除这类误报。

---

> **核心记忆点**
>
> auto-predict 不感知 Lock 对写入的拒绝。
> 凡是向 Lock 保护的寄存器执行 frontdoor write，
> 必须在 write 之后立即调用 `predict(UVM_PREDICT_DIRECT)`，
> 将 mirrored 恢复为硬件实际持有的值。

---

## 思考题

1. 如果在 Step ②.5 不加 `predict(DIRECT)`，只是在 Step ③ 之后补一个 `predict(DIRECT, orig_val)`，能解决 scoreboard 误报吗？为什么？

2. 对于 `access = "RO"` 的静态只读字段，执行 `write(~orig_val)` 后，auto-predict 会更新 mirrored 吗？和 Lock bit 场景有什么本质区别？

3. 在多轮测试（带复位循环）中，第 1 轮对某字段执行了 `write(A)` 使 mirrored=A，第 2 轮复位后硬件该字段清零，但我们跳过了重新编程。此时 CHK_LOCK 的第一步 `read()` 会触发 scoreboard 误报吗？误报的 MONITOR 和 PREDICTOR 分别是什么值？

---

## 参考答案

**1.** 不能解决。Scoreboard 误报发生在 Step ③ 的 `read()` 完成时——此时 monitor 捕获到读事务，scoreboard 立即用当前 mirrored（= ~orig_val）生成预测，与 HW 返回的 orig_val 比较，已经报错。Step ③ 之后再执行 `predict(DIRECT)` 是亡羊补牢，错误已经发出无法撤回。`predict(DIRECT)` 必须在 Step ③ 的 `read()` 发起之前执行，这样 scoreboard 拿到的 mirrored 才是正确值。

**2.** 对 `RO` 字段：auto-predict **不会**更新 mirrored。因为 UVM 在定义阶段就知道该字段的 access 类型为 RO，auto-predict 内置了"RO 字段写入后 mirrored 不变"的规则。Lock bit 场景的本质区别在于：Lock 保护是运行时动态条件，UVM 在定义阶段不知道也无法表达，所以 auto-predict 无法正确处理，只能依赖 Callback 或 `predict(DIRECT)` 手动修正。

**3.** 会触发 scoreboard 误报。第 2 轮复位后，硬件该字段 = 0（复位值）。CHK_LOCK 的 Step ① `read()` 触发 auto-predict，scoreboard 监控到这次读事务：MONITOR（HW 返回）= 0，PREDICTOR（mirrored，第 1 轮残留）= A。两者不一致，scoreboard 报错。这是"stale mirror"导致的误报——问题根因不在 CHK_LOCK 本身，而在于第 2 轮未能在 CHK_LOCK 前将 mirrored 同步到复位值。修复方法：复位后用 `predict(DIRECT, 0)` 或 `peek()` 将 mirrored 与硬件重新同步。
