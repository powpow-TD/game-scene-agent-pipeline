# 面向游戏场景工业化的状态感知 Agent 调度管线架构创新研究

**State-Aware Agent Scheduling Pipeline Architecture for Game Scene Industrialization**

---

# 摘要

**摘要：** 针对当前游戏场景 AI 生产管线碎片化、缺乏全局环境状态感知、规划调度高度依赖资深策划人工经验、场景逻辑一致性差等行业痛点，本文提出一种以状态感知智能体（Agent）为核心的场景生产调度管线架构。该架构以统一的生成式世界模型作为底层时空表征基底，在其之上构建独立的顶层规划调度层，遵循“感知—规划—调度—执行—更新”的闭环运行，并以人类保留意图供给与结果审核的人机协作（human-on-the-loop）形态落地。针对底层生成模型输出均为非结构化几何与文本、无法直接支撑智能体全局推理的问题，本文设计并实现了状态接地层，将异构导出物解析为结构化的全局状态快照，作为智能体环境状态接地感知的输入来源。本文通过在三个场景、九个冻结世界上的对照实验考察该架构增益的来源，得到两点发现：其一，状态接地层所提供的、超出任务简报的场景特有状态，明显改善了智能体的调度表现（目标物体覆盖率由 0.70 提升至 0.92，效应量 d=1.25）；其二，在信息量严格对等的前提下，将状态组织为结构化快照相对等量的自然语言描述，在全部九个世界中位置与指标逐一相同（效应量 d=0.00），即在本文条件下未产生可检测的额外增益。据此，本文将状态接地层的价值重新界定为“为智能体提供任务简报之外的场景状态”，而非“以结构化表示替代自然语言”，并据此给出架构贡献与设计建议。本文的方法将游戏场景生产中的顶层规划调度认知劳动从人工经验中析出，转化为可结构化、可自动化、可复制的智能调度流程，为生成式 AI 时代的设计工作流再造提供了新的思路。

**关键词：** 游戏场景工业化；生成式人工智能；智能体调度；状态接地；人机协作设计

---

# Abstract

**Abstract:** To address the fragmentation, lack of global environmental state awareness, heavy reliance on senior designers for planning and scheduling, and poor logical consistency in current AI-driven game scene production pipelines, this paper proposes a scene-production scheduling pipeline architecture centered on a state-aware agent. The architecture adopts a unified generative world model as the underlying spatiotemporal representation, on top of which an independent top-level planning-and-scheduling layer is constructed, operating in a “perceive-plan-schedule-execute-update” loop and realized as a human-on-the-loop collaboration in which humans retain intent provision and result review. To resolve the problem that the outputs of the underlying generative model are unstructured geometry and text that cannot directly support the agent's global reasoning, we design and implement a State Grounding Layer that parses heterogeneous exports into a structured global state snapshot, serving as the input source for the agent's grounded perception. Through a controlled experiment over three scenes and nine frozen worlds we examine the sources of the architectural gain and obtain two findings: (i) the scene-specific state supplied by the grounding layer, beyond what the task brief contains, substantially improves the agent's scheduling performance (target-object coverage rises from 0.70 to 0.92, Cohen's d = 1.25); and (ii) under strictly equal information content, organizing that state as a structured snapshot yields object positions and metrics identical to an equivalent natural-language description in all nine worlds (Cohen's d = 0.00), that is, no additional gain from the structured representation was observed under these conditions. We therefore reframe the value of the grounding layer as “supplying the agent with scene state beyond the task brief” rather than “replacing natural language with a structured representation,” and derive the architectural contribution and design implications accordingly. The method extracts the top-level planning-and-scheduling cognitive labor of game scene production from human experience and transforms it into a structured, automatable, and reproducible intelligent scheduling process, offering a new perspective for design-workflow reengineering in the era of generative AI.

**Keywords:** game scene industrialization; generative AI; agent scheduling; state grounding; human-AI collaborative design
