# 审查台账与覆盖协议

audit.json 是机器可检查的事实台账，Markdown 是面向人的解释；两边结论必须来自同一份记录。UTF-8，schema_version "1.0"，扩展字段允许。`check` 会点名缺失的标量字段；`init` 只生成 project、四条项目检查、gates 与 progress 的骨架，其余实体初始为空数组，其内部键见第 1 节末尾的形状表。需要某实体的完整必填清单时，把它的记录清到只剩 id 再跑 `check`，报错会逐条点名。

## 1. 实体与覆盖单位

| 实体 | ID | 覆盖含义 |
|---|---|---|
| 项目 | PRJ-001 | 本次约定的目标、访问能力与基线 |
| 页面 | PAGE-001 | 路由模板、独立页面/子应用、具有独立任务的虚拟页面 |
| 组件定义 | DEF-001 | 一个实际实现；同名但实现不同应拆分 |
| 组件实例 | CMP-001 | 某页面中具有独立思考位置、props、上下文的逻辑 UI 单元 |
| 场景 | SCN-001 | 明确身份、数据、环境和事件顺序的验证 |
| 检查 | CHK-001 | 某个目标在一个维度下的可回答问题 |
| 证据 | EV-001 | 实际读取/执行/观察的定位记录 |
| 问题 | FND-001 | 具有实际/预期差异、影响、证据与归因的发现 |
| 组件蓝图 | BP-001 | 一份当前与目标组件契约，允许多实例复用 |
| 任务 | TASK-001 | 可单独实施、验证、恢复的变更或补证动作 |
| 门槛 | GATE-001 | 与产品目标相匹配的发布前条件 |

判定 CMP 的依据是它承担独立的语义、交互、状态、布局或数据责任：页壳、布局区域、文本信息、图标、按钮、菜单项、错误消息、条件出现的内容都要登记。纯装饰与纯包装节点归入最近负责组件的 layout_content 检查，并在实例备注交代归属。同一页面的顶部与底部两个保存按钮是两个 CMP，底层 DEF 可以共享。

重复数据行登记模板加上所有 props/权限/状态/布局契约不同的实例类别，写明等价分组依据与代表数据；新增页、组件分支或参数类别时扩大分母并保留稳定 ID。

嵌套对象与数组元素的键（骨架与报错都不会给出）：

- `project.baseline`：source_ref、runtime_ref、observed_at
- `project.inventory_sources[]`：kind、locator、evidence_ids；reconciled 时每项 evidence_ids 非空
- `project.out_of_scope[]`：surface、reason、authority
- `project.assumptions[]` 等说明数组：每项为非空字符串
- `scenarios[].context`：role、data、network、viewport、input、lifecycle 六项齐全，每项为非空字符串或字符串数组；不适用的一项写具体原因，`N/A` 不算；`steps` 与 `expected` 是非空字符串数组
- `findings[].reproduction`：preconditions、steps
- `findings[].decision`（仅 accepted_risk 与 dismissed）：reason、authority
- `findings[].resolution_evidence_ids`：数组，暂无内容也保留

## 2. 枚举词表

`check` 只报告"invalid"，合法取值以此处为准；发现级别 P0–P3 的后果判断标准见 SKILL 第 6 节。

- mode：audit_plan | implement
- review_depth：quick | full。quick 不要求台账，也不能取得完整覆盖、完整方案或发布就绪结论；SKILL 第 1 节"未指定深度时选 quick"讲的是本次审查的选择，本行"旧台账缺该字段时按 full 校验"讲的是历史台账兼容，两者不是一条规则。
- access_mode：source_runtime | source_only | runtime_only | screenshots_only
- inventory_status：discovering | reconciled | limited。reconciled 只用于已核对全部可用发现渠道并解决差异；仍可能存在未能发现的角色页面用 limited。
- scope_status：in_scope | excluded（排除要写理由与依据来源）
- source_status：located | unavailable | inferred（后两者要把推测标为待确认，不计入静态通过）
- criticality：high | normal
- evidence.kind：source | runtime | test | measurement | artifact | specification
- check/scenario/gate status：not_checked | passed | failed | blocked | not_applicable；scenario 另有 planned（场景已设计、本轮决定不执行，与"缺能力所以执行不了"的 blocked 区分）
- finding severity：P0 | P1 | P2 | P3
- finding confidence：confirmed | probable | needs_validation；"已确认 FND"指 confidence 为 confirmed
- finding status：open | in_progress | fixed_unverified | resolved | accepted_risk | dismissed
- disposition：retain | configure | refactor | replace | remove | investigate
- task status：planned | in_progress | implemented | verified | blocked | deferred

必评维度是词汇表也是分母：项目层 reproducibility、architecture、security_boundaries、delivery_observability；页面层 routing_history、state_coverage、responsive_content、journey_integration；实例层八维见 SKILL 第 5 节。同一维度可有多条具体检查，用多个原子问题覆盖不同风险；静态与运行检查分列成行。

## 3. 状态使用条件与证据能证明什么

- passed：列出的每条具体预期都有充分证据。
- failed：有证据证明实际违反明确预期，并关联已确认 FND。源码可确认的缺陷用 failed CHK 表达，未执行的场景不因此写 failed。
- blocked：缺环境、账号、工具、数据、源码或合同，写明缺口、所需证据和下一步。
- not_applicable：说明该目标为何适用；不能用它代替无法验证。
- resolved 的 FND 需要 resolution_evidence，且至少一项是 source/runtime/test/measurement；specification 与 artifact 本身不足以证明修复已验证。其关联的当前 CHK/SCN 必须是 passed 或有理由的 not_applicable；失败与修复前证据保留版本与时间。
- verified 的 TASK 需要 runtime/test/measurement 证据、全部依赖已 verified、验收场景至少一项 passed；implemented 停留在 implemented 直到证据到位。
- accepted_risk 与 dismissed 需要 decision.reason 与 decision.authority，接受风险由用户或负责人决定。
- 只有源码时，静态可确认的因果写成 failed CHK 配 source EV，其运行影响另建 blocked SCN；behavior、states、semantics_accessibility 等维度要 passed 需要 runtime 或 test 证据并链接通过的场景，纯源码审查把它们写成 failed 或 blocked，不写成 passed。根因已确认、后果待验证时 FND 的 confidence 保持 probable 或 needs_validation，此时该 CHK 不能同时是 failed 又与该发现并列通过。
- 门槛不适用时把 required 一并置为 false（`init` 生成的门槛默认 required=true）；保留 required=true 的 not_applicable 门槛仍计入未完成。

各证据类型能证明的范围：source 证明读过的文件与符号、关键控制流；runtime 证明实际观察到的 URL、操作与结果；test 证明实际执行命令与环境退出状态；measurement 只在记录设备/浏览器/构建模式/样本条件时支撑性能结论；artifact（截图、录像、设计稿）只覆盖图中已展示的状态；specification 表示预期，不表示已实现。行为、状态、键盘、异步、路由和完整旅程需要 runtime 或 test 证据。

每个 in_scope 页面和实例至少关联一个 SCN，高风险实例关联高风险场景；断言写成用户可观察或服务端可验证的结果。

## 4. target_contract 十维（唯一定义处）

每个已登记 DEF 至少一份 BP，包括尚无 CMP 引用但保留在正式台账中的定义。逐项写到该组件的实际属性、事件、状态、调用者与变更位置：

1. responsibility：职责与边界。
2. interface：props/events/slots/输出与兼容策略。
3. states：有效状态、转换、逆向、中断、恢复。
4. data_effects：权威数据来源、缓存、请求、取消、清理。
5. semantics_accessibility：语义、名称、焦点、键盘、动态反馈。
6. styling_layout：token、布局、内容边界、响应式、层级、动效。
7. performance_lifecycle：渲染、资源、生命周期与预算。
8. security_privacy：信任边界、授权依赖、数据最小化。
9. observability：必要错误、事件、诊断与脱敏。
10. integration：父子契约、其他页面与服务依赖。

纯静态叶子写适用范围与不适用理由即可；源码不可得的项标待确认，不假造函数签名。每个 CMP 恰好一份 component_plan；configure/refactor/replace/remove/investigate 链接 TASK，retain 与 investigate 也要本实例的理由与复验场景。除正式接受或排除的风险外，每个问题由 TASK 负责解决或确认，resolved 的 FND 保留 TASK 以追溯实施与复验。

## 5. 覆盖口径与门槛

分六项分别报告，不合成一个模糊百分比：

1. 发现完整度：各渠道核对情况、路由与运行入口差异、外部子应用与动态分支限制。
2. 页面覆盖：in_scope 分母，已访问、静态已读、运行已验证、blocked。
3. 组件覆盖：DEF 与 CMP 分开，必评维度与实例场景是否齐全。
4. 场景覆盖：计划、实际通过、实际失败、阻塞、高风险数量。
5. 方案覆盖：DEF 是否都有 BP、CMP 是否都有处置、FND 是否都有 TASK、依赖是否无环。
6. 发布门槛：哪些已满足、哪些未满足、证据基线是否一致。

`audit_coverage_closed` 表示声明范围内的发现已核对且必需检查与场景都已判定，允许存在已确认失败，因此不等于可发布。`definitions_without_blueprints`、`instances_without_plans`、`findings_without_tasks` 是方案缺口，阻止 `--require-plan`，但不否定已完成的审查覆盖。`production_gates_satisfied` 只表示台账中声明的门槛满足，不叫安全认证，也不承诺没有遗漏。not_applicable 不增加通过项，blocked 不进入完成项。

必要门槛按 production_profile 选取：核心流程与异常恢复、对象/租户权限、关键可访问性、数据一致性、生产构建、性能预算、可观测性、发布与恢复。门槛不适用要写原因。

## 6. 分批与续接

progress 保留 current_page（PAGE ID 或 null）、completed_batches、next_actions、unresolved_access、last_updated；后三者是说明数组或时间字符串，"暂无下一步"写空数组而不是 null，以免破坏交接报告。

先把全量清单与最低检查占位和 progress 写入台账，之后每完成一页或一批共享组件立刻保存增量。时间或上下文不足时保留所有未检查项并继续后续批次。

并行时按页、DEF 或领域划分，由主代理统一分配 ID 并归并去重；主代理维护唯一 audit.json，子代理提交带来源的局部记录。
