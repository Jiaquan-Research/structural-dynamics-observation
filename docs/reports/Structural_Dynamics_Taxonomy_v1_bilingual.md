# Structural Dynamics Taxonomy v1
# 结构动力学分类体系 v1

## Pair-Space Structural Dynamics on the Tennessee Eastman Process
## Tennessee Eastman Process 上的 Pair-Space 结构动力学

---

# 1. Objective
# 1. 目标

This work explores whether industrial process faults can be characterized as distinct structural dynamics regimes in a low-dimensional pair-space representation.

本工作探索：工业过程故障是否可以在一个低维 pair-space 表征中，被刻画为不同的结构动力学状态。

The goal is not:

本研究的目标不是：

* supervised fault classification
* root-cause inference
* predictive maintenance benchmarking
* end-to-end industrial deployment
* 有监督故障分类
* 根因推断
* 预测性维护基准测试
* 端到端工业部署

Instead, the goal is:

相反，本研究的目标是：

> to observe how multivariate correlation structure evolves over time, and whether industrial faults naturally form different attractor regimes in pair-space dynamics.

> 观察多变量相关结构如何随时间演化，以及工业故障是否会在 pair-space 动力学中自然形成不同的吸引子状态。

These limitations do not diminish the framework's value; they define its current scope.

这些边界并不会削弱该框架的价值，它们只是界定了当前工作的范围。

The central hypothesis is:

核心假设是：

```text
Industrial faults are not only changes in variable magnitude,
but also changes in relational structure dynamics.
```

```text
工业故障不仅表现为变量幅值的变化，
也表现为关系结构动力学的变化。
```

---

# 2. Experimental Setup
# 2. 实验设置

## 2.1 Dataset
## 2.1 数据集

Experiments were conducted on the Tennessee Eastman Process (TEP) benchmark dataset.

实验基于 Tennessee Eastman Process（TEP）基准数据集进行。

The study used:

本研究使用了：

* fault-free testing runs
* fault runs F01–F20
* multiple simulation runs per fault
* batch-scale statistical evaluation
* 无故障测试运行
* F01–F20 的故障运行
* 每种故障的多次仿真运行
* 批量规模的统计评估

The TEP dataset is treated here as a controllable industrial dynamics sandbox rather than a deployment target.

在这里，TEP 数据集被视为一个可控的工业动力学沙盒，而不是一个直接部署目标。

---

## 2.2 Pair-Space Observation Window
## 2.2 Pair-Space 观测窗口

A deliberately small observation window was used.

本研究有意采用了一个较小的观测窗口。

Selected variables:

选取的变量为：

* XMEAS7
* XMEAS8
* XMEAS9
* XMEAS10
* XMEAS11

This produces:

由此得到：

```text
5 variables
→ 10 pair relations
→ 10-state pair-space
```

```text
5 个变量
→ 10 个 pair 关系
→ 10 状态的 pair-space
```

This low-dimensional space is intentional.

这种低维空间是刻意设计的。

The purpose is not full process reconstruction, but:

目的不是完整重建过程状态，而是：

```text
to maximize structural interpretability.
```

```text
最大化结构可解释性。
```

The pair-space should therefore be interpreted as a selective structural observation window rather than a complete system state representation.

因此，pair-space 应被理解为一个有选择性的结构观测窗口，而不是完整系统状态的表示。

The advantage of this constrained representation is that dominant structural states remain physically interpretable at the pair level.

这种受限表示的优势在于：主导结构状态在 pair 层面仍然保持物理可解释性。

---

## 2.3 Structural Features
## 2.3 结构特征

For each sliding window:

对每个滑动窗口：

* differenced correlation matrices were computed
* pair contribution vectors were extracted
* dominant pair states were identified
* 计算差分相关矩阵
* 提取 pair contribution 向量
* 识别主导 pair 状态

From these sequences, the following structural dynamics metrics were derived:

基于这些序列，进一步得到如下结构动力学指标：

| Metric | Interpretation |
| --- | --- |
| occupancy | time spent in dominant pair |
| switching | top-pair transition frequency |
| entropy | distributional spread of pair contributions |
| transition entropy | unpredictability of pair transitions |
| residence time | duration inside dominant basin |
| escape rate | probability of leaving basin |
| return probability | probability of re-entering basin |

| 指标 | 含义 |
| --- | --- |
| occupancy | 在主导 pair 中停留的时间占比 |
| switching | top-pair 转换频率 |
| entropy | pair contribution 分布的扩散程度 |
| transition entropy | pair 转移的不确定性 |
| residence time | 在主导 basin 中的停留时长 |
| escape rate | 离开 basin 的概率 |
| return probability | 离开后重新进入 basin 的概率 |

---

# 3. Structural Dynamics Hypothesis
# 3. 结构动力学假设

The core hypothesis of this work is:

本研究的核心假设是：

```text
Faults can alter the topology of relational dynamics,
not only the magnitude of process variables.
```

```text
故障能够改变关系动力学的拓扑结构，
而不仅仅是过程变量的幅值。
```

Under this view:

在这一视角下：

* normal operation corresponds to diffuse exploration of pair-space
* mild faults create metastable locking
* severe structural faults create deep attractor basins
* 正常工况对应于 pair-space 中的弥散式探索
* 轻度故障会产生亚稳态锁定
* 强结构故障会形成深吸引子 basin

This framing shifts the problem from:

这一框架将问题从：

```text
threshold detection
```

```text
阈值检测
```

toward:

转向：

```text
structural dynamics observation.
```

```text
结构动力学观测。
```

---

# 4. Structural Taxonomy
# 4. 结构分类体系

Experiments consistently revealed three major structural regimes.

实验稳定地呈现出三类主要结构状态。

---

## 4.1 Diffuse Wandering
## 4.1 弥散游走

Representative faults:

代表性故障：

* NORMAL
* F04
* F15
* F16

Characteristics:

特征：

* high transition entropy
* high edge count
* low occupancy
* short residence time
* high escape rate
* transition entropy 高
* edge 数量高
* occupancy 低
* residence time 短
* escape rate 高

Interpretation:

解释：

```text
The system continues to explore many relational configurations.
No dominant attractor forms.
```

```text
系统持续探索许多关系构型，
不会形成主导吸引子。
```

Typical values:

典型数值：

```text
occupancy ≈ 0.20–0.25
mean residence ≈ 3
escape rate ≈ 0.30
typical edge count ≈ 35–40
```

---

## 4.2 Metastable Basin
## 4.2 亚稳态 Basin

Representative faults:

代表性故障：

* F12
* F17
* F18

Characteristics:

特征：

* partial locking
* intermediate occupancy
* moderate residence time
* moderate escape rate
* nontrivial return probability
* 部分锁定
* occupancy 居中
* residence time 中等
* escape rate 中等
* return probability 非平凡

Interpretation:

解释：

```text
The system forms temporary structural basins,
but still escapes and re-enters dynamically.
```

```text
系统会形成临时性的结构 basin，
但仍会动态地逃离并重新进入。
```

Typical values:

典型数值：

```text
occupancy ≈ 0.40–0.75
mean residence ≈ 7–17
escape rate ≈ 0.04–0.13
typical edge count ≈ 2–4
```

---

## 4.3 Single-Edge Attractor
## 4.3 单边吸引子

Representative faults:

代表性故障：

* F06
* F08
* F13
* F14

Characteristics:

特征：

* near-single-edge topology
* extremely high occupancy
* long residence time
* near-zero escape rate
* high return probability
* 接近单边拓扑
* occupancy 极高
* residence time 很长
* escape rate 接近零
* return probability 高

Interpretation:

解释：

```text
The system collapses into a dominant relational mode.
Pair-space exploration effectively disappears.
```

```text
系统坍缩到一个主导关系模式中，
pair-space 探索几乎消失。
```

Typical values:

典型数值：

```text
occupancy ≈ 0.80–0.99
mean residence ≈ 40–60
escape rate ≈ 0.003–0.01
typical edge count = 1
```

This is quantitatively supported by:

这一点在定量上由下述事实支持：

```text
typical_edge_count = 1
across essentially all parameter settings
for F06/F08/F13/F14.
```

```text
对于 F06/F08/F13/F14，
在几乎所有参数设置下，
typical_edge_count 都等于 1。
```

These regimes emerged without supervised labeling.

这些状态是在没有监督标签的情况下自然出现的。

---

# 5. Attractor Subgraphs
# 5. 吸引子子图

Transition matrices were converted into attractor subgraphs using adaptive typical-edge selection.

转移矩阵通过自适应 typical-edge 选择被转换为 attractor subgraph。

Instead of using a fixed probability threshold, each fault retained only the smallest edge subset covering 80% transition mass.

我们没有使用固定概率阈值，而是为每个故障保留仅覆盖 80% transition mass 的最小边集合。

This avoided threshold arbitrariness and produced topology-adaptive graphs.

这样避免了阈值任意性，并得到对拓扑自适应的图结构。

Observed structures:

观察到的结构如下：

| Regime | Typical topology |
| --- | --- |
| diffuse wandering | dense transition graph |
| metastable basin | sparse multi-edge basin |
| single-edge attractor | near-self-loop collapse |

| 状态 | 典型拓扑 |
| --- | --- |
| diffuse wandering | 稠密转移图 |
| metastable basin | 稀疏多边 basin |
| single-edge attractor | 接近自环坍缩 |

Particularly:

特别地：

```text
F06/F08/F13/F14
collapsed into near-single-edge self-loop attractors.
```

```text
F06/F08/F13/F14
坍缩为接近单边自环的吸引子。
```

---

# 6. Robustness Validation
# 6. 稳健性验证

A robustness sweep was performed across:

我们进行了如下参数范围的稳健性扫描：

* W ∈ {80, 100, 150}
* S ∈ {5, 10, 20}
* typical_mass ∈ {0.75, 0.80, 0.90}

Total:

总计：

```text
27 parameter combinations
```

```text
27 组参数组合
```

Results:

结果如下：

| Fault Type | Consistency |
| --- | --- |
| F06/F08/F13/F14 | ≈ 1.00 |
| F18 (boundary case) | ≈ 0.74 |
| F17 | ≈ 0.78 |
| F12 | ≈ 0.52 |
| NORMAL/F04/F15/F16 | ≈ 0.89 |

Interpretation:

解释：

```text
Strong attractors were highly robust.
Diffuse wandering was also robust.
Metastable basins were partially parameter-sensitive.
F18 behaved as a boundary case between metastable and strong-locking regimes.
```

```text
强吸引子具有很高稳健性。
弥散游走同样稳健。
亚稳态 basin 对参数部分敏感。
F18 处在 metastable 与强锁定之间的边界区域。
```

This suggests the taxonomy is not purely a parameter artifact.

这说明该分类体系并不只是参数选择带来的假象。

---

# 7. Basin Escape Dynamics
# 7. Basin 逃逸动力学

The strongest evidence for genuine basin structure came from temporal escape dynamics.

关于真实 basin 结构的最强证据来自时间上的逃逸动力学。

Three quantities were especially informative:

最有信息量的三个量是：

* residence time
* escape rate
* return probability
* 停留时间
* 逃逸率
* 返回概率

Results showed:

结果表明：

```text
single-edge attractors
not only had high occupancy,
but also deep temporal persistence.
```

```text
single-edge attractor
不仅 occupancy 很高，
而且具有很深的时间持续性。
```

Representative examples:

代表性例子：

| Fault | occupancy | mean residence | escape |
| --- | --- | --- | --- |
| F14 | 0.880 | 62.6 | 0.003 |
| F13 | 0.810 | 38.7 | 0.012 |
| NORMAL | 0.238 | 3.1 | 0.316 |

This supports the interpretation that some faults generate genuine dynamic basins rather than static statistical concentration.

这支持了如下解释：某些故障产生的是真正的动态 basin，而不是静态统计浓缩。

---

# 8. Interpretation Boundary
# 8. 解释边界

Several important limitations must be stated clearly.

需要明确指出若干重要局限。

---

## 8.1 Small Pair-Space
## 8.1 小型 Pair-Space

The current system uses:

当前系统使用的是：

```text
5 variables → 10 pair states
```

```text
5 个变量 → 10 个 pair 状态
```

This low-dimensionality improves interpretability but may also produce artificially “hard” attractors.

这种低维表示提高了可解释性，但也可能产生人为“偏硬”的吸引子。

The current attractor geometry should therefore be interpreted as:

因此，当前吸引子几何应被理解为：

```text
a low-dimensional structural projection,
not a full industrial state manifold.
```

```text
一个低维结构投影，
而不是完整的工业状态流形。
```

---

## 8.2 No Causal Inference
## 8.2 不包含因果推断

The framework observes:

该框架观测的是：

```text
structural coupling dynamics
```

```text
结构耦合动力学
```

but does not establish:

但它并不能建立：

```text
causal directionality.
```

```text
因果方向性。
```

Observed pair locking should not be interpreted as physical causation without additional engineering analysis.

因此，在缺少额外工程分析的前提下，观测到的 pair locking 不应直接解释为物理因果。

---

## 8.3 TEP is a Simulator
## 8.3 TEP 是仿真器

The TEP benchmark lacks many realities of operational industrial systems:

TEP 基准缺少许多真实工业系统中的因素：

* maintenance interventions
* sensor degradation
* operating mode switching
* startup/shutdown transients
* human operator actions
* 维护干预
* 传感器退化
* 工况模式切换
* 启停瞬态
* 人类操作员行为

Real deployment validation remains future work.

真实部署验证仍然属于未来工作。

---

# 9. Future Applications
# 9. 未来应用

The long-term motivation of this work is marine engine-room structural monitoring.

本研究的长期动机是面向船舶机舱系统的结构监测。

Potential target systems include:

潜在目标系统包括：

* cooling loops
* scavenge air systems
* turbocharger dynamics
* fuel injection systems
* lube oil circulation systems
* 冷却回路
* 扫气系统
* 涡轮增压器动力学
* 燃油喷射系统
* 润滑油循环系统

The intended role is not alarm replacement.

其目标角色不是替代报警系统。

Instead:

而是：

```text
alarm-preceding structural monitoring
```

```text
报警前置的结构监测
```

The hypothesis is:

相应假设是：

```text
before conventional alarm thresholds are crossed,
pair-space structure may already enter abnormal basins.
```

```text
在常规报警阈值被触发之前，
pair-space 结构可能已经进入异常 basin。
```

This is especially relevant for:

这对于以下情形尤其相关：

* gradual cooling degradation
* air cooler fouling
* turbocharger efficiency loss
* combustion imbalance
* control-loop instability
* 渐进式冷却退化
* 空气冷却器污堵
* 涡轮增压效率下降
* 燃烧不平衡
* 控制回路不稳定

Future validation must therefore occur on real marine subsystem telemetry.

因此，未来验证必须落到真实船舶子系统遥测数据上。

---

# 10. Conclusion
# 10. 结论

This work demonstrates that industrial process faults can produce distinct pair-space structural dynamics regimes.

本工作展示了：工业过程故障可以产生不同的 pair-space 结构动力学状态。

Across TEP experiments:

在 TEP 实验中，

* diffuse wandering
* metastable basins
* single-edge attractors
* diffuse wandering
* metastable basins
* single-edge attractors

emerged naturally from unsupervised transition dynamics.

这些状态都从无监督的转移动力学中自然涌现。

The results suggest that:

结果表明：

```text
industrial faults may be interpretable
not only as variable deviations,
but also as attractor transitions
inside relational structure space.
```

```text
工业故障也许不仅可以被理解为变量偏移，
还可以被理解为关系结构空间中的吸引子转移。
```

The current work should be viewed as:

当前工作应被视为：

```text
a structural dynamics observation framework,
not yet an industrial deployment system.
```

```text
一个结构动力学观测框架，
而不是一个已经可以工业部署的系统。
```

The next major milestone is validation on real marine engineering telemetry.

下一个关键里程碑，是在真实船舶工程遥测数据上完成验证。
