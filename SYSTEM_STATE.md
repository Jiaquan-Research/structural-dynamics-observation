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
