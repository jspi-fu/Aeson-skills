# 一手来源与版本核对

本表是规则溯源与版本查询入口，按当前问题打开需要的来源，不无差别抓取。优先读项目内已安装版本与配置，再在线核实版本敏感行为。历史 AI 质量研究与厂商产品承诺都不构成本项目的缺陷率、严重性或验收阈值。

## 来源性质

- 正式规范：记录适用版本、章节、成功准则或协议上下文，区分规范性要求与信息性示例；一项浏览器规范不等于该产品的全部验收要求。
- 官方实践指南：把建议与项目约束对照，推荐架构、工具与示例实现按候选对待。
- 框架与平台文档：先匹配实际版本、路由模式、运行环境与部署产品，一种框架的行为不推广到另一种。
- 性能参考值：区分行业推荐、合同指标与当前项目预算，附测量设备、网络、构建方式、样本、分位数与时间。
- 法规与合规：另核适用地区、合同与用户指定标准；技术指南推不出法律义务。
- 来源冲突：核对版本、条件与原文，保留无法解决的差异，统一结论不需要以删掉限定条件为代价。

## 版本核对步骤

1. 读 package.json、实际锁文件、packageManager 字段、运行时配置、框架配置与 CI，用已安装依赖的包元数据确认解析版本。
2. 同时记录声明范围与解析版本；`^` 与 `~` 不是实际安装版本，查版本时不自动升级或联网安装 latest。
3. 区分 dev、build、preview、生产服务器与 SSR/Edge 运行时，读真实脚本链确认 typecheck、lint、测试是独立执行还是被 build 包含。
4. 打开官方文档对应 major 页面、迁移指南或 release notes；只有滚动文档时记录查询日期与适用条件。
5. 浏览器行为记录目标浏览器、版本、操作系统、输入方式与必要真机结果；模拟器与单一引擎结果分开。
6. 可由网关或托管平台补充的能力读实际响应与部署配置；没有访问权限时标 blocked，源码缺失不等于部署能力缺失。
7. 具体漏洞查维护者公告与受影响/修复范围，再检查项目可达路径；扫描器级别不等于实际风险。
8. 结论记录来源标题、URL、适用版本与章节、访问日期和项目证据；持久文件用稳定 URL。

## 规范与浏览器

| 标识 | 一手来源 | 性质与使用边界 |
|---|---|---|
| HTML | [WHATWG HTML Living Standard](https://html.spec.whatwg.org/multipage/) | 浏览器平台规范。核对原生语义、表单、导航、iframe 与消息机制；语义正确不等于完整可用。 |
| FETCH | [WHATWG Fetch Standard](https://fetch.spec.whatwg.org/) | 网络与跨源协议规范。核对 credentials、请求、响应、重定向与 CORS；区分请求发出、服务器执行与响应可读。 |
| RFC9110 | [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) | HTTP 语义标准。按 9.2.2 节等对应内容核对幂等与重试；方法名是业务幂等证据之外的东西。 |
| RFC9111 | [RFC 9111 — HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html) | HTTP 缓存标准。核对可缓存性、认证、指令与验证器；应用自管缓存另有一套规则。 |
| MDN-CACHE | [MDN — Cache](https://developer.mozilla.org/en-US/docs/Web/API/Cache) | Web API 说明。核对 Cache API 的应用管理责任与限制；HTTP 缓存头与 Cache API 条目分开。 |

## 无障碍与性能

| 标识 | 一手来源 | 性质与使用边界 |
|---|---|---|
| WCAG22 | [W3C — WCAG 2.2](https://www.w3.org/TR/WCAG22/) | W3C Recommendation。按用户指定等级与适用成功准则审查；标准符合性与法律适用性分开，一次扫描覆盖不了全部准则。 |
| ARIA-APG | [W3C WAI — ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/) | 官方实践指南。参考 dialog、tabs、menu、combobox 等模式的语义与键盘行为。 |
| VITALS | [web.dev — Web Vitals](https://web.dev/articles/vitals) | 官方指标与体验建议。复核当期指标、推荐阈值与测量口径；实验室观察与真实用户分位数分开。 |

具体阈值、分位数口径与测量条件见 visual-accessibility-performance.md；引用时把 Web Vitals 当体验目标，与合同指标分开。

## 框架、构建与测试

| 标识 | 一手来源 | 性质与使用边界 |
|---|---|---|
| REACT-BOUNDARY | [React — Error Boundary](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary) | React 实现文档。核对渲染异常、生产上报与捕获范围；按版本核查事件、异步、SSR、自身错误及 transition 例外。 |
| TS-BASICS | [TypeScript — The Basics](https://www.typescriptlang.org/docs/handbook/2/basic-types.html) | 语言工具文档。核对静态检查、输出与类型擦除；类型标注不是运行时数据校验。 |
| VITE-FEAT | [Vite — Features / TypeScript](https://vite.dev/guide/features#typescript) | 构建器文档。区分转译与完整类型检查，先看项目 build 脚本是否另行执行 tsc 或其他 checker。 |
| VITE-ENV | [Vite — Env Variables and Modes](https://vite.dev/guide/env-and-mode) | 配置与模式文档。核对暴露前缀、构建时替换与环境优先级；判定秘密是否进入客户端以实际构建产物为准。 |
| VITE-BUILD | [Vite — Building for Production](https://vite.dev/guide/build) | 生产构建文档。核对目标浏览器、资源 base、懒加载与构建选项；默认值随 major 变化。 |
| PLAYWRIGHT-BP | [Playwright — Best Practices](https://playwright.dev/docs/best-practices) | 官方测试实践。参考用户可见行为、隔离、断言等待、trace 与浏览器矩阵。 |
| PLAYWRIGHT-A11Y | [Playwright — Accessibility Testing](https://playwright.dev/docs/accessibility-testing) | 官方测试范围说明。核对自动检查覆盖、状态扫描与人工评估要求；WCAG 规则与工具附加规则分开。 |

遇到 Vue、Angular、Next.js、Svelte、组件库、路由器或数据请求库时补查其官方对应版本文档；本表列举的工具不构成迁移目标，Vite 的行为也推广不到其他框架的 build。

## 安全与数据权限

| 标识 | 一手来源 | 性质与使用边界 |
|---|---|---|
| OWASP-FE | [OWASP — Web Frontend Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Web_Frontend_Security_Cheat_Sheet.html) | 安全实践指南。核对客户端信任边界、秘密、文本与 HTML 渲染。 |
| OWASP-AUTH | [OWASP — Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) | 授权实践指南。核对每请求、对象、字段、静态资源与默认拒绝，检查落在可信服务层。 |
| OWASP-HTML5 | [OWASP — HTML5 Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html) | 浏览器安全实践指南。核对 Web Storage、消息来源、跨域、嵌入与离线存储。 |
| OWASP-CSRF | [OWASP — CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html) | 按架构选择防护的指南。核对身份携带、服务器校验与等效机制；判定可利用性需要架构与路径证据。 |
| OWASP-LOG | [OWASP — Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) | 日志与隐私实践指南。核对事件关联、敏感数据排除、日志失败、访问与告警。 |
| SUPABASE-RLS | [Supabase — Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security) | 产品与数据库授权文档。核对 grants、policy、角色、操作、视图/函数及测试；公开 anon key 与服务端私密 key 分开判断。 |

需要 XSS、CSP、上传、会话、OAuth 或供应链细节时，从相关 OWASP 条目进入其专题与项目所用框架的官方防护文档，先建立适用威胁与执行路径再引用建议。接入 Sentry 等监控或回放 SDK 时查实际版本的事件捕获、默认采集、脱敏、source map 与 release 文档，并用合成标记验证。

## 交付与运维

| 标识 | 一手来源 | 性质与使用边界 |
|---|---|---|
| NPM-CI | [npm — npm ci](https://docs.npmjs.com/cli/v11/commands/npm-ci/) | 包管理器文档。核对锁文件一致性与干净安装；链接固定 v11，其他版本切换对应文档。 |
| GHA-SECURE | [GitHub Actions — Secure Use](https://docs.github.com/en/actions/reference/security/secure-use) | 平台安全实践。核对最小权限、第三方 action 引用、不可信输入与 secrets；平台默认值使用时复核。 |
| VERCEL-ROLLBACK | [Vercel — Instant Rollback](https://vercel.com/docs/instant-rollback) | 托管平台文档。用于核查部署与配置恢复边界；数据库、外部 API 与旧客户端兼容性另判。 |

## 在报告中引用

硬性不符合项给适用规范与具体条款；建议项给参考依据、收益与适用条件。来源证明规则存在，项目证据才证明行为发生，两者分开写；版本差异写成"项目版本 + 文档版本 + 已验证行为"，无法匹配时降低确定性并列出下一步。工具营销、媒体转述与其他项目事故都不进入本项目的判定依据。
