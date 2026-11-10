# 议程设置 v3 逐点诊断 Schema

版本：v3.4  
适用范围：单个 `claim` 的逐点诊断；不负责知识卡生成，不负责联网，不负责判定层归属。  
知识卡：`agenda-setting` 议程设置知识卡（含 `key_elements_required` 与 `concept_development`）。

## 0. 顶层输出结构

```json
{
  "concept": "agenda-setting",
  "claim": "用户完整原文",
  "overall": "对 / 部分对 / 错 / 依据不足",
  "points": [],
  "summary": "一句话总结，说明哪部分成立、哪部分不成立"
}
```

顶层字段规则：

1. `concept` 固定为 `"agenda-setting"`；本 schema 不处理其他概念。
2. `claim` 必须逐字等于用户输入，不做标点、空格或措辞归一化。
3. `points` 为 1–5 个诊断点；每个点对应一个可定位的主张，不把同一主张拆成重复点。
4. `summary` 必须与 `points` 和 `overall` 一致，不得只写“基本正确”或“需要加强”。

## 1. 诊断点字段（10 个核心字段；ai_judged 另带四个判断字段）

| 字段 | 类型 | 必填 | 定义 |
|---|---|---|---|
| `claim_span` | string | 是 | 用户原文中的连续逐字片段。不得改写、概括、补字或调换标点。 |
| `subject` | string | 是 | 该主张的主体。按第 2 节消歧规则填写，不得凭空补主体。 |
| `card_ref` | string[] | 是 | 知识卡字段路径列表；必须包含 `checkpoints[C1]` 与 `checkpoints[C8]`；`knowledge_backed` 用直接路径；`ai_judged` 至少含一个非 checkpoint 的锚点（`adjacent_concepts[...]`、`uncovered_dimensions[...]`，或在“不在范围内”判断中用 `core_definition[...]` 说明范围）；`contradicted` 必须含至少一个直接陈述被违反命题的字段；所有路径真实存在。 |
| `coverage_level` | enum | 是 | 第 8 个核心字段：`knowledge_backed`、`ai_judged`、`contradicted`、`undetermined`。定义与联动见第 3.4 节。 |
| `verdict` | enum | 是 | `对`、`部分对`、`错`、`依据不足` 四档之一。 |
| `error_type` | object | 是 | 固定为 `{"primary": "...", "secondary": null 或 "..."}`；枚举见第 4 节。 |
| `evidence_gap` | string or null | 是 | 仅当 `coverage_level="undetermined"`（即 `verdict="依据不足"`）时必填，说明缺哪类证据、信息或哪条 C1/C8 检查失败；其他情况必须为 `null`。 |
| `correction` | string | 是 | 修正说明；必须引用 `card_ref` 中至少一个字段路径及该字段的原文要点。 |
| `covered_key_elements` | string[] | 是 | 该诊断点答到的 `key_elements_required` id 列表；没有答到任何要素时为 `[]`，不得重复。 |
| `missing_key_elements` | object[] | 是 | 漏掉的必需要素；每项固定为 `{"id": "K?", "standard_statement": "知识卡原文"}`，`standard_statement` 必须逐字取自知识卡的 `key_elements_required[].standard_statement`，不得自行改写；全部覆盖时为 `[]`。 |

`error_type` 不得增加第三个键；`secondary` 为空时必须写 JSON `null`，不能省略。

`covered_key_elements` 与 `missing_key_elements` 都必须出现，即使为空数组也不能省略。两个数组只在议程设置范围内的诊断点上参与 verdict 与 overall 判定；第 2.4 节“概念范围外但自身可判”的 `ai_judged` 点，两者都写 `[]`，不参与要素覆盖判定，该点仍按自身概念判断对/部分对/错。

`coverage_level="ai_judged"` 时，该点还必须带四个判断字段：

```json
{
  "ai_generated": true,
  "unverified": true,
  "classic_definition_comparison": "不在范围内：……",
  "deviation_note": "……"
}
```

`ai_generated` 与 `unverified` 必须为 `true`，表示该判断由 AI 生成、未收录在本地知识卡中。`classic_definition_comparison` 必须明确说明用户说法与知识卡经典定义的关系，取值为“符合 / 偏离 / 不在范围内”之一，并给出具体说明；`deviation_note` 必须写清偏差在哪里；如果 AI 认为该说法成立但知识卡没有收录，写“合理但不在经典定义范围内，建议人工复核”。这四个字段只属于 `ai_judged`，其他 `coverage_level` 不得带 `ai_generated=true`。

### 1.1 overall 聚合规则

- 所有点均为 `对`，且所有 `key_elements_required` 都已被至少一个点覆盖、所有点的 `missing_key_elements` 均为空：`overall = "对"`。
- 所有点均为 `依据不足`：`overall = "依据不足"`。
- 没有成立部分，且核心主张被知识卡反驳：`overall = "错"`。
- 其余混合情形：`overall = "部分对"`。
- `overall = "部分对"` 可以包含 `"依据不足"` 的诊断点；`部分对` 表示“有成立部分，也有不成立或无法判断的部分”。
- `overall = "对"` 不要求 `correction` 为空；`correction` 可以是“建议补充条件/测量指标”的建设性内容，只要所有 `verdict` 均为 `对`。
- 只要任一必需要素未覆盖，`overall` 不得为 `"对"`；哪怕所有点的 verdict 都是 `对`，也必须降为 `"部分对"` 或更低。

## 2. 主体消歧规则

### 2.1 能从上下文唯一确定 antecedent

当 claim 内部或紧邻上下文能唯一确定主体时，按 antecedent 消歧，并在 `subject` 中写明消歧依据。

示例：

```text
subject: "平台算法（由前句“算法推荐”限定）"
```

消歧只改变 `subject`，不得改变 `claim_span` 原文。

### 2.2 找不到唯一 antecedent 或存在多个可能主体

当“媒体”“平台”“算法”等指称无法唯一落到新闻媒体、平台算法、政府公关或其他主体时：

- `subject` 写 `"未区分的新闻媒体/平台算法"`；
- C1 失败；
- `coverage_level = "undetermined"`；
- `verdict` 只能是 `"依据不足"`；
- `error_type.primary` 必须是 `"无"`；
- `evidence_gap` 必须点名 C1，并说明缺少哪个指称的消歧依据。

不得为了填写 `subject` 而替用户选择一个未明示的主体。

### 2.3 主体明示

claim 已明示主体（如“新闻媒体”“平台算法”“政府公关”）时，直接使用原文主体；不得扩写成原文没有的主体。

### 2.4 概念范围外但自身可判

当 claim 的主体和对象在其自身概念内清楚，只是不属于议程设置时（例如讨论“自由”与“公理、私法”的关系），不按 C1 主体歧义处理，也不判 `undetermined`。此时：

- `coverage_level = "ai_judged"`；
- `verdict` 按该 claim 在其自身概念下的经典定义判断，可为 `对`、`部分对` 或 `错`；
- `classic_definition_comparison` 必须写明它与议程设置经典定义的关系是“符合 / 偏离 / 不在范围内”；
- `deviation_note` 必须写明这是“选错概念”，不是“说错了”；
- `evidence_gap = null`。

这类判断不是“知识库没有覆盖所以答不上来”，而是“知识库能判断它不属于本概念，AI 对它所属概念的合理性作出未核验判断”。必须保留 `ai_generated=true` 与 `unverified=true`。

## 3. verdict 定义、error_type 关系与总体聚合

### 3.1 verdict 四档

#### `对`

`claim_span` 本身没有错误，且 `missing_key_elements` 为空、`covered_key_elements` 覆盖所有 `key_elements_required`。`knowledge_backed` 时由知识卡直接支持；`ai_judged` 时由经典定义比较或相邻锚点支持，但该支持未收录在本地知识卡中，必须标 `ai_generated=true`、`unverified=true`。`correction` 允许且鼓励写建议性补充，例如“可补测量指标”“可补时间窗口”“可补对照组”，但不得暗示 `claim_span` 有错误。

例外：第 2.4 节的概念范围外 `ai_judged` 点不受要素覆盖约束，两个要素数组均为 `[]`。

关系约束：

- `error_type.primary = "无"`；
- `error_type.secondary = null`；
- `evidence_gap = null`。

#### `部分对`

`covered_key_elements` 非空，且 `missing_key_elements` 非空。`claim_span` 有一个实际可指、可修正的错误，例如表述过强、缺少条件、指称含混、把必要条件写成充分条件；同时该片段仍有成立部分。

关系约束：

- `error_type.primary` 必须非 `"无"`；
- `evidence_gap` 可以为 `null`；
- 必须同时有答到的要素和漏掉的要素；只漏不答或只答不漏都不算 `部分对`；
- 不得因为“可以更好”就判 `部分对`；`部分对` 要求 `claim_span` 本身有实际可指的错误。

#### `错`

`claim_span` 与知识卡相冲突，且不是只缺少一个可补条件。若知识卡中有一条字段直接陈述了被该 claim 违反的命题，优先使用 `coverage_level="contradicted"`，并在 `card_ref` 中引用该字段；若只是范围、强度或结构上的可修正缺陷，没有逐字否定，可用 `knowledge_backed` 搭配 `错`。

关系约束：

- `error_type.primary` 必须非 `"无"`；
- `evidence_gap = null`。

#### `依据不足`

`coverage_level="undetermined"` 时的唯一 verdict。表示 claim 本身模糊、自相矛盾，或 C1 主体歧义、C8 经验前提与理论推断无法区分，导致连 AI 也无法给出对/部分对/错的判断。不得因为知识卡没有直接依据就判“依据不足”；知识卡无直接依据但不矛盾时，按 `coverage_level="ai_judged"` 处理，verdict 可为对/部分对/错。

关系约束：

- `error_type.primary = "无"`；
- `error_type.secondary = null`；
- `evidence_gap` 必须非空；
- 若是 C1 或 C8 失败，`evidence_gap` 必须点名 `C1` 或 `C8`。

### 3.2 “完整性错误”与“undetermined/依据不足”不得合并

- `完整性错误`：知识卡能证明这类主张需要某个必要成分，而 `claim_span` 缺少该成分；缺的是 claim 的结构。
- `undetermined/依据不足`：claim 模糊、自相矛盾，或主体/经验前提无法区分，连 AI 也无法给出对/部分对/错的判断；缺的是可判定性。知识卡无直接依据但不矛盾时归 `coverage_level="ai_judged"`，不归“依据不足”。

两者可以同时出现在不同诊断点，但同一点不得用“依据不足”掩盖可指出的完整性错误，也不得用“完整性错误”掩盖知识卡无法判断的事实。

### 3.3 overall 聚合规则

- 所有点均为 `对`，且所有必需要素都被覆盖、所有 `missing_key_elements` 均为空：`overall = "对"`。
- 所有点均为 `依据不足`：`overall = "依据不足"`。
- 没有成立部分，且核心主张被知识卡反驳：`overall = "错"`。
- 其余混合情形：`overall = "部分对"`。

补充：

1. `overall = "部分对"` 可以包含 `"依据不足"` 的诊断点；`部分对` 表示“有成立部分，也有不成立或无法判断的部分”。
2. `overall = "对"` 不要求 `correction` 为空；`correction` 可以是“建议补充条件/测量指标”的建设性内容，只要所有 `verdict` 均为 `对`。
3. `overall` 不得优于其 `points` 所支持的最高结论；只要存在一个实质性的 `错` 或 `依据不足`，不得把整体写成 `对`。
4. 只要任一 `key_elements_required` 未覆盖，`overall` 不得为 `对`；要素覆盖是“对”的必要条件，不能由多个点中任意一个的 verdict 抵消。

### 3.4 coverage_level 与 verdict 联动

| `coverage_level` | 允许的 `verdict` | 额外要求 |
|---|---|---|
| `knowledge_backed` | `对 / 部分对 / 错` | 直接 `card_ref` 可逐字追溯；error_type 按原规则；`evidence_gap=null`；若存在逐字否定 claim 的字段，改用 `contradicted` |
| `ai_judged` | `对 / 部分对 / 错` | 知识卡无直接依据但不矛盾；至少 1 个非 checkpoint 锚点（`adjacent_concepts[...]`、`uncovered_dimensions[...]`，或用于范围判断的 `core_definition[...]`）；`ai_generated=true`、`unverified=true`；必须填 `classic_definition_comparison` 与 `deviation_note`；允许判 `对`；error_type 按 verdict 规则 |
| `contradicted` | `错` | 必须引用至少 1 个直接陈述被违反命题的知识卡字段；error_type.primary 非 `"无"`；`correction` 必须点名冲突字段；`evidence_gap=null` |
| `undetermined` | `依据不足` | error_type.primary=`"无"`，secondary=`null`；`evidence_gap` 必须说明缺什么信息，或点名 C1/C8；不得判 `对/部分对/错` |

补充：

1. `依据不足` 只允许与 `coverage_level="undetermined"` 搭配；`knowledge_backed`、`ai_judged`、`contradicted` 都不得搭配 `依据不足`。
2. `contradicted` 不是“证据不足”，必须能指出知识卡中直接冲突的字段；没有冲突字段时不得用它兜底。
3. `ai_judged` 可以判 `对`；不得再以“本地没有直接依据”为由强制降为 `部分对`、`错` 或 `依据不足`。
4. `ai_judged` 的证据不是本地知识卡直接结论，不得在 correction 或 summary 中声称“知识卡直接支持”；必须保留 `ai_generated=true`、`unverified=true`。
5. `undetermined` 不得搭配 `对`、`部分对` 或 `错`；只要 `verdict="依据不足"`，`evidence_gap` 就必须非空，并说明是 C1 主体歧义、C8 推断跳步，还是 claim 本身模糊/自相矛盾。

## 4. error_type 主/次优先级

### 4.1 枚举

`primary` 与 `secondary` 允许值：

```text
理解错误
知识错误
逻辑错误
完整性错误
表达问题
无
```

### 4.2 判定含义

| 类型 | 含义 |
|---|---|
| `理解错误` | 定义性混淆，例如把议程设置等同于框架理论、priming，或把第一层/第二层混为一谈。 |
| `知识错误` | 理论功能、事实归属或机制归属搞错，例如把框架理论的功能直接归给议程设置。 |
| `逻辑错误` | 前提与结论之间推理无效，例如充分条件误用、因果倒置、相关当因果。 |
| `完整性错误` | 缺少知识卡要求的必要成分或证据结构；缺的是 claim 的结构，不是外部事实。 |
| `表达问题` | 意思基本对，但表述过强、含混、指称不清或缺少限定。 |
| `无` | 该点没有错误，或该点 `coverage_level="undetermined"`、只能判 `依据不足`。 |

### 4.3 同时出现多个错误

1. `primary` 按以下优先级取最高：`理解错误` > `知识错误` > `逻辑错误` > `完整性错误` > `表达问题`。
2. `secondary` 取剩余错误中优先级最高者；没有第二个错误时必须为 `null`。
3. `secondary` 不得与 `primary` 相同。
4. `verdict="对"` 或 `verdict="依据不足"` 时，`primary` 必须为 `"无"`，`secondary` 必须为 `null`。

## 5. required_checkpoints：C1 与 C8

每个诊断点都必须在 `card_ref` 中包含：

```text
checkpoints[C1]
checkpoints[C8]
```

### C1：主体与议程是否说清

通过条件：`subject` 可唯一确定，且 `claim_span` 能看出所说的“议程/对象”是什么；若主体只是泛称（如“媒体”），但核心主张明确且与知识卡直接冲突，按下面的 `contradicted` 例外处理，不要求唯一消歧。

失败条件：claim 模糊到无法判断“这句话在说什么”，包括主体无法唯一消歧且核心主张不清，或 claim 没有说清被显著性转移的对象/议程。

C1 只在 claim 属于议程设置范围时检查主体与议程对象是否说清。若 claim 讨论的是另一个概念、但其自身的主体和对象清楚（如 C-01 讨论自由与私法），不按 C1 主体歧义处理，按第 2.4 节判 `coverage_level="ai_judged"`，并在 `classic_definition_comparison`/`deviation_note` 里写明“选错概念”。

C1 因 claim 过于模糊、无法判断“这句话在说什么”而失败时：`coverage_level="undetermined"`，`verdict` 只能为 `"依据不足"`，`error_type.primary="无"`，`evidence_gap` 必须点名 C1。

C1 失败导致 `verdict="依据不足"` 只适用于 `coverage_level="undetermined"`。若 claim 主体是泛称（如“媒体”），但核心主张明确且与知识卡直接冲突，判 `coverage_level="contradicted"`，不因主体泛化强制降级。此时 `subject` 允许写“新闻媒体/平台算法（泛称，不影响冲突判断）”，C1 不算失败。只有 claim 模糊到无法判断“这句话在说什么”时，C1 才失败并导致 `undetermined`。

### C8：经验前提与理论推断是否分开

通过条件：claim 把经验前提（曝光、接触、报道频率、测量结果等）与理论推断（显著性转移、公众重要性判断、效果结论等）分开表达，或至少能清楚区分。

失败条件：claim 把“曝光/接触”直接等同于“议程设置效果”，没有给出可区分的经验前提与效果推断。

C8 失败时：`coverage_level="undetermined"`，`verdict` 只能为 `"依据不足"`，`error_type.primary="无"`，`evidence_gap` 必须点名 C8，并可补充缺少的证据类型。C8 不负责判断知识卡有没有直接依据；知识卡无直接依据但不矛盾时走 `ai_judged`，不能因为 C8 失败就把该点改写成“没有覆盖”。

### 5.1 C2 的限定用途

`checkpoints[C2]` 允许且仅用于询问“媒体显著性是否可测量”的诊断点；C2 不是每个点的必填检查项，C1/C8 才是。

## 6. card_ref 允许路径列表

路径格式统一为 `字段[ID或键]`；只能使用知识卡中真实存在的路径，不得自造，也不得用自由文本替代。

允许的字段族：

```text
core_definition[E1] ... core_definition[E5]
necessary_boundary[B1] ... necessary_boundary[B5]
common_misreadings[M1] ... common_misreadings[M6]
adjacent_concepts[框架理论]
adjacent_concepts[priming]
adjacent_concepts[议程建构]
adjacent_concepts[算法策展/平台推荐]
uncovered_dimensions[知识卡中的实际维度ID]
uncovered_dimensions[知识卡中的实际维度ID].adjacent_tradition
conditions[知识卡中的实际组ID或索引]
acceptable_variants[知识卡中的实际条目ID或索引]
checkpoints[C1] ... checkpoints[C8]
sources[知识卡中的实际来源ID或索引]
```

补充规则：

1. `checkpoints[C2]` 适用于“媒体显著性是否可测量”的诊断点，用于检查报道频率、版面/时段、重复度等是否可观察。
2. `conditions` 与 `acceptable_variants` 的 ID/索引必须来自实际知识卡；没有对应条目时不得引用。
3. 每个诊断点至少包含 C1、C8，另按需引用 `core_definition`、`necessary_boundary`、`common_misreadings`、`adjacent_concepts` 或 `conditions`。
4. `coverage_level="knowledge_backed"`：`card_ref` 必须包含能直接支持该判断的字段；不得把相邻锚点伪装成直接依据。
5. `coverage_level="ai_judged"`：知识卡无直接依据但不矛盾；`card_ref` 至少包含 1 个非 checkpoint 锚点（`adjacent_concepts[...]`、`uncovered_dimensions[...]`，或用于范围判断的 `core_definition[...]`）；必须填 `ai_generated=true`、`unverified=true`、`classic_definition_comparison`、`deviation_note`；不得声称知识卡直接支持。
6. `coverage_level="contradicted"`：`card_ref` 必须包含至少 1 个直接陈述被违反命题的字段；`correction` 必须点名该字段；不得用“没有直接依据”代替“与知识卡冲突”。
7. `coverage_level="undetermined"`：`evidence_gap` 必须说明缺什么信息；若因 C1/C8 失败，必须点名 C1/C8；不得编造路径来避免 `undetermined`。

## 7. 12 条校验规则

1. 顶层必须含 `concept`、`claim`、`overall`、`points`、`summary`；`concept="agenda-setting"`，`claim` 与输入逐字一致，`points` 数量为 1–5。
2. 每个诊断点必须含 10 个核心字段：`claim_span`、`subject`、`card_ref`、`coverage_level`、`verdict`、`error_type`、`evidence_gap`、`correction`、`covered_key_elements`、`missing_key_elements`；`ai_judged` 点还必须带 `ai_generated=true`、`unverified=true`、`classic_definition_comparison`、`deviation_note`。
3. `claim_span` 必须是 `claim` 的连续逐字子串；不得改写、拼接或只写关键词。
4. `subject` 必须按第 2 节消歧；无法唯一消歧时必须写 `"未区分的新闻媒体/平台算法"`，且 C1 失败。
5. `card_ref` 必须非空、所有路径在白名单内，并且每个点都包含 `checkpoints[C1]` 与 `checkpoints[C8]`；`ai_judged` 点还必须至少含一个非 checkpoint 锚点；`contradicted` 点必须含直接冲突字段。
6. `coverage_level` 必须是四档之一；`verdict` 必须是四档之一；两者与 `error_type`、`ai_generated`、`unverified`、`classic_definition_comparison`、`deviation_note` 的联动必须满足第 3.4 节。
7. C1 主体歧义失败或 C8 失败时，`coverage_level` 必须为 `undetermined`，`verdict` 必须为 `"依据不足"`，`error_type.primary="无"`，`evidence_gap` 必填并点名失败的 checkpoint；C1 的“概念范围外但自身可判”按第 2.4 节走 `ai_judged`，不算 C1 失败。
8. `error_type.primary`/`secondary` 必须使用第 4 节枚举，主次优先级正确；`secondary` 不得与 `primary` 相同。
9. `correction` 必须非空，并引用至少一个实际 `card_ref` 路径及该字段要点；`verdict="对"` 时 correction 只能写建议性补充；`ai_judged` 的 correction 必须与 `classic_definition_comparison`、`deviation_note` 的判断一致。
10. `overall` 必须符合第 3.3 节聚合规则；`summary` 必须说明成立部分与不成立/无法判断部分，且不得与 points 冲突。
11. `covered_key_elements` 必须全部是知识卡 `key_elements_required` 中真实存在的 id，且不得重复；`missing_key_elements` 的 `id` 必须真实存在，`standard_statement` 必须与知识卡对应要素的 `standard_statement` 逐字一致。
12. 议程设置范围内的 `verdict="对"` 必须满足 `missing_key_elements=[]` 且 `covered_key_elements` 覆盖所有必需要素；`verdict="部分对"` 必须同时满足 `covered_key_elements` 非空与 `missing_key_elements` 非空；任一必需要素未覆盖时，顶层 `overall` 不得为 `"对"`。

## 8. 最小完整示例骨架

```json
{
  "concept": "agenda-setting",
  "claim": "用户完整原文",
  "overall": "对",
  "points": [
    {
      "claim_span": "用户原文片段",
      "subject": "新闻媒体",
      "card_ref": [
        "checkpoints[C1]",
        "checkpoints[C8]",
        "core_definition[E1]"
      ],
      "coverage_level": "knowledge_backed",
      "verdict": "对",
      "error_type": {
        "primary": "无",
        "secondary": null
      },
      "evidence_gap": null,
      "correction": "可依据 core_definition[E1] 补充测量指标。",
      "covered_key_elements": ["K1", "K2", "K3", "K4", "K5"],
      "missing_key_elements": []
    }
  ],
  "summary": "该说法覆盖了议程设置的必要要素。"
}
```

### 8.1 C-01：概念范围外的 ai_judged 示例

```json
{
  "concept": "agenda-setting",
  "claim": "自由就是在公理的限制下不被私法限制。",
  "overall": "对",
  "points": [
    {
      "claim_span": "自由就是在公理的限制下不被私法限制。",
      "subject": "自由（法权/自然法语境）",
      "card_ref": [
        "checkpoints[C1]",
        "checkpoints[C8]",
        "core_definition[E1]",
        "uncovered_dimensions[legal_natural_law].adjacent_tradition"
      ],
      "coverage_level": "ai_judged",
      "verdict": "对",
      "error_type": {
        "primary": "无",
        "secondary": null
      },
      "evidence_gap": null,
      "correction": "依据 core_definition[E1] 的议程设置定义范围与 uncovered_dimensions[legal_natural_law].adjacent_tradition：你这句话作为自由的定义是合理的，但它不属于议程设置要回答的问题。议程设置问的是媒体显著性如何转移，不是自由与私法的关系。如果你要讨论自由，请换概念；如果你要讨论议程设置，可以改成“平台推荐让我更常看到某些议题，但我还没证据说明这改变了公众对议题重要性的判断”。",
      "covered_key_elements": [],
      "missing_key_elements": [],
      "ai_generated": true,
      "unverified": true,
      "classic_definition_comparison": "不在范围内：这句话符合“法律下的自由/自然法传统”，但不符合议程设置的经典定义。",
      "deviation_note": "偏差不是“说错了”，是“选错概念”——用户选的是议程设置，这句话讨论的是自由与私法的规范关系。"
    }
  ],
  "summary": "这句话作为自由的定义成立，但它不属于议程设置要回答的问题；应切换概念，或改写为媒体显著性转移问题。"
}
```
