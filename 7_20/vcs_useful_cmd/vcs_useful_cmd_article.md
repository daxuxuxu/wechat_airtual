## [日常问题] VCS 常用命令与 Option：把 compile、debug、coverage 和 runtime 分开理解

![封面](cover_vcs_useful_cmd.png)

---

### 导读

VCS command line 很容易越写越长，最后变成没人敢碰的一串 option。

真正高效的使用方式不是背所有 flag，而是先分清：哪些 option 决定 simulation image 里有什么，哪些 option 只影响本次 runtime，哪些 option 是为 debug 和 coverage 服务。

---

### 前置概念速查

`vcs` 通常负责 compile 和 build simulation image。`simv` 是 build 后运行的 simulation executable。

compile option 会影响 source file、include path、macro define、debug database 和 coverage instrumentation。runtime option 则影响 test、seed、verbosity、log 和部分 test behavior。

![VCS：compile option 与 runtime option 的分界](vcs-compile-runtime-flow.png)

---

### 一、编译与文件组织

`-sverilog` 用于启用 SystemVerilog 解析。`-f` 用于读取 filelist。`+incdir+` 用于加入 include directory。`+define+` 用于在编译前传入 macro define。

这几个 option 最容易出问题的地方是“编译 image 与 source 环境不一致”。例如 filelist 漏了 package，include directory 没有加入，或 macro define 在不同 regression build 中不一致。

建议把 source list、include path 和 compile define 放入可追踪的 filelist 或 build configuration，不要只依赖 shell history。

---

### 二、Debug 与 log

`-debug_access` 用于保留 debug 所需的访问能力。`-l` 用于把 compile 或 runtime log 写入指定文件。

runtime 中常见的 UVM option 包括 `+UVM_TESTNAME` 和 `+UVM_VERBOSITY`。前者选择 test，后者控制 UVM message 输出级别。

debug 的目标不是“开越多越好”。过多 debug access 会增加 compile time、image size 和 runtime overhead。应按 waveform、backtrace、signal visibility 的实际需要选择。

---

### 三、Coverage

`-cm` 用于开启指定 coverage 类型。`-cm_name` 用于标识本次 run。`-cm_dir` 用于指定 coverage database 的保存位置。

coverage option 最重要的是保证不同 seed、不同 test 和不同 regression job 的数据库不会互相覆盖。merge 前还要确认 compile-time instrumentation 一致，否则 coverage result 没有可比性。

---

### 四、Test 与随机

`+UVM_TESTNAME` 用来选择 test。`+ntb_random_seed` 用于控制随机 seed，使问题可复现。

发现随机 failure 时，第一步应该记录 test name、seed、compile define、runtime plusarg 和 simulator version。只保存一个 seed 不足以稳定复现，因为 build option 变化也可能改变 randomization path。

![VCS option 按目的分类](vcs-option-groups.png)

---

### 五、常用 option 的使用原则

第一，compile option 与 runtime option 分开维护。

第二，debug、coverage、performance build 分开定义，避免所有 regression 默认开启最大 debug。

第三，所有可影响行为的 macro define、plusarg、seed 都写入 log 或 run metadata。

第四，出现 failure 时，优先重现同一 image、同一 test、同一 seed、同一 plusarg，再开始改代码。

---

### 六、总结

VCS option 可以按四类记忆：编译组织、debug/log、coverage、test/random。

> **compile option 决定 image 有什么，runtime option 决定这次 run 怎么跑。**

---

*本文以通用 VCS／UVM 使用习惯整理。不同版本和团队封装脚本可能对具体 option 组合有额外要求。*
