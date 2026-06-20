# ⚽ Football Match Deep Analysis Skill (v3.2)

> 足球比赛赛前深度分析与盘口推演 —— 一个用于 **Claude Code** 的结构化分析技能。
> Structured pre-match football analysis & betting-market read skill for Claude Code.

先联网核实「赛事状态 + 数据时效」，再按 **球队画像 → 战术对位 → 历史心理 → 盘口推演** 四模块输出带信心标注的结构化报告；严格区分竞彩让球 / 亚盘 / 欧赔 / 大小球，内置盘口反推与风险控制。

## ✨ 核心特性
- **6 条分析护栏**：数据先于判断 · 不低估亚非韧性 · 不低估巨星破局 · 严格区分盘口类型 · 市场热度≠稳妥 · 输出必含风险。
- **4 道验证门工作流**：① 赛事状态校验（未开赛/进行中/已结束/延期）② 数据采集与三角验证 ③ 四模块分析 ④ 输出自检。
- **盘口推演引擎**：亚盘缺失时由欧赔「去抽水 → 主胜净概率」反推让球 · 竞彩↔亚盘换算 · 市场信号速查。
- **三档深度**：⚡ 快速 / 📊 标准 / 🔬 深度。
- **合规边界**：仅做分析；**不含下注金额/资金管理建议**；不面向未成年人。

## 📁 文件结构
| 文件 | 作用 |
|---|---|
| `SKILL.md` | 路由层：护栏、4 门工作流、深度档、自检 |
| `playbook.md` | 操作手册：状态校验、三角验证、盘口反推、赛后复盘 |
| `template.md` | 输出骨架：档位映射、三档章节、结论汇总表、免责声明 |
| `tools/handicap.py` | 泊松/Dixon-Coles 盘口计算器：由赔率/λ 精算公平亚盘·大小球·比分分布 |
| `LICENSE` | Apache License 2.0（沿用原项目） |
| `README.original.md` | 原作者 README 存档（署名/出处） |

## 🚀 安装
将本目录复制到 Claude Code 用户级技能目录：
- **Windows**: `C:\Users\<you>\.claude\skills\football-match-deep-analysis\`
- **macOS/Linux**: `~/.claude/skills/football-match-deep-analysis/`

重启 Claude Code 或执行 `/skills` 确认加载。

## 💬 使用
直接说明比赛即可触发，例如：
> 分析 德国 vs 科特迪瓦，2026 世界杯 E 组

触发词：`足球分析` / `赛前分析` / `盘口分析` / `比分预测` / `赛后复盘` / `football analysis` 等。
追加 `快速版` / `深度+混合方案` / `赛后复盘` 切换模式。

## 🧰 工具（tools/）
`tools/handicap.py` —— 泊松 / **Dixon-Coles** 盘口计算器：从 1X2 赔率或期望进球 λ 逐案反算**公平亚盘 / 大小球 / 比分分布**，比 `playbook.md` §4.1 速查表更精确（尤其重型/高进球热门）。默认 Dixon-Coles ρ=-0.13（修正低分平局偏差），`--poisson` 可退回独立泊松；仅依赖 Python 3 标准库。

```bash
# 美式 1X2 赔率（主 平 客），可选 --total 总进球主线（更准）
python tools/handicap.py --odds -180 365 540 --total 2.62
# 已有期望进球时最精确
python tools/handicap.py --lambdas 1.90 0.80
# 自检（对称/德国/巴西三案例）
python tools/handicap.py --selftest
```

## 📝 与原版差异（v2 → v3.2）
本项目是对 [timepatience/-Football-Match-Deep-Analysis-Skillv2](https://github.com/timepatience/-Football-Match-Deep-Analysis-Skillv2)（Apache-2.0）的**修改增强衍生版**。依 Apache 2.0 §4(b) 声明主要变更：
1. 将纯 Prompt 模板转换为合规 Claude Code Skill（补全 YAML frontmatter 与触发词）。
2. 新增「赛事状态校验门」——避免预测已结束/进行中的比赛，防止误用同名旧赛事数据。
3. 新增信心标注、多源三角验证与「来源清单」规范。
4. 新增盘口推演手册（去抽水反推、竞彩/亚盘换算、市场信号速查）。
5. 新增三档深度、输出自检门，并对模板去重精简（template 体积 -55%）。

## 📜 许可
基于 **Apache License 2.0**（沿用原项目）。原始模板版权归原作者所有，详见 `LICENSE` 与 `README.original.md`。

## ⚠️ 免责声明
本技能生成内容仅用于足球赛事研究与数据讨论，**不构成投注建议**，不含下注金额/资金管理建议，不面向未成年人，请遵守当地法律。预测含不确定性，盘口以实时为准。理性对待，量力而行。
