## 2026-05-15 / 2026-05-16 工作总结

### 工作目标

从 benchmark accumulation 转向
mechanism interpretation。

核心问题从：

"geometry detector 能检测多少 fault"

转变为：

"不同 detector 在看什么 statistical structure"

---

### 新增实验和脚本

scripts/analysis/f01_amplitude_audit.py
scripts/analysis/ruptures_baseline_benchmark.py
scripts/analysis/detector_response_matrix.py
scripts/analysis/detector_disagreement_heatmap.py
scripts/analysis/fault_archetype_profiles.py

---

### F01 Amplitude Audit 结论

F01 的 XMEAS7-XMEAS11 pair 激活频率 ≈ 0.407，
但 top1_mass 检出率只有 7%。

诊断结论：

F01 是 sub-threshold weak activation。
pair 被激活，但 top1_mass 幅度
系统性地集中在 0.60-0.80 之间，
中位数 = 0.750，低于 threshold=0.80。

F06 对照：中位数 = 0.845，集中在 threshold 右侧。

分类修正：

F01 不是 noisy switching，
而是 weak geometry activation：
信号结构与 F06 相同，但幅度不足。

---

### Ruptures Baseline 建立

新增两个 ruptures changepoint detector：

Version A：
输入 XMEAS7 + XMEAS11 原始信号
penalty = 50
actual_fp = 0.4%
mean_detection = 31.5%

Version B：
输入 XMEAS7-XMEAS11 滚动相关系数
penalty = 200
actual_fp = 1.4%
mean_detection = 4.9%

关键发现：

ruptures_B 被证伪为有效 detector。
rolling correlation changepoint
不等于 persistent geometry concentration。

---

### 五方 Detector Comparison 建立

统一 benchmark schema，五个 detector：

detector     FP       detection  delay
T2           0.09%    61.9%      3.08
SPE          32.1%    85.9%      3.32
top1_mass    4.5%     25.2%      5.37
ruptures_A   0.4%     31.5%      2.09
ruptures_B   1.4%     4.9%       2.84

输出文件：

outputs/csv/detector_comparison_summary_v2.csv
outputs/csv/fault_detector_response_matrix.csv

---

### Fault Archetype Taxonomy 建立

基于五方 detector response matrix，
识别四个 fault archetype：

Archetype A: Classical-Global
Faults: F11, F17, F19, F20
T2/SPE Strong, geometry Weak

Archetype B: Raw-Shift
Faults: F02, F07, F18
ruptures_A Strong, top1_mass Weak

Archetype C: Geometry-Only
Faults: F14
top1_mass Strong (0.974)
ruptures_A Insensitive (0.004)
当前最重要的 archetype。

Archetype D: Mixed-Coupled
Faults: F06, F08, F12, F13
多个 detector 同时响应。

---

### Detector Disagreement Structure

核心发现：

不同 detector 的分歧是系统性的，
不是随机噪声。

这说明不同 detector
并不是同一 underlying signal 的 noisy approximation，
而是在观察不同 statistical structure。

最大分歧对：
SPE vs ruptures_B = 0.810

最小分歧对：
top1_mass vs ruptures_B = 0.221
（原因：共同受限于 XMEAS7-11 子空间，
不是机制相似）

最重要的 separation points：

F14: top1_mass=0.974 vs ruptures_A=0.004
delta = 0.970
最强 geometry-specific evidence。

F02: top1_mass=0.064 vs ruptures_A=0.998
delta = -0.934
最强 raw-shift evidence。

输出文件：

outputs/taxonomy/detector_disagreement_heatmap.png
outputs/taxonomy/detector_pairwise_disagreement.png
outputs/taxonomy/per_fault_max_disagreement.png

---

### Fault Archetype Profiles（视觉验证）

对 F02 / F06 / F14 各取 p95 run，
画五个 panel 对比：

Panel A: XMEAS7 / XMEAS11 原始信号
Panel B: 滚动相关系数
Panel C: top1_mass trace
Panel D: dominant pair identity timeline
Panel E: ruptures_A changepoints

关键视觉结论：

F14（run=150）：

* top1_mass 全程 = 1.0
* dominant pair 全程 = XMEAS7-XMEAS11
* ruptures_A: No changepoint detected
* 这是 pure representation-level geometry concentration
  最干净的视觉证据

F06（run=164）：

* top1_mass 全程 = 1.0
* dominant pair 全程 = XMEAS7-XMEAS11
* ruptures_A: changepoint at window 1
* 和 F14 的关键差异：raw signal shift 同时存在

F02（run=366）：

* top1_mass 从 1.0 逐渐下降，最终跌破 threshold
* dominant pair 持续切换（多个 pair 出现）
* ruptures_A: changepoint at window 2
* pair switching 是 geometry-weak 的直接表现

重要观察：

F06 和 F14 的原始信号形态相似
（XMEAS7 都跳到 2500-3000，XMEAS11 几乎不动），
但 ruptures_A 对 F06 检出，对 F14 完全不检出。

说明 ruptures_A 检测的不是幅值跳变本身，
而是联合分布的更细微 statistical structure 变化。

输出文件：

outputs/taxonomy/archetype_profile_F02.png
outputs/taxonomy/archetype_profile_F06.png
outputs/taxonomy/archetype_profile_F14.png
outputs/taxonomy/archetype_triangle_comparison.png

---

### 新增文档

docs/detector_family_interpretation.md

内容包括：

* Current Positioning（项目边界声明）
* Representation-Level Interpretation
* Detector Family Summary
* Detector Interpretation（五个 detector 各自的解读）
* Detector Disagreement Structure
* Fault Archetype Structure
* Open Questions
* Limitations
* Next Steps

---

### 当前 Fault Taxonomy（最新版）

1. Persistent Geometry Concentration
   F06, F08, F14
   注：F06/F08 同时有 raw shift，
   F14 几乎纯 geometry

2. Geometry-Convergent
   F12
   directed convergence to XMEAS9-XMEAS11

3. Geometry-Partial / Weak
   F01
   sub-threshold weak activation
   pair 被激活但幅度不足

4. Geometry-Insensitive
   F03

---

### Open Questions（新增）

Q1: F06 和 F14 的原始信号形态相似，
但 ruptures_A 对两者检出结果截然不同。
ruptures_A 到底在检测什么微细 statistical structure 差异？

Q2: pair persistence（dominant pair 的稳定性）
是否比 top1_mass amplitude 更能描述
geometry concentration 的本质？

Q3: geometry concentration 是否与
representation space 中的
effective dimensionality reduction
相关？

Q4: Transfer Entropy 能否区分 F14 的
XMEAS7-XMEAS11 关系方向性？

---

### 项目当前定位（重申）

本项目定位为：

* detector-family analysis study
* representation-geometry study
* statistical structure comparison framework

不声称：

* physical attractors
* causal propagation mechanisms
* physical locking phenomena

所有结论为 representation-level 观察，
需要领域专家验证物理合理性。

---

### 下一步候选

高优先级：

* pair persistence 正式量化
  （连接 switching audit 数字和 archetype visual）
* F14 专项深挖
  （Transfer Entropy 方向性分析）

中优先级：

* Variable subset 扩展（超出 XMEAS7-11）
* Classical per-timestep PCA baseline

长期：

* Marine system mapping（MAN S50MC6）
* 真实数据验证


---

## 2026-05-17 / 2026-05-18 ????

### ????

?? TE ??????
?? Raw-shift family audit?
????? online trigger ????ESP line??

---

### P1 ???F13 vs NORMAL Variance-Matched Surplus

???te_variance_matched_surrogate_perrun.csv
???lag=5?n=50 per condition

???

| metric | value |
|--------|-------|
| F13 mean surplus | 0.1752 |
| NORMAL mean surplus | 0.1344 |
| mean difference | +0.0408 |
| bootstrap 95% CI | [0.0268, 0.0542] |
| Mann-Whitney p | 6.6e-08 |
| verdict | SIGNIFICANT |

???

F13 Dimension B?TE asymmetry?? variance-matched surrogate
???? NORMAL ? surplus ???????
TE ????????

?????
- open_questions.md: Q10 ?? closed
- te_fault_separation_audit.md: ?? Section 7

---

### PA-1b ???Raw-shift Family Audit?F01-F05?

???existing SCI/RFI direct computation results
???pairwise distance in [SCI_v0, RFI_v0] space

???

| fault | SCI_v0 | RFI_v0 | group |
|-------|--------|--------|-------|
| F01 | 0.5523 | 0.1738 | uncertain |
| F02 | 0.3545 | 0.2645 | candidate_raw_shift |
| F03 | 0.3580 | 0.2646 | candidate_raw_shift |
| F04 | 0.3244 | 0.2774 | candidate_raw_shift |
| F05 | 0.4647 | 0.2219 | uncertain |

F02-F03 distance: 0.0035??????
F02-F04 distance: 0.0328

???

F02/F03/F04 ?? candidate raw-shift family?EL-1??
F01?SCI??RFI????????representation?????
F05 ??? uncertain?????
PA-1b ??????? F01-F05?

???docs/exploratory/raw_shift_family_audit.md

---

### ESP Line?Online Trigger ????????

#### ESP-v0

???SCI_v0 rolling?RFI_v0 rolling
???invalidated
???SCI ceiling saturation?RFI trigger direction mismatch

#### ESP-v0a

???SCI_true rolling??????RFI_v0 rolling??????
WINDOW=100?STEP=10?N_RUNS=50?F13 vs NORMAL

???No-go

| indicator | F13_TPR | NORMAL_FPR | verdict |
|-----------|---------|------------|---------|
| SCI_true (p99.5) | 1.0 | 0.16 | No-go |
| RFI_v0 (all) | 1.0 | 1.0 | No-go |

???SCI/RFI rolling ???? online trigger?
FPR ???? Go ???<=0.05??

#### ESP-v1a

???TE_7_to_11?TE_11_to_7?TE_asymmetry?TE_abs_asymmetry?TE_total
Fixed NORMAL-derived bin edges??? per-window bin drift?
WINDOW=100?STEP=10?LAG=5?N_RUNS=50?F13 vs NORMAL

???No-go

???? TE_asymmetry?

| threshold | F13_TPR | NORMAL_FPR | median_lead |
|-----------|---------|------------|-------------|
| p95 | 0.96 | 0.82 | -70 samples |
| p99 | 0.74 | 0.32 | ~-200 samples |
| p99.5 | 0.60 | 0.22 | -240 samples |

?????

std_XMEAS7??? baseline?? TE_asymmetry??????
? 70-90 samples ???

F13 ????????????????
?? slow-drift ?????

#### ESP Line ??

```text
ESP-v0a: closed_negative
ESP-v1a: closed_negative
Online trigger line: closed
```

???
- docs/exploratory/esp_v0_negative_result.md
- docs/exploratory/esp_v1_negative_result.md

---

### ??????

#### Offline line????

```text
F13:
  SCI elevated (EL-3)
  TE surplus elevated (EL-2)
  Directional-Locked archetype candidate

F02/F03/F04:
  candidate raw-shift family (EL-1)

F01/F05:
  uncertain
```

#### Online trigger line????

```text
SCI/RFI rolling: No-go
TE rolling: No-go
Reason: high NORMAL FPR, no positive lead time
```

---

### ?????

??????????

RS-v2 candidate?
????? offline ??? online ????
???run-level accumulation?persistent state detection?
trajectory descriptor?semi-online audit?

???

```text
ESP line: frozen
TE expansion: frozen
PA-1c (raw-shift bootstrap): frozen
F08 TE audit: frozen
```

????

```text
??? ESP threshold
? lag ?? TE rolling
indicator ??
```
## 2026-05-18 补充：RS-v2a 结果

### RS-v2a-v0 Persistence Proxy Audit

输入：representation_audit_f13_normal_unified.csv
类型：per-run aggregate（非 per-window trace）
条件：F13 vs NORMAL，各 50 runs

结果：

| metric | F13 | NORMAL | verdict |
|--------|-----|--------|---------|
| mean_run_length | 6.01 | 1.14 | SIGNIFICANT |
| occupancy_ratio | 0.960 | 0.329 | SIGNIFICANT |
| transition_entropy_proxy | 0.109 | 1.523 | SIGNIFICANT |
| target_pair_match | 1.000 | 0.000 | sanity check only |

核心发现：

```text
F13 的检测信号不在单窗口幅度
而在连续窗口的状态持久性

mean_run_length 差距：5.3x
transition_entropy 差距：14x

ESP 失败的结构性解释：
单窗口阈值无法区分
NORMAL 的偶发高值
和 F13 的持续高值
```

当前状态：

```text
RS-v2a-v0:
persistence proxy: supported
EL-1 exploratory
scope: aggregate proxy only
```

下一步候选：

```text
RS-v2a+:
保存 dominant_pair_trace.csv
计算 trace-level persistence metrics

前置确认：
原始 pipeline 的 mean_run_length 定义
是否与 RS-v2a 预期一致
```

暂停项（不变）：

```text
ESP line: frozen
TE expansion: frozen
PA-1c: frozen
F08 TE audit: frozen
```

## ES-v3 Recovery Revision (2026-05-23)

Completed:

ES-v3.2c

Recovery / Relock

ES-v3.2d-lite

Recovery Boundary Scan

Current recovery consensus:

Eligible relock:

100%

Median relock time:

100 samples

Observed recovery boundary:

not found

within current trace horizon

Known artifacts:

relock_rate = 0.84

→ eligibility artifact

residual_damage ~= 0.7

→ horizon artifact

block_30 degraded status

→ not confirmed

Current interpretation:

Formation:

ROBUST

TPR floor ~=0.84

Maintenance:

fragment-sensitive

contiguous robust

Recovery:

eligible relock observed

boundary unresolved

Current limit:

trace horizon

Deferred:

ES-v3.2a

mixed disturbance

ES-v3.3

recovery quality

RS-v2b

soft lock

Restrictions remain:

EL-1 exploratory only

No taxonomy update

No industrial claim

No early-warning claim

No frozen promotion

## ES-v3 Freeze (2026-05-23)

Completed:

ES-v3.0b

synthetic disturbance

ES-v3.0b++

adaptive exhaustion

ES-v3.1a

formation boundary

ES-v3.1b

maintenance boundary

ES-v3.1c

contiguous maintenance

ES-v3.2c

recovery relock

ES-v3.2d-lite

recovery boundary

ES-v3.3a

recovery quality

ES-v3.3b

collapse cluster

ES-v3.3c

collapse profile

Current consensus:

Formation:

ROBUST

TPR floor ~=0.84

Maintenance:

fragment-sensitive

contiguous robust

Recovery:

eligible relock observed

median relock ~=100 samples

Recovery quality:

population split observed

Population A:

44 runs

high baseline lock

stable recovery

Population B:

6 runs

low baseline lock

fragile recovery

Mechanism:

weak_lock

+

recovery_fragile

Rejected:

late trigger

artifact overlap

horizon artifact

Boundary:

not observed within current trace horizon

Restrictions:

EL-1 exploratory only

No taxonomy update

No frozen promotion

No industrial claim

No early-warning claim

Deferred:

ES-v3.4

RS-v2b

soft lock

marine transfer

## ES-v3 Final Freeze (2026-05-23)

Completed:

ES-v3.0b

synthetic disturbance

ES-v3.0b++

adaptive exhaustion

ES-v3.1a

formation boundary

ES-v3.1b

maintenance boundary

ES-v3.1c

contiguous maintenance

ES-v3.2c

recovery relock

ES-v3.2d-lite

recovery boundary

ES-v3.3a

recovery quality

ES-v3.3b

collapse cluster

ES-v3.3c

collapse profile

ES-v3.4a

stress separation

ES-v3.4b

floor mechanism

ES-v3.4c

early-break precursor

Current consensus:

Formation:

ROBUST

TPR floor ~=0.84

Maintenance:

fragment-sensitive

contiguous robust

Recovery:

confirmed

median relock ~=100 samples

Population split:

Population A

44 runs

stable recovery

Population B

6 runs

weak_lock

recovery_fragile

early_break

oscillatory persistence

persistent floor

Mechanism chain:

weak_lock

↓

relock

↓

run_length decay

↓

below persistent

↓

early_break

↓

oscillation

↓

quality floor

Precursor:

weak

H=10

best rule:

below persistent

precision=1.0

recall=0.513

F1=0.678

Restrictions:

EL-1 exploratory only

No taxonomy update

No frozen promotion

No industrial claim

No early-warning claim

Deferred:

ES-v3.5

RS-v2b

soft lock

marine transfer

## ES-v3 Status (2026-05-22)

Completed:

ES-v3.0b
synthetic disturbance

ES-v3.0b++
adaptive local exhaustion

ES-v3.1a
formation boundary scan

ES-v3.1b
maintenance boundary scan

ES-v3.1c
contiguous maintenance attack

Current consensus:

Formation:
robust
TPR floor ~= 0.84

Maintenance:
sensitive to fragmentation
not uniformly fragile

Deferred:

ES-v3.2 mixed disturbance
RS-v2b
marine transfer
soft lock

Keep:

EL-1 exploratory only

Forbidden:

taxonomy update
industrial claim
early-warning claim
frozen promotion

## ES-v3 Status Revision (2026-05-23)

Completed:

ES-v3.0b
synthetic disturbance

ES-v3.0b++
adaptive local exhaustion

ES-v3.1a
formation boundary

ES-v3.1b
sparse maintenance

ES-v3.1c
contiguous maintenance

ES-v3.2c
recovery / relock

Current consensus:

Formation:

robust

TPR floor ~= 0.84

Maintenance:

fragment-sensitive

contiguous disturbance tolerant

Recovery:

eligible relock = 100%

median relock time = 100 samples

Known artifacts:

relock_rate = 0.84

→ eligibility artifact

residual_damage ~= 0.7

→ horizon artifact

Deferred:

ES-v3.2a: mixed disturbance

ES-v3.2d: failure surface

ES-v3.0a: soft lock design

RS-v2b: trajectory geometry

Keep:

EL-1 exploratory only

Forbidden:

taxonomy update

industrial claim

early-warning claim

frozen promotion

## 2026-05-20 补充：RS-v2a+ Trace Persistence

输入：

dominant_pair_trace_NORMAL.csv

dominant_pair_trace_F13.csv

STEP = 10

WINDOW = 100

SAMPLE_FILTER = 200

规模：

50 NORMAL

50 F13

75 windows per run

结果：

| metric | F13 | NORMAL |
|--------|------|--------|
| max_run_length | 59.86 | 9.58 |
| persistence_ratio_k5 | 0.522 | 0.130 |
| stay_probability | 0.949 | 0.578 |
| switch_rate | 0.051 | 0.422 |

结论：

RS-v2a+:

trace persistence:

supported

Formal verdict: RS-v2a TRACE SUPPORTED

方向：

F13:

long persistence

high stay

low switching

NORMAL:

short persistence

frequent switching

限制：

Current trace begins after SAMPLE_FILTER.

Supports:

post-filter persistence

Not:

early fault evolution

状态：

RS-v2a:

supported

RS-v2a+:

supported

ESP:

closed_negative

RS-v2b:

not started

EL-1 exploratory only.

---

## 2026-05-21 补充：ES-v2.2a Lock Formation

ES-v2.2a:

Semi-online Event Timing Audit

Median delays:

candidate:

90

persistent:

110

locked:

160

Derived:

candidate → persistent:

20

persistent → locked:

50

Theoretical minimum:

50

Observed:

50

Locked fraction:

F13:

1.00

NORMAL:

0.00

Interpretation:

F13 usually enters locked state directly
after persistence establishment.

Current state:

RS-v2:

supported

ES-v2.0:

supported

ES-v2.1:

supported

ES-v2.2a:

semi-online LOCK candidate supported

Restrictions:

No early-warning claim

No industrial claim

EL-1 exploratory only

---

## 2026-05-22 补充：ES-v3.0b 收口

ES-v3.0b:

single break:

TPR:

1.00

delay:

+40

status:

ROBUST

double break:

TPR:

1.00

delay:

+55

status:

ROBUST

ES-v3.0b++:

adaptive local exhaustion

TPR:

0.84

miss:

0.16

delay:

+55

FPR:

0

Interpretation:

Strong local robustness observed.

Boundary detected.

Local complete exhaustion:

84% survival

16% failure

Current status:

ES-v3.0b complete

ES-v3.1 pending

Scope:

local pre-trigger attack only

Restrictions:

No industrial claim

No early-warning claim

No taxonomy update

EL-1 exploratory only

---

## 2026-05-21 补充：ES-v2.3a 收口

Cross-fault conditions:

F14

F13

F01

F02

NORMAL

Current structure:

F14:

Locked-only

locked_fraction:

0.852

duration:

62.32

segments:

1.14

F13:

Directional-Locked

locked_fraction:

0.731

duration:

50.86

segments:

1.42

F01:

Weak-Locked

locked_fraction:

0.262

duration:

19.48

segments:

1.02

F02:

Non-anchor

NORMAL:

baseline

Status:

ES-v2 Stage-1

completed

ES-v2.3a

supported

Scope:

representation level only

Restrictions:

No mechanism claim

No industrial claim

No early-warning claim

EL-1 exploratory only

---

## 2026-05-21 补充：ES-v2.3a Cross-fault

Cross-fault traces:

NORMAL

F13

F14

F01

F02

Current interpretation:

F13:

Directional-Locked

F14:

Locked-only candidate

F01:

Weak-Locked candidate

F02:

Non-anchor

NORMAL:

baseline

F01 audit:

locked_run_fraction:

1.00

mean segments:

1.02

mean duration:

19.48

Conclusion:

single sustained lock exists

but weaker than F13/F14

Status:

ES-v2.3a

supported

EL-1 exploratory

Restrictions:

No industrial claim

No early-warning claim

No taxonomy update

No archetype promotion

---

## 2026-05-21 补充：ES-v2 Stage-1 完成

ES-v2 Stage-1:

SUPPORTED

Scope:

F13

XMEAS7-XMEAS11

EL-1 exploratory

Main results:

ES-v2.0:

Persistence trigger

best:

k=5

TPR:

1.00

FPR:

0.00

delay:

110

ES-v2.1:

Occupancy trigger

precision:

delay=110

FPR=0

speed:

delay=100

FPR=0.04

Pareto:

speed vs false positive

ES-v2.2a:

locked fraction

F13:

1.00

NORMAL:

0.00

Semi-online LOCK candidate supported

ES-v2.2b:

locked_fraction:

F13:

0.731

NORMAL:

0

lock_cycles:

1.42

mean_locked_duration:

46.07

Interpretation:

F13 enters locked state
and remains there
for long periods.

Current chain:

RS-v2

↓

Persistence

↓

Trigger

↓

Timing

↓

Realtime replay

Current status:

ES-v2 Stage-1:

supported

Scope:

semi-online candidate

Restrictions:

No industrial claim

No early-warning claim

EL-1 exploratory only

---

## 2026-05-20 补充：ES-v2.0 / ES-v2.0a

### ES-v2.0 Persistence Trigger Benchmark

输入：
dominant_pair_trace_NORMAL.csv
dominant_pair_trace_F13.csv

TARGET_PAIR：XMEAS7-XMEAS11
F13 frequency：0.916
NORMAL frequency：0.0104

触发规则：
TARGET_PAIR 连续出现 >= k 个窗口

结果：

| k | F13_TPR | NORMAL_FPR | verdict |
|---|---------|------------|---------|
| 3 | 1.00 | 0.08 | Weak |
| 5 | 1.00 | 0.00 | Go |
| 10 | 1.00 | 0.00 | Go |
| 20 | 1.00 | 0.00 | Go |
| 30 | 0.98 | 0.00 | Go |
| 40 | 0.90 | 0.00 | Go |
| 50 | 0.70 | 0.00 | Go |
| 60 | 0.60 | 0.00 | Weak |

Overall verdict：
ES-v2.0 CANDIDATE SUPPORTED

---

### ES-v2.0a Trigger Time Audit

固定参数：
Fault injection：sample 160
Trace start：sample 210
Minimum observable delay：50

结果：

| k | trigger_rate | median_delay | p10 | p90 | delay<=100 | delay<=200 |
|---|-------------|-------------|-----|-----|------------|------------|
| 5 | 1.00 | 110 | 90 | 180 | 0.42 | 0.96 |
| 10 | 1.00 | 160 | - | - | 0.00 | 0.72 |
| 20 | 1.00 | 265 | - | - | 0.00 | 0.00 |

分类：
fast persistence confirmation

解释：
k=5 距理论最优（delay=50）只差 60 samples。
96% 的 F13 run 在 200 samples 内触发。
无 run 延迟超过 500 samples。

---

### 当前项目状态

```text
ESP-v0a: SCI/RFI rolling: No-go
ESP-v1a: TE rolling: No-go

RS-v2: Persistence structure: SUPPORTED
RS-v2a: Aggregate persistence: SUPPORTED
RS-v2a+: Trace persistence: SUPPORTED
RS-v2a.2: Transition structure: SUPPORTED
RS-v2a.3: Weighted locking: SUPPORTED

ES-v2.0: Persistence trigger: SUPPORTED (k=5, TPR=1.0, FPR=0.0)
ES-v2.0a: Fast persistence confirmation: SUPPORTED (median delay=110)
```

---

### 下一步候选

高优先级：

```text
ES-v2.1:
Absorb trigger
目标：per-window absorbing tendency估计
看能否把median delay从110压到80-60
注意：需要新设计per-window滑动指标
不能直接复用RS-v2a.3的全局transition matrix
```

暂停项（不变）：

```text
ESP line: frozen
TE expansion: frozen
PA-1c: frozen
F08 TE audit: frozen
RS-v2b: not started
```

## 2026-05-20 补充：RS-v2a.3 Weighted Transition Audit

输入：

rs_v2a_transition_deep.csv

rs_v2a_transition_matrix_NORMAL.csv

rs_v2a_transition_matrix_F13.csv

rs_v2a_weighted_audit.csv

结果：

weighted_self_loop_prob:

F13 = 0.949

NORMAL = 0.578

locking_mass_ratio_top1:

F13 = 0.953

NORMAL = 0.218

concentration_ratio:

F13 = 46.45

NORMAL = 1.24

structure_class:

F13 = Single-core

NORMAL = Multi-core

NORMAL inflation:

pairs = 2

transition fraction = 0.142

结论：

RS-v2a.3:

weighted locking:

supported

解释：

F13:

local locking

single-core absorbing structure

NORMAL:

distributed switching

multi-core structure

状态：

RS-v2a:

supported

RS-v2a+:

supported

RS-v2a.2:

supported

RS-v2a.3:

supported

RS-v2b:

not started

EL-1 exploratory only.

## 2026-05-18 补充：RS-v2a 结果

### RS-v2a-v0 Persistence Proxy Audit

输入：representation_audit_f13_normal_unified.csv
类型：per-run aggregate（非 per-window trace）
条件：F13 vs NORMAL，各 50 runs

结果：

| metric | F13 | NORMAL | verdict |
|--------|-----|--------|---------|
| mean_run_length | 6.01 | 1.14 | SIGNIFICANT |
| occupancy_ratio | 0.960 | 0.329 | SIGNIFICANT |
| transition_entropy_proxy | 0.109 | 1.523 | SIGNIFICANT |
| target_pair_match | 1.000 | 0.000 | sanity check only |

核心观察：

```text
F13 signal may involve
multi-window persistence behavior.

Current evidence:
proxy level only.

mean_run_length gap: 5.3x
transition_entropy gap: 14x
```

ESP 关联（tentative）：

```text
RS-v2a provides a possible persistence-based interpretation
for ESP negative results.

Single-window thresholds may have difficulty separating
NORMAL transient events from F13 persistent behavior.

This interpretation requires trace-level validation.
```

当前状态：

```text
RS-v2a-v0:
Persistence proxy: supported
ESP interpretation: tentative
Archetype impact: none
EL-1 exploratory
Scope: aggregate proxy only
```

下一步候选：

```text
RS-v2a+:
保存 dominant_pair_trace.csv
计算 trace-level persistence metrics

前置确认：
原始 pipeline 的 mean_run_length 定义
是否与 RS-v2a 预期一致
```

暂停项（不变）：

```text
ESP line: frozen
TE expansion: frozen
PA-1c: frozen
F08 TE audit: frozen
```
