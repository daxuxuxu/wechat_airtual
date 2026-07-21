## [AXI] AMBA CHI：为什么一致性互连不再只是读写通道

![封面](cover_amba_chi.png)

---

### 导读

AXI 很擅长描述 master 和 slave 之间的读写 transaction。但当多个 processor cache、accelerator cache、memory controller 同时访问同一份数据时，问题不再只是“谁发 request、谁回 response”。

系统还必须回答：谁拥有最新 cache line？谁需要被 snoop？谁决定 request 的顺序？这就是 CHI 需要解决的问题。

---

### 前置概念速查

CHI 是 AMBA 5 中面向 scalable coherent interconnect 的协议。它用于让多个 coherent requester 共享 memory，并保持 cache coherence。

Request Node，RN，发起 coherent request。Home Node，HN，维护地址相关的 coherency、ordering 与 snoop 决策。Subordinate Node，SN，通常提供 memory 或 peripheral service。

![CHI node roles](chi-node-roles.png)

---

### 一、为什么 AXI 不足以单独解决 cache coherence

AXI 可以传输读写，但它不会天然知道某个 cache line 是否已经被另一个 requester 修改或持有。

如果多个 cache 都能保留同一地址的数据，仅靠普通 read/write 无法保证其中一个 requester 写完后，其他 cache 不再使用旧数据。CHI 在 interconnect 层加入 coherence transaction，让系统能主动询问、失效或获取其他 cache 的状态。

---

### 二、CHI 的四类通道

CHI 不只把流量分成 request 和 response。它使用 REQ、RSP、SNP、DAT 四类通道，把 request、completion、snoop 和 data transfer 解耦。

![CHI 四类通道](chi-four-channels.png)

REQ 负责发起 transaction。RSP 返回 completion、retry 等控制信息。SNP 用于发起 coherency snoop。DAT 用于传输 read data、write data、snoop data 与相关 data response。

这种拆分使 snoop、response 和 data 可以独立流动，适合高并发 coherent system。

---

### 三、Home Node 为什么是关键

Home Node 可以理解成某个 address range 的“协调者”。它知道 request 应该去 memory、去哪个 cache，还是先发 snoop。

当一个 RN 想读某个 cache line，HN 可能直接从 memory 返回，也可能先向另一个 cache 发 snoop，确认对方是否持有更新数据。

当一个 RN 想写某个 cache line，HN 可能需要让其他 cache invalid 或 clean，避免多个 cache 同时保留不一致的副本。

---

### 四、DV 中最重要的是 transaction lifecycle

CHI 验证不应只看单一 channel handshake。一个 coherent request 往往横跨 REQ、SNP、RSP、DAT 多个通道。

DV 需要追踪 request identity、address、snoop target、data source、response order 和最终 cache state。特别是 retry、snoop data、cache line eviction、reset 和 outstanding transaction 并发时，单通道 checker 很难发现问题。

建议把每笔 transaction 建模为 lifecycle：REQ allocate、HN decision、optional snoop、DAT/RSP completion、state retire。

---

### 五、常见验证场景

- 两个 RN 同时访问同一 cache line。
- 一个 RN read，另一个 RN write。
- dirty cache line 被另一个 RN 请求。
- snoop response 延迟或 data 延迟。
- retry 后重新发 request。
- HN mapping 或 snoop filter hit/miss。
- reset 发生在 snoop 或 DAT 返回期间。

---

### 六、总结

CHI 的核心不是增加更多 channel，而是把 cache coherence 变成 interconnect 可管理的 transaction。

> **AXI 解决读写传输，CHI 还要解决谁持有数据、谁必须被 snoop、谁拥有最新 cache line。**

---

*本文根据 Arm 公开的 AMBA CHI 概念资料与通用 coherent interconnect 验证方法整理。*
