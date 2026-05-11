# Marine Structural Monitoring Mapping v1
# 船舶结构监测映射 v1

## Pair-Space Structural Dynamics for Marine Engine Room Systems
## 面向船舶机舱系统的 Pair-Space 结构动力学

---

# 1. Objective
# 1. 目标

This project explores whether marine engine-room systems exhibit detectable structural dynamics changes before conventional alarm thresholds are crossed.

本项目探索：在传统报警阈值被触发之前，船舶机舱系统是否已经出现可检测的结构动力学变化。

The core idea is:

核心思想是：

```text id="qk9m31"
industrial systems are not only collections of variables,
but also networks of dynamic relationships.
```

```text id="qk9m31_cn"
工业系统不仅是变量的集合，
也是动态关系的网络。
```

Traditional alarm systems mainly monitor:

传统报警系统主要监测：

* single-variable thresholds
* fixed safety limits
* direct parameter excursions
* 单变量阈值
* 固定安全限值
* 直接参数越界

This project instead studies:

而本项目研究的是：

```text id="8vr1q7"
whether the relational structure
between variables
changes earlier than alarm activation.
```

```text id="8vr1q7_cn"
变量之间的关系结构
是否会早于报警触发而发生变化。
```

The intended role is not alarm replacement.

其目标角色不是替代报警系统。

Instead:

而是：

```text id="i4q9z2"
alarm-preceding structural monitoring
```

```text id="i4q9z2_cn"
报警前置的结构监测
```

---

# 2. Motivation from Marine Engineering
# 2. 海事工程动机

In real engine-room operation, many failures develop gradually:

在真实机舱运行中，很多故障是渐进发展的：

* air cooler fouling
* turbocharger efficiency degradation
* injector imbalance
* cooling performance decline
* lubrication deterioration
* 空冷器污堵
* 涡轮增压器效率退化
* 喷油器不平衡
* 冷却性能下降
* 润滑状态恶化

In many cases:

在很多情况下：

```text id="u9m3lp"
individual parameters may remain inside nominal limits,
while the coupling structure between subsystems
has already changed.
```

```text id="u9m3lp_cn"
单个参数可能仍然处于标称范围内，
但子系统之间的耦合结构
已经发生了变化。
```

Example:

例如：

* exhaust temperature may remain below alarm level
* scavenge pressure may remain acceptable
* turbocharger rpm may still appear normal
* 排气温度可能仍低于报警值
* 扫气压力可能仍然可接受
* 涡轮增压转速看起来仍然正常

but:

但是：

```text id="1x7lrm"
the dynamic relationship
between these variables
may already become abnormal.
```

```text id="1x7lrm_cn"
这些变量之间的动态关系
可能已经变得异常。
```

This project investigates whether such structural transitions are observable.

本项目研究的是：这类结构转变是否可被观测。

---

# 3. Current Experimental Basis
# 3. 当前实验基础

Current experiments were conducted on the Tennessee Eastman Process (TEP) benchmark.

当前实验基于 Tennessee Eastman Process（TEP）基准开展。

The experiments revealed several distinct structural dynamics regimes:

实验揭示了若干不同的结构动力学状态：

| Regime | Characteristics |
| --- | --- |
| diffuse wandering | weak structural locking |
| metastable basin | partial structural concentration |
| single-edge attractor | strong structural locking |

| 状态 | 特征 |
| --- | --- |
| diffuse wandering | 弱结构锁定 |
| metastable basin | 部分结构集中 |
| single-edge attractor | 强结构锁定 |

The key observation is:

关键观察是：

```text id="x7m5dr"
faults may alter the pattern
of relationship dynamics,
not only variable magnitude.
```

```text id="x7m5dr_cn"
故障可能改变关系动力学的模式，
而不仅仅是变量幅值。
```

The current framework uses:

当前框架使用：

* pair-space occupancy
* transition entropy
* residence time
* escape rate
* attractor subgraphs
* pair-space occupancy
* transition entropy
* residence time
* escape rate
* attractor subgraph

to characterize structural behavior.

用于刻画结构行为。

The TEP results are treated as:

TEP 结果被视为：

```text id="l8q4yt"
proof-of-mechanism,
not industrial validation.
```

```text id="l8q4yt_cn"
机制验证，
而不是工业验证。
```

---

# 4. Proposed Marine Validation Target
# 4. 建议的海事验证目标

The preferred first validation target is:

首选的第一阶段验证目标是：

# Scavenge Air + Turbocharger System
# 扫气系统 + 涡轮增压系统

Reason:

原因：

* strong subsystem coupling
* rich dynamic behavior
* gradual degradation patterns
* physically interpretable variable relationships
* 子系统耦合强
* 动态行为丰富
* 存在渐进退化模式
* 变量关系具有物理可解释性

---

# 5. Candidate Variables
# 5. 候选变量

Initial variable candidates:

初始候选变量：

| Variable | Physical Meaning |
| --- | --- |
| main engine load | operating condition |
| engine rpm | propulsion state |
| scavenge air pressure | air supply condition |
| scavenge air temperature | thermal air state |
| turbocharger rpm | compressor efficiency |
| mean exhaust gas temperature | combustion output |
| cylinder exhaust temperature deviation | cylinder imbalance |
| air cooler seawater inlet/outlet temperature | cooling efficiency |
| air cooler differential pressure | fouling indicator |

| 变量 | 物理意义 |
| --- | --- |
| 主机负荷 | 工况状态 |
| 发动机转速 | 推进状态 |
| 扫气压力 | 供气状态 |
| 扫气温度 | 热空气状态 |
| 涡轮增压转速 | 压气机效率 |
| 平均排气温度 | 燃烧输出 |
| 各缸排气温差 | 气缸不平衡 |
| 空冷器海水进出口温度 | 冷却效率 |
| 空冷器压差 | 污堵指标 |

Not all variables are required initially.

初期不需要一次性使用全部变量。

A small interpretable subsystem window is preferred for early-stage experiments.

在早期实验中，更适合使用一个小而可解释的子系统窗口。

---

# 6. Pair-Space Interpretation
# 6. Pair-Space 解释

The framework does not model the entire engine-room state.

该框架并不建模整个机舱状态。

Instead:

相反：

```text id="q1k8mn"
it constructs a selective structural observation window.
```

```text id="q1k8mn_cn"
它构建的是一个有选择性的结构观测窗口。
```

Examples of interpretable pair relationships:

可解释的 pair 关系示例：

| Pair | Possible Interpretation |
| --- | --- |
| TC rpm ↔ scavenge pressure | compressor effectiveness |
| load ↔ exhaust temperature | combustion thermal response |
| scavenge temperature ↔ exhaust deviation | air-combustion coupling |
| air cooler ΔT ↔ scavenge pressure | cooling-airflow interaction |

| Pair | 可能解释 |
| --- | --- |
| TC rpm ↔ 扫气压力 | 压气机效率 |
| 负荷 ↔ 排气温度 | 燃烧热响应 |
| 扫气温度 ↔ 排气偏差 | 空气-燃烧耦合 |
| 空冷器 ΔT ↔ 扫气压力 | 冷却-气流相互作用 |

The purpose is to observe whether certain relationships become structurally dominant or dynamically trapped.

目标是观察某些关系是否会变成结构主导状态，或者被动态困在某个 basin 中。

---

# 7. Proposed Validation Questions
# 7. 建议的验证问题

The first-stage validation questions are intentionally simple.

第一阶段的验证问题刻意保持简单。

---

## Q1

Can structural indicators change before conventional alarm activation?

结构指标能否早于常规报警发生变化？

Example:

例如：

```text id="4n2wlp"
Does occupancy / escape rate shift
before high-temperature alarms appear?
```

```text id="4n2wlp_cn"
在高温报警出现之前，
occupancy / escape rate 是否已经发生变化？
```

TEP experiments suggest that:

TEP 实验暗示：

```text id="7q4mka"
strong-locking fault types
may produce detectable structural shifts
before conventional alarm thresholds.
```

```text id="7q4mka_cn"
强锁定型故障
可能会在常规报警阈值之前
产生可检测的结构变化。
```

---

## Q2

Do gradual degradations produce metastable structural basins?

渐进退化是否会产生亚稳态结构 basin？

Example:

例如：

* air cooler fouling
* turbocharger efficiency loss
* 空冷器污堵
* 涡轮增压效率损失

---

## Q3

Do severe abnormalities produce strong attractor locking?

严重异常是否会产生强吸引子锁定？

Example:

例如：

* major combustion imbalance
* severe airflow degradation
* 严重燃烧不平衡
* 严重气流退化

---

# 8. Data Requirements
# 8. 数据需求

Preferred data sources:

优先数据源：

* AMS trend export
* K-Chief trend logs
* simulator telemetry
* teaching engine-room simulator data
* AMS 趋势导出
* K-Chief 趋势日志
* 仿真器遥测
* 教学机舱仿真器数据

Desired characteristics:

期望的数据特征：

| Requirement | Importance |
| --- | --- |
| continuous time series | critical |
| multi-variable synchronization | critical |
| sampling interval consistency | important |
| known operating modes | important |
| known fault injection timing | highly valuable |
| repeated runs | highly valuable |

| 要求 | 重要性 |
| --- | --- |
| 连续时间序列 | 极其重要 |
| 多变量同步 | 极其重要 |
| 采样间隔一致 | 重要 |
| 已知工况模式 | 重要 |
| 已知故障注入时刻 | 很有价值 |
| 可重复运行 | 很有价值 |

Simulator environments are especially attractive because:

仿真环境尤其有吸引力，因为：

```text id="z2q7wm"
fault injection timing can be controlled,
and experiments can be repeated consistently.
```

```text id="z2q7wm_cn"
故障注入时刻可以被控制，
实验也可以一致地重复。
```

---

# 9. Current Scope Boundary
# 9. 当前范围边界

This framework currently does NOT provide:

该框架当前并不提供：

* fault diagnosis
* causal inference
* maintenance recommendation
* certified industrial monitoring
* 故障诊断
* 因果推断
* 维修建议
* 经过认证的工业监测

The current stage is:

当前阶段属于：

```text id="v9m1ra"
structural dynamics observation research.
```

```text id="v9m1ra_cn"
结构动力学观测研究。
```

The main objective is to determine whether marine systems exhibit observable attractor-like structural transitions.

主要目标是确定：海事系统是否会表现出可观测的、类似吸引子的结构转变。

---

# 10. Proposed Next Step
# 10. 下一步建议

A realistic first-stage validation setup could be:

一个现实的一阶段验证方案可以是：

1. Select one subsystem
2. Export synchronized trend data
3. Build pair-space trajectories
4. Compare:

   * normal operation
   * gradual degradation
   * abnormal conditions
5. Observe:

   * occupancy
   * transition entropy
   * escape dynamics
   * attractor formation

1. 选择一个子系统
2. 导出同步趋势数据
3. 构建 pair-space 轨迹
4. 对比：

   * 正常工况
   * 渐进退化
   * 异常工况
5. 观察：

   * occupancy
   * transition entropy
   * escape dynamics
   * attractor formation

The initial goal is not deployment.

初始目标不是部署系统。

The initial goal is:

初始目标是：

```text id="8w4qmk"
to determine whether marine subsystem telemetry
contains measurable structural dynamics signatures.
```

```text id="8w4qmk_cn"
判断海事子系统遥测中
是否包含可测量的结构动力学特征。
```
