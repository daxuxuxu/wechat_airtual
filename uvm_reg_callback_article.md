# UVM 寄存器模型 Callback 机制

## 原理、应用场景与常见陷阱

*芯片验证 · UVM · Register Model · Callback*

---

**摘要**：UVM 寄存器模型提供了一套 Callback 机制，允许验证工程师在寄存器读写操作的各个阶段插入自定义逻辑，而无需修改原始寄存器定义。这种机制广泛用于模拟硬件的写保护行为、访问约束、副作用触发等场景。本文系统介绍 Callback 的工作原理、注册方式、常见用法，并重点分析 Callback 与 auto-predict 机制交互时容易产生的陷阱。

---

## 一、为什么需要 Callback

UVM 寄存器模型（reg model）描述了寄存器的字段布局和访问属性，但无法直接描述硬件在运行时的动态行为，例如：

- **写保护**：某个字段一旦被置为特定值（如 1），后续写操作被硬件拒绝
- **副作用**：写入一个字段会联动修改另一个字段的值
- **访问约束**：在特定状态下某寄存器不允许被访问
- **镜像修正**：硬件对写入值有额外的掩码或约束，实际存储的值与写入值不同

Callback 提供了一种**非侵入式**的扩展手段——不改变寄存器类定义，通过在外部注册钩子函数来插入所需逻辑。

---

## 二、Callback 的基本结构

UVM 寄存器 Callback 继承自 `uvm_reg_cbs`，该基类提供了六个虚方法（钩子）：

| 钩子方法 | 触发时机 | 典型用途 |
|---|---|---|
| `pre_write()` | frontdoor write 发送前 | 拦截写操作、修改写入值 |
| `post_write()` | frontdoor write 完成后 | 触发副作用、记录访问日志 |
| `pre_read()` | frontdoor read 发送前 | 访问控制、状态检查 |
| `post_read()` | frontdoor read 完成后 | 修正读回值、触发副作用 |
| `post_predict()` | 任何 predict 操作完成后 | 修正 mirrored 值、约束镜像更新 |
| `encode() / decode()` | 值编解码时 | 非线性字段映射 |

字段级别（field-level）和寄存器级别（register-level）均支持 Callback。

---

## 三、Callback 的注册与生命周期

### 注册方法

```systemverilog
// 为某个字段实例注册 Callback
uvm_reg_field_cb::add(field_handle, callback_instance);

// 为某个寄存器实例注册 Callback
uvm_reg_cb::add(reg_handle, callback_instance);

// 注销
uvm_reg_field_cb::delete(field_handle, callback_instance);
uvm_reg_cb::delete(reg_handle, callback_instance);
```

Callback 实例通常在测试的 `build_phase` 或 `connect_phase` 中注册，以确保在仿真开始前就绑定完成。

### 执行顺序

同一目标可以注册多个 Callback。执行时按注册顺序依次调用，形成调用链。每个 Callback 可以通过修改参数或设置返回状态来影响后续 Callback 和最终的操作结果。

---

## 四、最常见的应用：写保护 Callback

写保护（Lock Callback）是芯片验证中最典型的 Callback 应用场景。其目的是：**模拟硬件在特定字段被置为某值后拒绝后续写入的行为**。

### 设计意图

以一个配置锁定字段为例：

- 初始状态：字段 = 0，寄存器可正常读写
- 软件将字段置 1（锁定）
- 此后：硬件拒绝所有对该寄存器的写入，包括试图将字段清回 0

### 实现方式

在 `post_predict()` 钩子中检查 mirrored 值：如果字段当前 mirrored 为 1，则阻止任何将其更新为 0 的 predict 操作。

```systemverilog
class lock_keep_callback extends uvm_reg_cbs;

  virtual function void post_predict(
    input uvm_reg_field   fld,
    input uvm_reg_data_t  previous,   // 操作前的 mirrored 值
    inout uvm_reg_data_t  value,       // 即将写入 mirrored 的新值
    input uvm_predict_e   kind,
    input uvm_path_e      path,
    input uvm_reg_map     map);

    // 如果字段已锁（mirrored=1），阻止任何将其清为 0 的预测
    if (previous == 1 && value == 0 && kind != UVM_PREDICT_DIRECT) begin
      value = 1;  // 强制保持 1，拒绝清零
    end
  endfunction

endclass
```

注册后，每次 `write()` 或普通 `predict()` 完成时，该 Callback 都会被触发，确保 mirrored 值不会因 auto-predict 而被错误清零。

### Callback 与 auto-predict 的交互

当测试代码执行 `write(field, 0)` 试图清零一个已锁定的字段时：

1. frontdoor write 发送到 HW → HW 拒绝（写保护生效）
2. auto-predict 触发，调用 `predict(UVM_PREDICT_WRITE, 0)`
3. **lock_keep Callback 的 post_predict() 被触发**
4. Callback 检测到 previous=1 && value=0 → 强制将 value 改回 1
5. 最终 mirrored 保持为 1，与 HW 实际状态一致

这是 Callback 最重要的作用之一：**修正 auto-predict 的结果，使 mirrored 值始终与 HW 的实际行为保持一致**。

---

## 五、Callback 与 predict(DIRECT) 的关系

既然 Callback 能维护 mirrored 的正确性，那么 `predict(UVM_PREDICT_DIRECT)` 扮演什么角色？

答案是：`UVM_PREDICT_DIRECT` 专门用于**绕过所有 Callback**，无条件强制设置 mirrored 值。

| predict 类型 | 触发 Callback | 典型场景 |
|---|---|---|
| `UVM_PREDICT_WRITE` | ✓ 会触发 | write() 完成后的 auto-predict |
| `UVM_PREDICT_READ` | ✓ 会触发 | read() 完成后的 auto-predict |
| `UVM_PREDICT_DIRECT` | ✗ 完全绕过 | 手动同步 mirrored 到 HW 实际状态 |

两者在作用上是互补关系：

- **Callback**：在"正常"读写流程中维护 mirrored 的正确性（拦截并修正 auto-predict）
- **predict(DIRECT)**：在"需要强制同步"场景中绕过 Callback，直接将 mirrored 设为已知的正确值

一个典型例子：硬件复位后，所有寄存器回到初始值（包括保护字段清零）。此时 mirrored 可能仍保留旧值，需要用 `predict(DIRECT)` 将 mirrored 强制同步到复位值——如果用普通 predict，lock_keep Callback 会阻止清零操作。

```systemverilog
// 复位后同步 mirrored（需要绕过 lock_keep Callback）
void'(field_handle.predict(RESET_VALUE, .kind(UVM_PREDICT_DIRECT)));

// 此后正常写操作：lock_keep Callback 重新生效
write(reg_handle, new_value, UVM_FRONTDOOR);
```

---

## 六、post_predict 的精确语义

`post_predict()` 是最常用的钩子，理解其参数至关重要：

```systemverilog
virtual function void post_predict(
  input  uvm_reg_field   fld,       // 被预测的字段
  input  uvm_reg_data_t  previous,  // predict 前的 mirrored 值
  inout  uvm_reg_data_t  value,     // predict 计算出的新 mirrored 值（可修改）
  input  uvm_predict_e   kind,      // 预测类型：WRITE / READ / DIRECT
  input  uvm_path_e      path,      // 访问路径：FRONTDOOR / BACKDOOR
  input  uvm_reg_map     map);
```

关键点：

- `value` 是 **inout**，Callback 可以修改它，最终这个值会被写入 mirrored
- `previous` 是只读的，代表操作前的 mirrored 值
- 通过检查 `kind` 可以区分是哪种 predict 触发了本次调用
- 当 `kind == UVM_PREDICT_DIRECT` 时，Callback **不会被触发**（DIRECT 完全绕过）

---

## 七、其他常见应用场景

### 7.1 副作用模拟

写某个控制字段触发另一个状态字段的自动更新，在 `post_write()` 中实现。

```systemverilog
// 写"触发"字段后，状态字段自动置位
virtual task post_write(uvm_reg_item rw);
  if (rw.value[0] == 1) begin
    // 模拟硬件自动置位状态标志
    void'(status_field.predict(1, .kind(UVM_PREDICT_DIRECT)));
  end
endtask
```

### 7.2 访问约束检查

在 `pre_write()` 中检查当前状态是否允许访问，不允许时报告错误并拦截操作。

```systemverilog
virtual task pre_write(uvm_reg_item rw);
  if (system_in_protected_state()) begin
    `uvm_error("REG_CBS", "Write to protected register rejected")
    rw.status = UVM_NOT_OK;  // 通知调用方操作被拒绝
  end
endtask
```

### 7.3 镜像值修正

硬件对写入值有额外截断或对齐处理，在 `post_predict()` 中将 mirrored 修正为硬件实际存储的值。

```systemverilog
virtual function void post_predict(...);
  // 硬件只保留 [31:2]，低两位始终为 0
  value = value & ~32'h3;
endfunction
```

---

## 八、注册 Callback 的最佳实践

1. **在 connect_phase 注册**：确保寄存器模型已完成构建，避免在 build_phase 中因顺序问题导致字段 handle 为空
2. **保持 Callback 轻量**：不在 Callback 中执行阻塞任务（不要在 function 类型的钩子里调用 task），避免影响仿真性能
3. **注意 DIRECT 的副作用**：使用 `predict(DIRECT)` 绕过 Callback 是有意为之，确保调用点确实需要强制同步，而非正常的访问流程
4. **文档化意图**：Callback 的行为不体现在寄存器定义里，建议在注册处添加注释说明为什么需要这个 Callback 及其预期效果

---

## 九、结语

UVM 寄存器 Callback 是连接"静态寄存器定义"与"动态硬件行为"的桥梁。它的核心价值在于：在不修改原始寄存器类的前提下，将硬件的运行时约束（写保护、副作用、访问控制）准确地反映到验证模型中，使 mirrored 值始终忠实于硬件的实际状态。

理解 Callback 与 auto-predict 的协作关系，以及 `predict(DIRECT)` 在"绕过 Callback 强制同步"场景中的精确作用，是掌握 UVM 寄存器验证框架的关键一步。两者不是对立关系，而是同一个正确性保障体系中的两种互补工具。

---

> **核心记忆点**
>
> Callback 在正常读写流程中修正 mirrored，使其与 HW 行为一致。
>
> predict(DIRECT) 在需要强制同步时绕过 Callback，直接设置 mirrored。
>
> 两者配合使用，共同维护 reg model 的正确性。
