# 实验执行细则（Codex 版）v1.1

> 用途：交予 Codex 执行。三组（B0/B1/B2）按本细则运行，产物按第 8 节规范回传。
> 本细则是**冻结基线**：Codex 不得自行改动组定义、指标定义、阈值或场景清单。
> 遇到问题按第 9 节处理（记录并暂停，不擅自改设计）。

---

## 0. 冻结决策（不得擅改）

| 项 | 定值 |
|---|---|
| 任务场景 | 3 个：`living_room`（室内客厅）/ `basketball_court`（户外篮球场）/ `beach_sea`（沙滩与大海） |
| 参考场景来源 | **Marble**（模型 `marble-1.1`）。每场景生成 1 个参考世界并冻结，三组共用 |
| 组件来源 | **Rodin（Hyper3D）AI 预生成组件库**；实验前一次性生成并冻结，三组共用（见第 2.5 节） |
| 引擎 | **UE 5.8.2**，路径 `D:\EPIC\EpicGames\ue\UE_5.8` |
| 引擎驱动 | UE5 内置 Python（`UnrealEditor-Cmd.exe -run=pythonscript`），无界面 |
| 推理模型 | `deepseek-flash`（DeepSeek-V4.1-Flash），`temperature=0` |
| 每场景重复次数 | **3 次**（run_1 / run_2 / run_3） |
| 随机性控制 | 三组复用同一批冻结参考与素材；B2 固定模型与 prompt；B0/B1 由同一人操作 |
| **任务产出** | ① 摆放方案（物体/位置/尺寸）+ ② **交互配置**（碰撞体/材质/物理行为/运动方式） |

---

## 1. 实验目标与假设

**目标**：在"底层资产生成能力完全一致"的前提下，检验**规划调度模块**对场景组装质量与效率的贡献。

| 假设 | 对比 | 内容 |
|---|---|---|
| **H1** | B0 → B1 | 增设**人工规划调度模块**（全局状态维护 + 任务编排）可提升场景完整度、空间逻辑正确性与**交互配置质量** |
| **H2** | B1 → B2 | 以**智能体规划调度模块**替代人工规划调度，在质量上不劣于、在效率上优于人工 |
| **H3**（探索） | B2 内部 | 智能体所获状态的**表现形式**（结构化快照 vs 等量自然语言）是否带来差异 |

> H3 为探索性，若时间/成本受限可只做 1 个场景，须如实标注。

---

## 2. 共同条件（三组完全一致）

### 核心前提（本实验的设计基础）

> **Marble 输出的是高斯泼溅表示，属于视觉/几何表面表征，不具备碰撞体与物理属性，因而其生成的场景整体不可交互。**
> 因此：**场景中一切可交互的对象都无法从 Marble 直接获得，必须由实验方自建**——
> 实体道具由 Rodin 生成，环境元素（地面/天空/水面）由 UE5 内置 actor 提供。
> Marble 在本实验中的角色是**提供参考场景**（供状态接地层解析出"应有哪些物体、在何处"），
> 而非提供可交互资产。

1. **参考世界**：每场景用固定提示词调用 Marble 生成 1 个世界，冻结后**三组共用同一份**。
   提示词示例（须记录实际用词）：
   - living_room → "a modern living room with a fabric sofa, a wooden coffee table, a bookshelf, a floor lamp, a ceiling fan and a curtain"
   - basketball_court → "an outdoor basketball court with a hoop, a basketball net, a basketball, a bench and paved ground"
   - beach_sea → "a sandy beach by the sea with dunes, shells and calm water under a clear sky"

   > 提示词须包含全部实体道具（含新增的吊扇/窗帘/篮网），否则接地层无法从参考场景读出其材质与位置。

2. **任务简报（真值来源，与状态接地层解耦）**：预先定义每场景的**必需物体清单**，写入 `spec/tasks.json`，用于后续程序化测量。此清单**不得**作为输入喂给 B2 的接地层（否则指标循环）。

3. **组件库**：每场景所需的实体组件由 **Rodin AI 预生成**并冻结，三组共用同一批资产（生成与冻结流程见第 2.5 节）。环境元素（地面/天空/水面/地形）使用 UE5 内置 actor，不占用组件库。

4. **引擎执行**：所有场景操作在 UE5 中完成；UE5 工程统一使用一个空白模板工程，路径写入配置。

---

## 2.5 组件库准备（实验前一次性；冻结后不得更改）

**目的**：让"组件生成"这一环节不成为组间变量——三组必须使用**完全相同**的资产。

### 组件分类（先分类，再生成）

| 类别 | 处理方式 | 示例 |
|---|---|---|
| **实体组件** | 用 Rodin text-to-3D 生成 | 沙发、茶几、书架、落地灯、**吊扇**、**窗帘**、篮球、篮筐、长凳、**篮网**、贝壳 |
| **含运动部件的组件** | 同上，但须额外验证部件分离/可仿真性（见下） | **吊扇**（叶片需可独立旋转）、**窗帘**、**篮网**（需可布料仿真） |
| **环境元素** | 使用 UE5 内置 actor | 地面、天空、水面、沙地 |
| **建筑/薄片元素** | 视生成质量决定；不合格则用简单几何体 | 窗户、栅栏（**窗帘已归入实体组件**） |

> 分类结果须写入 `assets/classification.json` 并说明每项的判定依据。

### 生成流程

1. 对每个**实体组件**，用 Rodin text-to-3D 生成，prompt 须简洁描述物体本身
   （例：`wooden coffee table, low poly, game ready`）
2. **导出格式优先 FBX**（UE5 原生支持），同时保留原始格式
3. **质量检查**（逐件）：导入 UE5 → 检查
   - 包围盒是否规整（无明显离群面）
   - 材质是否正常显示
   - 面数是否合理（建议 ≤ 5 万面/件）
   - 是否可正常配置碰撞体
4. 不合格则**重新生成**，重试次数须记入 manifest（不得隐藏失败）
4b. **运动部件附加检查**（仅吊扇/窗帘/篮网）：
   - **吊扇**：Rodin 是否支持输出**分离部件**（Parts 功能）？若无，叶片将无法独立旋转，
     此时须**降级**为静态吊扇，并把该项运动真值改为 `static`（须在 `RUN_NOTES.md` 说明）
   - **窗帘 / 篮网**：网格是否有**足够细分**以支撑 UE5 Chaos Cloth 仿真？
     低模可能导致布料解算异常，此时须降级为静态，并同步修正真值
   - 以上降级一旦发生，**M5d 的运动真值表须相应更新**，且在论文局限性中如实说明
5. 全部通过后**冻结**：导出统一格式存入 `assets/`，写入 `assets/manifest.json`
6. **冻结后不得再生成或替换任何组件**；三组只能从库中取用

### `assets/manifest.json` 字段（登记 AI 生成组件）

```json
{
  "asset_id": "coffee_table_01",
  "scene": "living_room",
  "category": "entity",
  "file": "assets/living_room/coffee_table_01.fbx",
  "format": "fbx",
  "bbox_size": [1.2, 0.45, 0.6],
  "face_count": 8421,
  "rodin_prompt": "wooden coffee table, low poly, game ready",
  "rodin_plan": "Free / Creator（须如实记录）",
  "generated_at": "YYYY-MM-DD",
  "retry_count": 1,
  "license_note": "商用权利以所用档位条款为准，须如实记录",
  "note": ""
}
```

> **重要**：Rodin 对生成资产的商用授权**依档位而定**，须如实记录所用档位与其条款，
> 不得默认可商用。若用于公开发表的论文，建议核实条款后再定档位。

### 成本提示

- Rodin 的 **API 访问需 Business 档（官网标价 $120/月）**；免费档仅提供有限私有资产。
- 本细则**不要求** Codex 调用 Rodin API——组件库在实验前由人准备即可。
- 若组件数量超出免费额度，须先报告成本再决定，**不得自行订阅**。

---

## 3. 三组定义

### 「交互配置」在三组中的位置

场景要"能用"，仅有几何摆对还不够——每个对象还须配置**交互属性**：
碰撞体、材质、物理行为（是否刚体/弹性/质量）、以及（对可动对象）运动方式。

> **关键**：Marble 与 Rodin 输出的都是**静态资产**，交互属性无法从它们获得，
> 必须在 UE5 中由实验方配置。因此"配置可交互性"是**规划调度的实质工作内容之一**，
> 三组在此能力上形成梯度。

| 组 | 交互配置由谁完成 | 说明 |
|---|---|---|
| B0 | 人工，凭个人经验现场决定 | 不写文档 |
| B1 | 人工，**先在规划文档中写明**每个物体的交互规格，再实现 | 规划与实现分离 |
| B2 | 智能体**输出交互规格**并自动应用 | 由状态接地层提供材质/性质证据 |

### B0　无规划调度模块（工业基线）
- **操作者**：人工（用户本人）
- **可见输入**：**仅任务简报文本**（如需可看 Marble 参考世界的渲染截图，但**不得**获得任何结构化状态或物体清单的机器解析结果）
- **执行**：在 UE5 中手动挑选素材、摆放、对齐、配置碰撞与物理
- **不做**：不写规划文档、不维护状态记录
- **禁止**：Codex 不得参与规划或给出摆放建议（否则污染基线）

### B1　人工规划调度模块
- **操作者**：人工（用户本人）
- **可见输入**：与 B0 相同的任务简报
- **执行**：**先撰写规划/状态文档**（物体清单、目标位置、层级、物理配置），**再**按文档在 UE5 中摆放
- **产出**：`plan_human.md`（规划文档）+ UE5 最终场景

### B2　智能体规划调度模块（全自动）
- **操作者**：Codex（全自动）
- **可见输入**：**状态接地层产出的结构化状态快照**（由 Marble 参考世界解析而来）
- **执行**：智能体以 tool-use 循环驱动 UE5 完成排布、对齐、碰撞与物理配置；每轮可回读场景状态
- **禁止**：不得把 `spec/tasks.json`（真值清单）喂给智能体

---

## 4. B2 技术实现要求

### 4.1 状态接地层（沿用既有实现）
- 输入：Marble 参考世界的导出物（caption / GLB / 360° 全景图）
- 处理：多模态视觉识别为主 + 语义先验 + 几何占用校验
- 输出：`snapshot.json`（objects / relations / hierarchy / lighting / physics_missing），附 `provenance`
- **交互证据**：每个物体须给出材质与物理性质的**视觉判断依据**（如「表面呈织物纹理」→ material=fabric；
  「球形、橡胶反光」→ material=rubber, restitution=high），并记录置信度与证据来源
- 注意：Marble 的网格为合并几何，**不得**依赖连通域分割得到物体级包围盒

### 4.2 智能体 tool-use 循环
智能体须**多次顺序调用工具**（至少 3 次有状态影响的调用），每轮可观察执行结果后决策。工具集：

| 工具 | 作用 |
|---|---|
| `list_assets(category)` | 返回可用素材 id 与属性 |
| `spawn_asset(asset_id, position, rotation, scale)` | 在 UE5 中生成物体 |
| `set_interaction(actor_id, collision, material, simulate, restitution, mass_class, motion)` | 配置碰撞体、材质、物理行为与运动方式 |
| `get_scene_state()` | 回读当前场景物体清单与变换 |
| `finish()` | 结束并固化场景 |

**技术路线**（二选一，Codex 择优并在日志中说明）：
- (a) UE5 常驻进程 + 命令队列（Python 桥），智能体逐条下发；
- (b) 智能体每轮输出增量指令 JSON，由驱动脚本应用到 UE5 并回传状态。

若 (a) 不可行而降级为"单次规划 + 一次性应用"，**必须在日志与产物中明确标注**，不得称为 tool-use。

### 4.3 H3 的可选条件
将 B2 的输入由结构化快照替换为**等量自然语言描述**（token 差异 ≤5%），记为 `B2_text`，其余完全不变。

---

## 5. B0/B1 的记录规范（Codex 仅记录，不参与）

Codex 的职责限于：
1. 呈现任务简报（纯文本）
2. **分段计时**：B1 分"规划阶段"与"搭建阶段"两段；B0 只有"搭建阶段"
3. 截屏存档（设置完成后、每场景至少 1 张）
4. 从 UE5 导出最终场景的物体清单与变换（`scene_export.json`）
5. 记录操作过程中的**人工干预次数**（如 B2 无此概念则记 0）

**禁止**：不得提示摆放位置、不得建议使用哪个素材、不得代写规划文档。

---

## 6. 测量指标（程序化，统一脚本）

以 `spec/tasks.json` 为真值，由脚本自动计算：

| 编号 | 指标 | 定义 |
|---|---|---|
| **M1a** | **实体道具覆盖率**（核心） | 命中的实体道具数 / 实体道具总数 |
| M1b | 总体覆盖率（辅助） | 命中的必需物体总数（含环境 actor）/ 必需物体总数 |
| M2 | 目标物体精度 | 命中数 / 场景实际物体总数 |
| M3 | 物体重叠对数 | 包围盒相交的物体对数量 |
| M4 | 越界物体数 | 位置超出场景边界的物体数 |
| **M5a** | 碰撞体配置率 | 已配置碰撞体的实体道具数 / 实体道具总数 |
| **M5b** | **材质配置正确率**（核心） | 材质与真值一致的物体数 / 实体道具总数 |
| **M5c** | 物理行为正确率 | 刚体标志、弹性档、质量档与真值一致的物体数 / 实体道具总数 |
| **M5d** | 运动方式正确率 | 运动类型与真值一致的物体数 / **有运动需求的物体数** |
| M6 | 人工工时 | 秒（B0/B1 实测；B2 记 0，另记自动耗时） |
| M7 | 自动耗时 | B2 的端到端挂钟时间 |
| M8 | 工具调用次数 | B2 的 tool-use 调用总数 |

> M6/M7 单位统一为秒；所有指标须**逐次运行**记录，不得只报均值。

---

## 6.5 交互配置规格与真值

### 智能体输出（B2）／规划文档（B1）中的交互规格

```json
{
  "id": "basketball_01",
  "type": "basketball",
  "interaction": {
    "collision": "mesh|box|none",
    "material": "rubber|fabric|wood|metal|glass|leather|stone|...",
    "simulate": true,
    "restitution": "high|medium|low|none",
    "mass_class": "light|medium|heavy",
    "motion": "static|physics_driven|kinematic_rotate|cloth"
  }
}
```

### 真值来源（写入 `spec/tasks.json`，**不得喂给待测智能体**）

```json
{
  "id": "basketball",
  "expected_interaction": {
    "collision": "mesh", "material": "rubber", "simulate": true,
    "restitution": "high", "mass_class": "light", "motion": "physics_driven"
  }
}
```

### 实体道具交互真值表（冻结；`—` 表示不适用）

| 物体 | collision | material | simulate | restitution | mass_class | motion |
|---|---|---|---|---|---|---|
| fabric sofa | box | fabric | false | — | medium | static |
| wooden coffee table | box | wood | false | — | medium | static |
| bookshelf | box | wood | false | — | heavy | static |
| floor lamp | box | metal | false | — | medium | static |
| **ceiling fan** | mesh | metal | false | — | — | **kinematic_rotate** |
| **curtain** | mesh | fabric | false | — | — | **cloth** |
| basketball | mesh | rubber | true | high | light | **physics_driven** |
| hoop | mesh | metal | false | — | heavy | static |
| bench | box | wood | false | — | heavy | static |
| **basketball net** | mesh | fabric | false | — | — | **cloth** |
| shell | mesh | stone | false | — | light | static |

> 运动需求物体：**4 个**（篮球 = 刚体物理；吊扇 = 程序化旋转；窗帘、篮网 = 布料仿真），
> 覆盖**刚体 / 程序化运动 / 软体**三类，构成 M5d 的有效样本。
> 若附加检查（2.5 节 4b）导致某件降级为静态，须同步修改本表。

**真值判定原则**：
1. 材质真值以 **Marble 参考场景的视觉证据**为准（接地层应能读出）
2. 运动方式真值按物体功能定义（篮球=physics_driven，吊扇=kinematic_rotate，窗帘=cloth，其余=static）
3. 真值由作者预先定义并冻结，**不得依 B2 输出反推**

## 7. 场景与注意

| 场景 | 实体道具（Rodin 生成；计入 M1a） | 环境元素（UE 内置 actor；仅计入 M1b） |
|---|---|---|
| 室内客厅 | fabric sofa / wooden coffee table / bookshelf / floor lamp / **ceiling fan** / **curtain** | 地面 / 墙体 / 天空光 / 室内光照 |
| 户外篮球场 | basketball / hoop / bench / **basketball net** | 地面 / 天空 / 光照 |
| 沙滩与大海 | shell | 沙地 / 海面 / 天空 / 光照 |

> **说明**：实体道具需要主动判断"该有什么、放哪里、什么材质与物理"，是区分度的主要来源；
> 环境元素只需放置对应 actor，难度低，单列统计以免稀释核心指标。
> `window` / `fence` 是否纳入实体道具，由用户在组件库准备阶段依生成质量决定，一旦确定即冻结。
> **运动需求**：篮球（刚体物理）/ 吊扇（程序化旋转）/ 窗帘 / 篮网（布料仿真），共 4 件。

---

## 8. 产物命名与落盘规范

```
experiment_v2/
├── spec/tasks.json              # 必需物体清单（真值）
├── assets/manifest.json         # Rodin 组件登记（prompt/档位/许可）
├── assets/classification.json   # 组件分类与环境元素判定依据
├── reference/{scene}/           # Marble 参考世界导出物 + snapshot.json
├── runs/{B0|B1|B2}/{scene}/run_{1..3}/
│   ├── plan_*.json|md           # 规划产物（B1 人工文档、B2 智能体规划）
│   ├── scene_export.json        # UE5 最终场景物体清单与变换
│   ├── screenshot_*.png
│   ├── timing.json              # 分段计时
│   └── log.txt                  # 该次运行日志
├── results/raw.csv              # 逐次运行的指标（一行一次）
├── results/summary.csv          # 按组聚合（均值/离散度）
└── scripts/                     # 全部脚本（含 UE5 驱动、测量、接地）
```

**`results/raw.csv` 字段**（不得缺列）：
`run_id, group, scene, repeat, source(Marble|human|agent), M1..M8, status(success|fail), note`

---

## 9. 失败处理与禁止事项

**禁止**：
1. 不得修改 `spec/tasks.json`、指标定义或本细则中的任何冻结项
2. 不得伪造或补全人工数据（B0/B1 必须是真人真实操作）
3. 不得只保留成功运行；失败运行须以 `status=fail` 如实入库
4. 不得用估算值填充缺失指标；缺失记 `null` 并说明
5. 不得把真值清单喂给待测智能体

**遇到以下情况 → 暂停并报告，不自行改设计**：
- UE5 无法无界面驱动 Python
- Marble 导出物缺失关键字段（如无 pano）
- 组件库缺件（Rodin 生成失败或质量不合格）导致必需物体无法覆盖
- 智能体 tool-use 循环无法稳定收敛

---

## 10. 完成后回传清单（给论文写作方）

1. `results/raw.csv` 与 `results/summary.csv`（**原始逐次记录**）
2. 全部 `scene_export.json`
3. `logs/`（含失败运行）
4. `scripts/` 全部脚本
5. `assets/manifest.json`、`assets/classification.json` 与 `spec/tasks.json`
6. 环境记录：UE 版本、模型名与版本、运行日期、Marble 余额变化
7. 一份 `RUN_NOTES.md`：实际执行与细则的**任何偏离**及其原因

> 回传的是**原始产物**而非结论摘要——写作方将据此重新计算全部统计量并核验。
