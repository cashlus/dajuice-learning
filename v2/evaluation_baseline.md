# Liberty v2 MVP 评估基线

日期：2026-11-01

## 当前基线

- 模型：`deepseek-chat`
- `LLM_REASONING_EFFORT`：未设置
- `LLM_MAX_TOKENS`：4000
- 测试集：模板前 2 条示例 + `test_cases_gold.csv` 18 条，共 20 条
- 结果文件：`C:\Users\cashrus\AppData\Local\Temp\chat_current_prompt_20_results.json`

| 指标 | 结果 |
|---|---:|
| 归属准确率 | 17/20（85.0%） |
| A 型准确率 | 10/12（83.3%） |
| B 型准确率 | 2/3（66.7%） |
| C 型准确率 | 5/5（100.0%） |
| 混淆逐字命中率 | 1/7（14.3%） |
| 误命中数 | 2（#4、#17） |
| guard 纠正 | 0 |
| schema 重试 | 0/20（0%） |
| 重试后仍判错 | 0（本轮无重试） |
| validate 通过 | 20/20 |
| RuntimeError | 0 |

## 路径 A 对照

路径 A 配置：`deepseek-v4-pro`、`reasoning_effort=none`、`max_tokens=4000`。

- 归属准确率：14/20（70.0%）
- 重试率：1/20（5.0%，仅 #5）
- 重试后仍判错：0
- 主要问题：#4、#16、#17、#19 被过度判为消极/积极歧义并误命中 C0；#8 落入 `no_coverage`；#15 被后半句 Mill 界限吞掉。
- 结论：路径 A 未达到“归属准确率 >= 80%”门槛，`deepseek-chat` 保留为 v2 基线。路径 A 的 70% 仅作为“v4-pro 关闭思考后 C0 过度触发”的对照记录。

## C0 触发边界

C0 是“把「做自己想做的事」当成单一框架的定义（消极自由/积极自由混淆）”。

边界规则：C0 应在 claim 同时含有“外部障碍/干涉缺失”和“欲望是否真实”两种成分时触发；不能因为 claim 只出现“想做”“想干什么”等字样就触发。

- 一个成分只说明单一框架：仅有外部干涉缺失，优先消极自由；仅有真实意志/自我主宰，优先积极自由。
- 两个成分同时出现且 claim 把两者混作一个定义时，才判框架间歧义并命中 C0。
- #4、#17 是当前 C0 过触发的实例；#16 含真实欲望成分但未明确含外部障碍缺失，不应仅因“想做”触发 C0。
- #15 是复合 claim：前半句涉及自我实现，后半句涉及 Mill 式伤害界限；是否收进歧义边界案例，留待 P2 决策。

该边界只记录为下一轮知识库与判定规则的约束，本文件不修改现有 prompt、validator 或 concept JSON。

## 决策

按既定规则：新 chat 归属准确率 85.0% >= 80%，`deepseek-chat` 定稿为 v2 基线，进入 P2：

1. #08 无支配/共和主义框架是否纳入。
2. #15 复合 claim 是否作为框架间歧义边界案例纳入。


---

## 追加记录：trigger_condition 与 5 条 C0 验证（2026-11-01）

本节只记录本轮结果，不改动上面的旧基线、判定 prompt、validator、测试 CSV 或旧 40 条结果。

### 1. `liberty_v2.json` schema 增量

- `common_confusions` 仍为 3 条；每条新增 `trigger_condition`，原有 `confusion`、`user_patterns`、`what_is_confused`、`diagnosis`、`key_spans` 保留不变。
- 顶层键仍为 `concept, core_question, frameworks, disagreements, common_confusions`；frameworks 3 条、disagreements 3 条。
- C0 `trigger_condition`：仅当 claim 同时含『外部障碍/干涉缺失』与『欲望真实性追问（这个欲望是否真是你的）』两种语义成分时触发。若 claim 以『没人拦/没人干涉/没有外部阻力/别人不阻止』为唯一条件限定，且无真实意志/自我主宰成分，判 single 消极自由，不触发本混淆。
- C1 `trigger_condition`：仅当 claim 把『不损害他人/不伤害别人/尊重他人的领域』当作自由本身的定义或唯一判据时触发；若 claim 只是把伤害原则表述为自由的外部界限、正当干涉条件，或把它与另一自由判据并列作为限定，判对应单框架或框架间歧义，不触发本混淆。
- C2 `trigger_condition`：仅当 claim 直接把『没人实际干涉/没人拦』等同于自由，并据此否认无支配是独立自由判据时触发；若 claim 明确承认无支配是与无干涉不同的另一种判据，或只是描述仁慈主人下仍可能受支配，判 no_coverage 或对应单框架，不触发本混淆。
- 实现事实：当前 `judge_mvp.py` 的 `compact_concept()` 只向 prompt 序列化混淆条目的 `confusion / user_patterns / what_is_confused / diagnosis / key_spans`，**未包含 `trigger_condition`**。因此本轮 LLM 实际看不到新增字段；本轮未修改 prompt 或代码。

### 2. 5 条新 claim 验证 C0

- 全部为新增 claim，未出现在旧 40 条中。
- gold 均在调用 LLM 前独立确定：`single_framework` / `Berlin 式消极自由` / `gold_confusion` 为空。
- 配置：`deepseek-chat`，`LLM_MAX_TOKENS=4000`，未设置 `LLM_REASONING_EFFORT`，`--retries 1`。
- 结果文件：`C:\Users\cashrus\AppData\Local\Temp\chat_trigger_condition_5_results.json`。

| id | claim | gold | actual | 是否误命中 C0 | schema 重试 | validate |
|---|---|---|---|---:|---:|---|
| C0V-01 | 没人拦着我的时候，我想做什么就做什么。 | single_framework: Berlin 式消极自由 | ambiguous_between_frameworks: Berlin 式消极自由 \| Berlin 式积极自由 | 是 | 0 | 通过 |
| C0V-02 | 没人干涉我，我想干什么都可以。 | single_framework: Berlin 式消极自由 | ambiguous_between_frameworks: Berlin 式消极自由 \| Berlin 式积极自由 | 是 | 0 | 通过 |
| C0V-03 | 只要法律没有禁止，我想做什么都行。 | single_framework: Berlin 式消极自由 | ambiguous_between_frameworks: Berlin 式消极自由 \| Berlin 式积极自由 | 是 | 0 | 通过 |
| C0V-04 | 周围没人阻止我，我想干嘛就干嘛。 | single_framework: Berlin 式消极自由 | ambiguous_between_frameworks: Berlin 式消极自由 \| Berlin 式积极自由 | 是 | 0 | 通过 |
| C0V-05 | 没人管我的时候，我就是自由的。 | single_framework: Berlin 式消极自由 | ambiguous_between_frameworks: Berlin 式消极自由 \| Berlin 式积极自由 | 是 | 0 | 通过 |

- 判为 `single_framework / Berlin 式消极自由`：**0/5**。
- 判为 `ambiguous_between_frameworks`：**5/5**；5 条均命中 C0。
- 5/5 通过 `validate()`；schema 重试 0；guard 纠正 0；RuntimeError 0。
- 决策：按既定规则，5 条中仅 0 条判为单一消极自由（≤3），`trigger_condition` 不足；不继续调 JSON，回到 prompt 层讨论是否加入“B 型必须同时含两种判据语义”的通用规则。
- 直接原因记录：新增字段未进入当前 prompt 的 `compact_concept()` 序列化结果；这不是 LLM 忽略字段，而是本次运行根本没有把该字段传给 LLM。

### 3. 40 条扩展基线（记录，不重跑）

- 配置：`deepseek-chat`，`LLM_MAX_TOKENS=4000`，未设置 `LLM_REASONING_EFFORT`。
- 归属准确率：**29/40（72.5%）**；A 型 12/21，B 型 6/7，C 型 11/12。
- schema 重试 0/40；guard 纠正 0；validate 40/40；RuntimeError 0。
- C0 边界 #21–26：**0/6 判对，6 条全部误判 B 并命中 C0**。
- 复合 claim #27–30：**4/4 判 B:积极|Mill**。
- 无支配 #31–34 及 #10/#14/#20：**7/7 判 no_coverage**。
- 误命中 10 条：#4、#17、#21–26、#38、#40；混淆逐字命中 1/11。

### 4. 已知问题（记录，不修）

1. **#36 能力/资源 claim 判成 A:积极自由**：`如果一个人缺少教育或基本资源，他就无法真正自由。` 被归为 `Berlin 式积极自由`，gold 为 `no_coverage`。能力/资源维度仍缺框架，记录为未修复问题。
2. **#15 与 #27–30 的差异**：模型能识别强“积极 + Mill”并列（#27–30 全部 B:积极|Mill），但“积极 + 弱伤害限定”的 #15（`自由就是按照自己的方式追求自己的生活计划，只要不伤害别人。`）被压成单一 `A:Mill`。结论：强并列可识别，弱伤害限定会被后置界限吞掉。
3. **#40 误命中 C1**：`一个人只有在不伤害他人的范围内，才可以正当地要求行动自由。` 归属正确判为 `A:Mill`，但 `confusion_hit` 误命中 C1（`把伤害原则当成自由的定义（界限当本质）`）。C1 的 `trigger_condition` 本轮只写入、未验证，留到下一轮验证。

- 文档追加前 SHA-256：`3b5c2da8691e9ade31b0577e1c264eedf27e649d1abdbeb4b16d72b9dd3bf280`。

## 追加记录：trigger_condition 接入 prompt 后的 5 条复测（2026-11-01）

### 1. 序列化修复

- 仅修改 `judge_mvp.py` 的 `compact_concept()`：`common_confusions` 序列化增加 `"trigger_condition": confusion.get("trigger_condition", "")`。
- 其他字段的序列化、prompt 文本、validator、CSV、旧 40 条结果均未改。
- `--prompt-only` 已确认 prompt 包含 `"trigger_condition"` 及 C0/C1/C2 三条触发条件原文。
- 以 `build_prompt()` 的 Python 返回值为准，C0V-01 的 prompt 长度从修复前 **8,844** 字符增至修复后 **9,309** 字符，增加 **465** 字符。通过 `--prompt-only` 文件读回时多 1 个换行，实际 prompt 为 9,309。

### 2. 复测结果

- 配置：`deepseek-chat`、`LLM_MAX_TOKENS=4000`、未设置 `LLM_REASONING_EFFORT`、`retries=1`。
- 结果文件：`C:\Users\cashrus\AppData\Local\Temp\chat_trigger_condition_5_after_serialization_results.json`。

| id | claim | gold | actual | 误命中 C0 | 重试 | 第一次 finish_reason |
|---|---|---|---|:---:|---:|---|
| C0V-01 | 没人拦着我的时候，我想做什么就做什么。 | single: 消极自由 | B: 消极自由 \| 积极自由 | 是 | 0 | stop |
| C0V-02 | 没人干涉我，我想干什么都可以。 | single: 消极自由 | B: 消极自由 \| 积极自由 | 是 | 0 | stop |
| C0V-03 | 只要法律没有禁止，我想做什么都行。 | single: 消极自由 | single: 消极自由 | 否 | 0 | stop |
| C0V-04 | 周围没人阻止我，我想干嘛就干嘛。 | single: 消极自由 | B: 消极自由 \| 积极自由 | 是 | 0 | stop |
| C0V-05 | 没人管我的时候，我就是自由的。 | single: 消极自由 | single: 消极自由 | 否 | 0 | stop |

- 判为 `single_framework / Berlin 式消极自由`：**2/5**。
- 仍误判为 `ambiguous_between_frameworks` 并命中 C0：**C0V-01、C0V-02、C0V-04**。
- 残余模式：三条仍误判的 claim 都以“没人拦 / 没人干涉 / 周围没人阻止”加“想做 / 想干什么 / 想干嘛”组合出现；C0V-03 同样含“想做”，但“法律没有禁止”被模型按外部条件处理为单一消极自由。C0V-05 不含“想做”，稳定判 single。
- 5/5 通过 `validate()`；schema 重试 0；guard 纠正 0；RuntimeError 0。
- 5 条均 `finish_reason=stop`；prompt_tokens 为 3,461–3,463，completion_tokens 为 71–112，total_tokens 为 3,534–3,575。`max_tokens=4000` 未被耗尽，输出没有截断。

### 3. 判定

- 按既定规则，5 条中 2–3 条判为 single：**部分有效**，不进入 P2。
- 本轮不追加 prompt 改动；残余问题集中在“没人拦/干涉/阻止 + 想做”类表述，留待下一轮决定是否加入通用规则。
- C0V-05 修复后判为 `single_framework / Berlin 式消极自由`，说明 `trigger_condition` 能覆盖“没人管我”这类表述。该条不含“想做”，与修复前的 B 型结果相比已变化。

## 追加记录：B 型前置检查与 5 条新 claim 验证（2026-11-01）

### 1. C0 边界 gold 复审结论

- 复审对象：`C0V-01`、`C0V-02`、`C0V-04`，以及旧 40 条中的 `#21–26`，共 9 条。
- 复审结论：**8/9 维持 `single_framework / Berlin 式消极自由`，confusion 为空；1/9 存在争议**。
- 争议条目：`#24 没有人强迫我的时候，我想干什么都由我自己决定。`。该条除“没人强迫”外，还含独立的“由我自己决定”自我主宰成分，按当前定义可读为 B: 消极自由｜积极自由。
- 本轮处理：**不采纳 #24 的 gold 改动**，记为争议案例；CSV、旧 40 条结果、旧指标均未修改或重算。
- 关键区分：其余 8 条的“想做/想干什么/想干嘛”只是外部障碍缺失条件下的行动内容，不构成独立于消极自由的第二判据。

### 2. 本轮唯一代码改动

- 仅修改 `app/judge_mvp.py` 的 `build_prompt()`：在“判定顺序”第 1 条之前插入【B 型前置检查】。
- 插入原文：`【B 型前置检查】判 B 型前，先检查 claim 是否同时包含两个框架各自能独立回答 core_question 的规范判据成分。若第二个成分只是第一个判据下的行动内容（例如“没人拦”之下的“想做什么”），不构成第二判据，判 A 型。B 型要求两个成分都能单独作为“自由是什么”的答案。`
- 未改三型 schema、validator、判定顺序其他条目、证据契约、JSON、CSV；未跑旧 40 条。
- `--prompt-only` 已确认新规则进入 prompt。`build_prompt()` 返回值中，C0V-01 的 prompt 长度由 **9,309** 字符增至 **9,454** 字符，增加 **145** 字符。
- `python -m py_compile app/judge_mvp.py` 通过。

### 3. 5 条全新 claim 验证

- gold 在调用 LLM 前独立标注，未参考本次运行结果。
- 配置：`deepseek-chat`、`LLM_MAX_TOKENS=4000`、未设置 `LLM_REASONING_EFFORT`、`retries=1`。
- 结果文件：`C:\Users\cashrus\AppData\Local\Temp\liberty_b_rule_5_results.json`。

| id | claim | gold | actual | 一致 | schema 重试 | guard |
|---|---|---|---|---:|---:|---:|
| BPC-01 | 只要没有人挡住我，我想往哪里走就往哪里走。 | single: 消极自由 | single: 消极自由 | 是 | 0 | 无 |
| BPC-02 | 没有任何人干涉我，我愿意做什么就做什么。 | single: 消极自由 | single: 消极自由 | 是 | 0 | 无 |
| BPC-03 | 没人阻碍我，而且我能按自己真正认同的价值生活。 | B: 消极自由｜积极自由 | B: 消极自由｜积极自由 | 是 | 0 | 无 |
| BPC-04 | 自由既意味着没有外力胁迫，也意味着行动发自真实的自我。 | B: 消极自由｜积极自由 | B: 消极自由｜积极自由 | 是 | 0 | 无 |
| BPC-05 | 自由就是别人不阻止我行动。 | single: 消极自由 | single: 消极自由 | 是 | 0 | 无 |

- 归属一致：**5/5**。
- schema 重试：**0/5**；guard 纠正：**0/5**；`validate()`：**5/5 通过**；RuntimeError：**0**。
- 5 条均 `finish_reason=stop`；`prompt_tokens` 为 **3,547–3,553**，低于 4,000；`completion_tokens` 为 **75–119**。
- BPC-03/BPC-04 的 `confusion_hit` 均命中 C0 原文；BPC-01/BPC-02/BPC-05 的 `confusion_hit` 均为 `null`。

### 4. 判定

- 前 2 条均判 single，第 3/4 条均判 B，第 5 条判 single；按本轮验收规则，**【B 型前置检查】规则有效**。
- 记录结果，具备进入 P2 的条件；本轮不启动 P2，不扩概念，不重算旧基线。
- `#24` 仍作为争议案例保留，不并入本轮结论。

## 追加记录：40 条验收与 90% 基线定稿（2026-11-01）

本节追加定稿基线，不修改上方 72.5% 的旧 40 条记录。

### 1. 90% 基线

- 配置：`deepseek-chat`、`LLM_MAX_TOKENS=4000`、`temperature=0`、`retries=1`。
- 判定条件：B 型前置检查规则生效。
- 结果文件：`C:\Users\cashrus\AppData\Local\Temp\chat_40_after_b_precheck_results.json`。
- 归属准确率：**36/40（90.0%）**。
- 分型构成：A 型 **19/21**，B 型 **6/7**，C 型 **11/12**。
- 相对 72.5% 旧基线净增 **7 条**（29→36）；逐条状态翻转口径为 **8 条变对**（#4、#17、#21、#22、#23、#26、#36、#38）和 **1 条变错**（#35），净变化为 +7。
- 仍错 4 条：**#15、#24、#25、#35**。
- 结构验收：`validate()` 40/40 通过；schema 重试 0/40；guard 纠正 0；RuntimeError 0。
- 备注：`#24` 若按复审意见改 B，则为 **37/40（92.5%）**；现行 gold 下仍报 **90.0%**。

### 2. 已知边界

1. **#15**：复合 claim（积极 + 弱伤害限定）被压成单框架 `A:Mill`。三轮（chat / 路径 A / 路径 C）一致，不修。
2. **#24**：争议 gold。“由我自己决定”被模型读作独立积极自由判据；复审建议改 B，现行不改。
3. **#25**：“没有外部阻力”措辞仍触发 C0。这是 B 型前置检查规则的覆盖边界，不针对 40 条改 prompt。
4. **#35**：资源/能力类新回归，`C → A:Mill`。与 **#36**（`A:积极 → C`）一进一出，资源/能力类整体不稳定，记入待修。

## P2 收尾决策记录（2026-11-01）

本节只记录 P2 决策与混淆口径变更。未修改 `judge_mvp.py`、`liberty_v2.json`、prompt、validator；未重跑模型；未扩概念、未接 UI。

### 1. 无支配/共和主义框架：选 B

- 不加第四框架。C 类 `reason` 统一点名“缺共和主义/无支配框架”。
- 理由：当前 B 型 validator 要求 `candidates` 恰好 2 个；加入第四框架会打开“框架数量可变”的结构冲突。现有 3 框架 + C2 混淆诊断已足够覆盖。
- 口径说明：选项 A 的 `29/40` 是旧 gold 口径下的数字，不构成本轮 `90.0%` 基线的准确率对比。

### 2. #15：收入已知边界，不改 prompt

- `#15` 的复合 claim（积极 + 弱伤害限定）继续被压成单框架 `A:Mill`，保留为已知边界。
- 不针对该条改 prompt；改 prompt 会误伤 `#27–30` 的 B 型识别。

### 3. #35/#36：资源/能力类整体不稳定，记录不修

- `#35`：`C → A:Mill`；`#36`：`A:积极 → C`，一进一出。
- 资源/能力类边界不稳定，记入已知边界/待修，不在本轮改 JSON 或 prompt。

### 4. 混淆口径：自由文本改为 C0/C1/C2/空

- `test_cases_gold.csv` 的 `gold_confusion` 列只允许填 `C0`、`C1`、`C2` 或空。
- 映射规则：
  - `C0`：原文描述“做自己想做的事歧义”（含“随心所欲/单一框架定义，混淆无干涉与自我主宰”）。
  - `C1`：原文描述“伤害原则当定义”（含“自我实现与伤害原则的界限并列，混淆/未区分自由的定义与自由的界限”）。
  - `C2`：原文描述“无干涉 = 无支配”。
  - 其他：空。
- 映射后的非空 gold：`#2、#3、#8、#11、#15、#27、#28、#29、#30`，共 9 条。
- `#7、#13` 原文是“无约束/法律约束”类表述，不属于“伤害原则当定义”，按“其他→空”处理。
- `C0/C1/C2` 对应的 canonical 原文：
  - `C0`：`把「做自己想做的事」当成单一框架的定义（消极自由/积极自由混淆）`
  - `C1`：`把伤害原则当成自由的定义（界限当本质）`
  - `C2`：`无干涉 = 无支配（把消极自由当成自由的全部）`
- 命中判定：模型 `confusion_hit` 逐字等于对应 canonical 原文才算命中。

### 5. 新口径重算（使用现有结果，不重跑）

- 数据来源：`C:\Users\cashrus\AppData\Local\Temp\chat_40_after_b_precheck_results.json`。
- 非空 gold：**9 条**。
- 命中：**9/9（100.0%）**。
- 误命中：**2 条**（`#24、#25`，gold 为空但模型命中 C0）。
- 同一份 90% 结果的旧/新口径对照：

| 口径（同一份 90% 结果） | 命中/非空 gold | 误命中 |
|---|---:|---:|
| 旧自由文本逐字 | 1/11（9.1%） | 2（#24、#25） |
| 新 C0/C1/C2 canonical | 9/9（100.0%） | 2（#24、#25） |

- 旧自由文本口径：**1/11（9.1%）**，保留在上方 72.5% 轮次记录中；该口径要求模型输出与自由文本逐字一致，且分母含 `#7、#13`，不可与新口径直接比较。

## v2 Streamlit UI 接入（2026-11-01）

### 1. 入口与启动

- v1 入口：`app/app.py`，保留原 10 概念判定与反馈界面，不改动。
- v2 入口：`app/pages/2_liberty_v2.py`，仅开放 `liberty`，标注 `v2 demo`。
- 启动命令：

```powershell
cd C:\Users\cashrus\Documents\Codex\.kb
streamlit run app/app.py
```

- Streamlit 会从 `app/pages/` 自动发现 v2 页面；侧栏页面导航中可在 v1（主页面）和 v2（`2 liberty v2`）之间切换。
- 浏览器默认地址：`http://localhost:8501`。

### 2. API 配置

- v2 页面侧栏提供 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` 三个输入框，值保存在 `st.session_state`。
- 提交判定前才写入进程环境变量，代码和文档中均不写入真实 key。
- 也可以先用环境变量预填：

```powershell
$env:LLM_BASE_URL = "https://<host>/v1"
$env:LLM_API_KEY = "<your-key>"
$env:LLM_MODEL = "deepseek-chat"
streamlit run app/app.py
```

- UI 默认模型为 `deepseek-chat`，与当前 90.0% v2 基线一致。

### 3. v2 UI 输出与知识库展示

- 判定直接调用 `judge_mvp.judge(claim, concept, model, retries=1)`，只渲染三型：`single_framework`、`ambiguous_between_frameworks`、`no_coverage`。
- A/B/C 分别使用绿色、橙色、灰色徽标与图标；A/B 显示 `next_question`，B 显示两个候选框架和 `confusion_hit`，C 显示本地知识库未覆盖的 `reason`。
- 判定异常统一显示为 `判定失败：<原因>`，页面不中断。
- 折叠面板默认收起。v2 JSON 没有 `source_spans`、`literature`、`chain` 顶层字段，因此这些展示从既有 `concepts/liberty.json` 读取；未修改任一 JSON。

### 4. UI 验证记录

- 当前执行环境未设置 `LLM_API_KEY`、`LLM_BASE_URL`，因此未发起真实 LLM 调用，未使用或写入任何真实 key。
- 使用 Streamlit `AppTest` 对实际页面脚本做了三型渲染验证，并用确定性 mock judge 注入预期结果：

| claim | 期望渲染 | 实际渲染 | 页面异常 |
|---|---|---|---|
| 自由是做自己想做的事 | B：消极自由 / 积极自由 + C0 + 追问 | 通过 | 无 |
| 自由就是没有人管我 | A：Berlin 式消极自由 + 追问 | 通过 | 无 |
| 自由就是不被任何人支配 | C：本地知识库未覆盖 + reason | 通过 | 无 |

- 折叠面板验证：`expanded=False`，包含 v2 框架 key_spans 与 v1 的 3 条 `source_spans`、5 条 literature、chain、5 条 stances。
- 异常路径验证：mock judge 抛出 `RuntimeError` 时，页面无未捕获异常，显示 `判定失败：模拟判定异常`。
- 上述结果只验证 UI 分支与错误处理，不代表真实模型在三型上的判定准确率。

### 5. CSV 恢复记录

- 40 条 `app/test_cases_gold.csv` 由 `C:\Users\cashrus\AppData\Local\Temp\chat_40_after_b_precheck_results.json` 恢复生成。
- 恢复时保留原 18 条的 notes；新增的 22 条 notes 为空。该 CSV 是当前 90.0% 基线的评测集，不重算、不改 gold。

### 6. 模型路由记录

- 本轮请求 `deepseek-chat`，服务端响应 `model=deepseek-flash`，属网关路由差异，未改配置；反馈层验证时注明这是路由结果。

