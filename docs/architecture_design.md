# flutoolpro 架构设计要点

> 语言无关的架构视角总结：高内聚低耦合、插件化 harness、横切关注点统一管理（主题/日志/配置）、开发与打包环境分离、数据流。本文是 **flutoolpro**（Flutter 复刻版，见第 10 章）的目标架构蓝图；现状分析基于当前 PyQt5 版 FluTool，作为迁移基线。

## 1. 背景与动机

对主题样式做深度扫描后发现：`setStyleSheet` 405 处、硬编码色值 895 处、主题监听 47 处。根因不是 QSS，而是架构问题：

> **横切关注点（cross-cutting concern）被放到了每个插件里各自实现。**

主题、日志、配置、事件这些能力，每个插件都在重复实现"判断主题 → 写颜色 → 自己监听信号"。本文从架构层面给出统一设计，供后续演进参考，与具体代码语言无关。

## 2. 核心分层与依赖方向

```text
Kernel（内核）  ←──── 唯一依赖方向 ────   Plugins（插件）
```

- **内核**：事件总线、服务容器（DI）、插件管理器、主题系统、数据层、日志、配置。
- **插件**：只依赖内核暴露的接口，不依赖其他插件（除非显式声明）。
- **禁止反向依赖**：内核永不 import 插件实现，这是插件系统可解耦、可替换、可测试的前提。

### 高内聚低耦合的落地

| 原则     | 落地方式                                                              |
| :------- | :-------------------------------------------------------------------- |
| 单一职责 | 每个模块只做一件事：`Widget -> Service -> Repository/DatabaseManager` |
| 依赖倒置 | 插件依赖接口（`ctx.db()`），不 import 具体实现                        |
| 最少知识 | 插件不知道其他插件内部结构，跨插件通信走事件总线                      |
| 显式依赖 | 依赖通过容器注入，不用全局单例到处 import                             |

## 3. 插件化 Harness 架构

### 3.1 契约先行（Contract-first）

每个插件通过 manifest 声明，而不是靠运行时扫描猜测：

```text
插件 = manifest（元数据） + 接口实现 + 资源
```

- manifest 必要字段：
  - `id`：全局唯一插件 ID。
  - `name`：显示名称。
  - `order`：序号 / 优先级，决定导航中的排序（数值越小越靠前）。
  - `icon`：图标（可为空，但字段必填，用于导航显示）。
  - `visible`：显示 / 隐藏（`false` 表示不在 UI 上展示导航入口，但仍可注册服务、参与功能）。
  - `version`：版本号。
  - `dependencies`：依赖的服务。
  - `theme_tokens`：消费的主题 token（声明式消费）。
  - `entry`：激活入口（懒加载触发点）。
- 接口：`activate(context)` / `deactivate()`，生命周期由 harness 管理。
- 内核按 manifest 决定：何时加载、注入什么、能访问什么。

FluTool 基线：`plugin.py`（开发环境）与 `plugins/plugin_index.py`（打包环境）双源 manifest，扫描阶段用 `ast.literal_eval` 解析、**绝不执行插件代码**。

flutoolpro 调整（Flutter 关键差异）：**Dart AOT 编译后无法运行时加载 Dart 代码**，动态 import 不可行——改为 build_runner 生成**静态注册表**；manifest 保留（排序、可见性、依赖声明的数据源），激活入口编译期固定。

### 3.2 生命周期

```text
注册(scan) → 解析(parse manifest，不加载代码) → 初始化(注入依赖)
  → 激活(懒加载：用户点开才实例化) → 挂起/销毁
```

关键：**扫描阶段不执行插件代码**；**懒加载激活**——未点开的插件不实例化、不参与全局事件刷新（这正是"没点开插件时主题切换很快"的原因）。

### 3.3 服务容器（DI）

插件需要的服务（数据库、搜索、主题、日志）通过接口从容器取：

```text
容器注册:  ThemeProvider、AppDatabase、SearchService、LogManager
插件注入:  void activate(PluginContext ctx) { ctx.theme; ctx.db; }
```

好处：可替换（mock 测试）、可隔离、依赖清晰，避免"插件 import 具体实现"导致测试污染真实数据。

### 3.4 事件总线解耦

跨插件通信走事件总线，不直接互调：

```text
发布:  event_bus.publish("note.created", note_id)
订阅:  event_bus.subscribe("note.created", handler)
```

注意：**主题切换虽然是全局事件，但不该靠每个订阅者各自处理**（见第 4 节推拉模型）。

### 3.5 懒加载

- 未激活的插件不建 widget、不连信号、不参与主题刷新。
- 激活时按需初始化，退回到挂起状态时释放资源。

## 4. 横切关注点统一管理

### 4.1 主题样式统一管理（重点）

#### 主题健康度审计（通用检查项）

不依赖具体项目，评估主题是否被正确托管，可检查以下指标：

| 检查项      | 健康信号                | 不健康信号                 |
| :---------- | :---------------------- | :------------------------- |
| 颜色字面量  | 集中在 token 模块       | 散落各页面，同色值多处重复 |
| 主题切换    | 单一 Provider 传播      | 每页面各自监听、各自刷新   |
| 样式来源    | 统一模板 / 主题对象生成 | 页面各自拼装样式表字符串   |
| 深/浅色取值 | 通过 token 引用         | 三元硬编码散落各文件       |

色值治理方法论（可直接套用）：
1. **灰阶中性格**（背景/卡片/边框/文字/网格）——占重复色值的大多数，抽成 token。
2. **品牌强调色**——数量少、全局统一，固定 token。
3. **低频业务色**（状态/图表）——就地使用，不抽。

#### 目标模型：三层

```text
1. Design Tokens（唯一色板源）
   light = { bg, card, border, text, grid, accent ... }
   dark  = { ... 同一组 token ... }

2. ThemeProvider（内核唯一持有者）
   持有当前主题状态，负责传播；不负责具体 widget 样式。

3. 消费端（插件）
   声明"我要哪些 token"，渲染时从 Provider 取；永远不写颜色字面量。
```

#### 推送 vs 拉取（核心机制）

- **推送（现状）**：主题变了，广播给 47 个监听者，各自重刷 → 谁漏刷新谁错。
- **拉取（目标）**：插件只在渲染时从 Provider 取 token，Provider 让依赖它的组件自动重建。

推拉的区别就是"47 处监听"与"0 处监听"的区别。实现载体随语言不同：Flutter 用 `Theme.of(context)` / `InheritedWidget`，PyQt 用统一样式表生成 + 信号，Web 用 CSS 变量 —— 结构一致。

#### 优化路径（分阶段、可回滚）

```text
阶段 1  定 Design Tokens（灰阶 + 品牌 + 语义，集中一处）
阶段 2  token 生成 forui 主题（CLI / Forui Create），light/dark 两套 FThemeData
阶段 3  主题切换走框架级重建：ThemeMode Provider + FApp 双主题注入
阶段 4  页面全部经 context.theme 拉取取色，消灭颜色字面量
```

每阶段独立验证、可单独回滚。主题 token 进插件 manifest 声明，插件未激活时不参与主题刷新。

### 4.2 日志管理

- 统一由内核的 `LogManager` 提供，插件不自己写日志文件。
- 关键流程记录日志，异常日志保留上下文（异常类型、调用链、输入片段）。
- 测试环境日志与真实环境日志隔离。

### 4.3 配置管理

- 配置统一由内核提供（`core/settings.dart`），业务配置写入数据库，偏好写入 `shared_preferences`。
- 插件不直接读写配置文件，通过配置接口读写自己的命名空间。
- 配置变更通过事件总线广播，但同样遵循"拉取"优先，避免逐插件监听。

## 5. 开发环境与打包后环境分离

核心：**代码中不硬编码任何本机路径**，运行时目录由平台 API 提供。

- 路径统一经 `path_provider`：数据用 `getApplicationSupportDirectory()`，资源用 `assets/`（编译期打包进应用）。
- 运行时数据目录启动时创建，不随包分发，无"把开发数据打进安装包"的问题。
- 资源收集：`pubspec.yaml` 的 `assets:` 声明；环境差异用 `--dart-define`（构建模式、API 地址）注入，不存在 PyInstaller 式 `--add-data` 问题。
- 插件收集：静态注册表随编译收集（见第 3.1 节），开发/打包行为一致，无双源 manifest 问题。
- 数据恢复：替换数据库文件后重建 drift 连接（重新 open `AppDatabase`）并刷新相关插件，保证 UI 显示当前数据。

## 6. 数据流

```text
Widget ──调用──> Service ──调用──> Repository ──> AppDatabase（drift）
                                      │
        Repository 注册 ◄──────────────┘        ImportService（导入/导出）
```

- **连接层**：`AppDatabase` 统一管理连接，外键约束在 `beforeOpen` 执行 `PRAGMA foreign_keys = ON`；Flutter 单事件循环天然避免并发竞争，耗时查询/导入导出走 isolate。
- **Schema / 迁移**：drift schema + migration 负责结构演进，业务不直接执行 DDL。
- **仓库注册**：集中注册各业务 Repository（容器），避免插件各自持有连接。
- **导入服务**：`ImportService` 统一处理导入导出（含 WAL checkpoint、zip 打包等细节）。
- **事务边界**：事务在 Service 层控制，Widget 不承载事务、校验和数据库异常处理。

## 7. 测试与可验证性

- 测试位于 `test/`（与 `lib/` 镜像），每次改动后运行 `flutter test`。
- 测试必须隔离真实数据目录（临时目录注入，替代真实 `getApplicationSupportDirectory`）。
- Service 层与 UI 分离，保证业务逻辑可用纯 Dart 单测覆盖（不依赖 widget 渲染）。
- 架构约束（如 `core/` 不依赖 `ui/`）通过测试维护，防止回归。

## 8. 原则清单（语言无关，可直接套用到任何项目）

1. **横切能力归内核**：主题/日志/配置/事件，插件永远不重复实现。
2. **契约先于实现**：manifest 和接口先行，插件实现靠后。
3. **依赖单向**：内核 ← 插件，禁止反向依赖。
4. **扫描不执行**：解析元数据，不跑插件代码。
5. **懒加载激活**：未用不实例化，未激活不参与全局刷新。
6. **推送改拉取**：状态变更由 Provider 传播，消费方不自己监听。
7. **服务容器注入**：接口取依赖，不 import 实现。
8. **声明式消费**：插件声明需求（token、服务），内核按声明供给。
9. **路径不硬编码**：运行时目录由内核创建，开发/打包环境分离。
10. **数据访问分层**：Widget → Service → Repository → DatabaseManager，事务与异常在 Service 层。

## 9. 目标文件结构设计（初步）

综合前述各章，给出 **flutoolpro** 的目标目录结构。当前 FluTool 代码目录为"现状"，本节为"目标"；迁移按第 4.1 节分阶段进行。

```text
flutoolpro/                         # Flutter 复刻项目根
├── lib/                            # Dart 源码（Flutter 惯例放 lib/ 下）
│   ├── main.dart                   # 启动入口：装配 ProviderScope → 读静态注册表 → FApp（forui 主题壳）
│   │
│   ├── core/                       # 内核：不依赖 ui/，不依赖任何插件
│   │   ├── container.dart          # 服务容器（DI）：Riverpod Provider / get_it
│   │   ├── app_core.dart           # 应用装配：容器初始化、插件生命周期编排
│   │   ├── plugin_manager.dart     # 插件管理器：读静态注册表 / 懒激活 / 销毁
│   │   ├── plugin_interface.dart   # 插件契约：activate(ctx) / deactivate()
│   │   ├── plugin_manifest.dart    # manifest 模型（id/order/icon/visible/依赖）
│   │   ├── plugin_registry.dart    # 静态注册表：build_runner 生成（AOT 无动态加载）
│   │   ├── event_bus.dart          # 事件总线：Stream 广播
│   │   ├── log.dart                # LogManager：统一日志（内核唯一）
│   │   ├── settings.dart           # 配置管理器：业务配置读写
│   │   ├── search.dart             # 全局搜索核心
│   │   ├── runtime_layout.dart     # path_provider 目录布局（数据/缓存）
│   │   ├── theme/                  # 主题系统（横切能力归内核）
│   │   │   ├── tokens.dart         # ① Design Tokens：深浅两套色板（唯一色值源）
│   │   │   ├── app_themes.dart     # ② forui 主题构建：tokens → FThemeData（light/dark）
│   │   │   └── theme_provider.dart  # ③ Riverpod StateNotifier<ThemeMode>（切换传播）
│   │   └── ai/                     # AI 能力（服务）
│   │       ├── provider_base.dart
│   │       ├── chat_service.dart
│   │       └── providers/           # deepseek / ollama / openai_compatible
│   │
│   ├── storage/                    # 数据层：drift（连接/schema/迁移/DAO）
│   │   ├── database.dart           # AppDatabase：连接 + PRAGMA foreign_keys
│   │   ├── migrations.dart         # drift schema 演进
│   │   └── repositories/            # 各业务 Repository / DAO
│   │
│   ├── ui/                         # 宿主 UI：只负责导航与显示
│   │   ├── main_shell.dart         # NavigationShell：导航 + 页面切换
│   │   ├── plugin_host.dart        # 插件页容器：懒加载 widget、触发数据加载
│   │   └── ...
│   │
│   └── plugins/                    # 插件：只依赖 core 接口，平级 + 分组两种形态
│       ├── <simple>/              # 独立插件：一个文件夹 = 一个导航入口
│       │   ├── plugin.dart         # manifest 声明（id/name/order/icon/visible）
│       │   ├── service.dart        # 业务逻辑：事务/校验/异常
│       │   ├── repository.dart     # 数据访问（复杂插件可选）
│       │   ├── page.dart           # 界面：Theme.of(context) 取色，不写颜色字面量
│       │   └── resources/           # 资源 → 声明进 pubspec.yaml assets
│       └── <group>/               # 父插件（分组容器）：主导航一个入口，子插件为内部页签
│           ├── plugin.dart         # manifest 声明（type: group）
│           ├── shared/             # 子插件共享组件（放父插件根目录）
│           └── <sub>/             # 子插件：manifest 声明 parent 字段，结构同独立插件
│               ├── plugin.dart     # manifest（id/name/order/icon/visible/parent）
│               ├── service.dart
│               ├── page.dart
│               └── resources/
│
├── assets/                         # 图标/图片/字体资源（编译期打包）
├── test/                           # flutter_test（与 lib/ 镜像）
│   ├── core/                       # 内核测试（容器、主题、插件管理）
│   ├── storage/                    # 数据层测试
│   └── plugins/                    # 各插件测试
├── pubspec.yaml                    # 依赖 + assets 声明
├── build.yaml                      # build_runner 配置（生成插件注册表）
└── docs/
```

### 9.1 关键设计点

1. **主题归 `core/theme/` 而非 `ui/`**：`tokens.dart` 是纯数据；`app_themes.dart` 只依赖 forui（token → FThemeData 构建，light/dark 两套），均不依赖 `ui/`，满足"内核 ← 插件"单向依赖；页面经 `context.theme` 拉取，主题切换由框架级重建完成（对应第 4.1 节"推送改拉取"）。
2. **服务容器统一注入**：Riverpod（Windows 桌面已验证）或 get_it；插件通过 `activate(ctx)` 的 `ctx` 取服务，不 import 具体实现——借鉴 DSH 的 `apply(ctx)` + `inject` 依赖声明，避免隐式 import 造成的测试污染与循环依赖。
3. **插件目录规范**（对照 DSH 插件约定 + Flutter 特性）：
   - **静态注册**：Dart AOT 无法运行时加载代码，插件经 build_runner 生成注册表（`plugin_registry.dart`），编译期收集；`--dart-define` 可按环境裁剪插件集。
   - manifest 仍保留：排序（`order`）、可见性（`visible`）、依赖声明的**数据源**（运行时读取排序导航），激活入口编译期固定。
   - 复杂插件强制 `service.dart` / `repository.dart` 分层，`page.dart` 不承载事务与异常。
   - `resources/` 声明进 `pubspec.yaml` 的 `assets:`，编译期打包，全新环境可用。
4. **测试镜像目录**：`test/` 按 `core/`、`storage/`、`plugins/` 镜像，架构约束（如 `core/` 不依赖 `ui/`）用测试守护。

### 9.2 FluTool 现状 → flutoolpro 目标 迁移对应

| FluTool 现状（基线）                   | flutoolpro 目标                                    |
| :------------------------------------- | :------------------------------------------------- |
| `setStyleSheet` / `isDarkTheme()` 三元      | forui FThemeData + `context.theme`          |
| 47 处 `themeChangedFinished` 监听      | ThemeMode Provider，框架级自动重建（0 处手动监听） |
| 插件动态扫描 + 动态 import             | build_runner 静态注册表（AOT 约束）                |
| 插件直接 import 服务/连接              | `activate(ctx)` / Riverpod 注入                    |
| 主题 token 散落各插件                       | `tokens.dart` 唯一色板源                     |

### 9.3 子插件设计（分组插件）

**模型**：父插件是"分组容器"——主导航占一个入口，子插件是内部页签（对应 FluTool 的 `dev_tools` / `text_tools` 形态：json_tool、vocabulary 等挂在分组下）。

#### manifest 扩展

- 父插件：`type: "group"`，只持有导航壳（TabBar / 页签切换），不承载业务逻辑。
- 子插件：增加 `parent: "<group_id>"` 字段，其余字段与独立插件一致（`order` 在**组内**排序）。

#### 依赖规则（防耦合关键）

| 方向 | 规则 |
| :--- | :--- |
| 子插件 → 父插件 `shared/` | 允许（显式依赖，单向） |
| 子插件 ↔ 兄弟子插件 | 禁止，跨子插件通信走事件总线 |
| 父插件 → 子插件实现 | 禁止，父只经注册表感知子插件，页签由注册表路由 |

父插件的导航壳从 `plugin_registry.dart`（build_runner 生成的树）读子插件清单，经注册表解析页面工厂渲染页签——父**不 import** 任何子插件的具体页面，增删子插件不改父插件代码。

#### 生命周期粒度

- 懒加载按**子插件**粒度：点开某个页签才实例化该子插件，其余兄弟不实例化、不参与主题刷新（组激活 ≠ 全组实例化）。
- 父插件激活 = 只构建导航壳 + 读取子插件清单。

#### 静态注册表（树形构建）

- build_runner 扫描全部 manifest，按 `parent` 字段组装插件树：`[{id: group, children: [sub1, sub2, ...]}, {id: simple}]`。
- 主导航按顶层 `order` 排序，组内页签按子插件 `order` 排序。
- `visible: false` 的子插件不显示页签，但服务仍注册（可被搜索、事件调用）。

#### 与 FluTool 基线对应

| FluTool 现状 | flutoolpro 目标 |
| :--- | :--- |
| `dev_tools` 等分组插件 + 子插件文件夹 | `<group>/` + `parent` 字段（结构一致） |
| 子插件统一 `page.py` 命名 | 子插件统一 `page.dart` 命名 |
| 共享组件放分组根目录 | `shared/` 放父插件根目录 |
| `plugin_index.py` 平铺注册 | build_runner 生成树形 `plugin_registry.dart` |

## 10. Flutter 复刻版命名（flutoolpro）

- **用途**：未来 Flutter 版复刻项目，与当前 PyQt5 版 FluTool 并存、独立仓库、独立发布。
- **名称**：`fluToolPro`（仓库 / 包名 / 可执行名 `flutoolpro`）。
- **命名含义**：`flu`（Flutter + 流畅）+ `tool`（延续 FluTool 品牌）+ `pro`（下一代增强版）。
- **与 FluTool 的关系**：
  - 品牌延续：图标风格、命名体系保持一致，便于用户识别。
  - 架构延续：按第 9 章目标结构实现，插件模型、服务容器、主题 token 三件套原样落地。
  - 数据兼容：SQLite schema 保持兼容（drift 读写同一 schema，可直接复用建表/迁移逻辑），数据目录独立（避免两版并存时互相覆盖）。
- **技术选型（试行，forui 先试）**：
  - **UI 组件库：forui**（v0.26+，Duobase 公司维护）。
    - 选型理由：shadcn/ui 极简现代风、桌面 + 触屏双场景设计；`Forui Create` 可视化设计主题 + 内置 CLI 生成主题样板，与 `tokens.dart` → 主题的工作流契合；自带 i10n；测试覆盖完善。
    - 约束：最新版要求 **Flutter 3.47+**；仍处 0.x，API 有破坏性变更——锁定版本使用，升级逐版本核对 CHANGELOG。
    - 备选：`fluent_ui`（要 Fluent 视觉延续时切换）、`shadcn_flutter`（组件更多、纯 `widgets.dart` 无 Material 依赖，但个人维护 0.0.x）。
  - **状态管理：Riverpod**（Windows 桌面已验证）。
  - **数据层：drift**（schema 与 FluTool 兼容，见"与 FluTool 的关系"）。
- **待定事项**：版本号起点、数据导入路径（是否支持从 FluTool 迁移数据）、跨端范围（Windows 优先，是否扩展 Android/macOS）、forui 0.x 升级节奏评估（试用期后定稿选型）。
