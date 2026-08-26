# JotMe 安卓笔记应用设计文档

> 基于 FluTool notes 插件功能移植的独立安卓应用。Kotlin 主语言，MVC 多层架构，与 PC 端 `data/notes` 数据完全互通（一键导入导出）。

---

## 1. PC 端（FluTool notes）功能与 UI 总结

### 1.1 窗口布局

```
┌──────────────────────────────────────────────────────────────┐
│ 标题+计数 | (拉伸) | 搜索框 | 表格切换 | 添加分类 | 快速添加 | 完整添加 | 导出 | 主题 │ ← 工具栏 48px
├────────────┬─────────────────────────────────────────────────┤
│ 全部笔记    │                                                 │
│ 收藏        │              内容区（可切换视图）                  │
│ 归档        │         ┌─────────┐ ┌─────────┐                │
│ ─────────  │         │ 笔记卡片 │ │ 笔记卡片 │  ...           │ ← 卡片视图（懒渲染）
│ 分类 A      │         └─────────┘ └─────────┘                │
│ 分类 B      │                                                 │
│ (可拖拽排序) │                                                 │
└────────────┴─────────────────────────────────────────────────┘
```

- 左侧导航：可折叠，固定项（全部/收藏/归档）+ 动态分类项，分类支持拖拽排序（`sort_order` 持久化）和右键菜单（重命名/删除）
- 内容区：`QStackedWidget` 切换卡片视图 / 表格视图（迷你 Excel）

### 1.2 功能清单

| 模块 | 功能点 |
|:---|:---|
| 增删改查 | 笔记创建/编辑/删除/查询，删除需二次确认 |
| 快速添加 | 标题（可选）+ 内容 + 分类下拉；Enter 保存（标题框）、Ctrl+Enter 保存（内容框） |
| 完整添加 | 标题、内容、分类、标签、代码块、备注、图片 全字段编辑器 |
| 搜索 | 关键词匹配标题/内容/标签/备注（LIKE 查询） |
| 收藏/归档 | 独立标记位（`is_favorite`/`is_archived`），一键切换 |
| 分类管理 | 增删改、拖拽排序（`sort_order` 持久化）、删除分类时笔记 `category_id` 置 NULL |
| 卡片视图 | 懒渲染虚拟滚动（视口缓冲区）、卡片内快捷操作、主题跟随 |
| 表格视图 | 迷你 Excel 风格，多表管理、单元格编辑、导出/复制 |
| 代码高亮 | Python/Java/JavaScript/其他 语言检测 + 语法高亮 |
| 图片 | 粘贴/上传，文件名存 `images` 字段（逗号分隔），文件存 `images/` 目录 |
| 主题 | 亮/暗一键切换，全局样式刷新 |
| 事件总线 | note/category 的 created/updated/deleted 事件驱动 UI 刷新 |
| 导出 | zip 打包 `notes.db` + `images/`（先 WAL checkpoint），与安卓端互通 |

### 1.3 数据结构（兼容契约，不可变更）

**表 categories**

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| id | INTEGER PK AUTOINCREMENT | 主键 |
| name | TEXT NOT NULL UNIQUE | 分类名 |
| sort_order | INTEGER DEFAULT 0 | 排序权重 |
| created_at | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**表 notes**

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| id | INTEGER PK AUTOINCREMENT | 主键 |
| title | TEXT NOT NULL | 标题 |
| content | TEXT NOT NULL | 正文 |
| category_id | INTEGER FK→categories.id ON DELETE SET NULL | 分类 |
| tags | TEXT | 标签，逗号分隔 |
| code_blocks | TEXT | 代码块（JSON/分隔符序列化） |
| remarks | TEXT | 备注，逗号分隔 |
| images | TEXT | 图片文件名，逗号分隔 |
| is_archived | INTEGER DEFAULT 0 | 归档 0/1 |
| is_favorite | INTEGER DEFAULT 0 | 收藏 0/1 |
| created_at | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**文件目录**（zip 导入导出格式，与 PC 端一致）

```
jotme_backup_YYYYMMDD_HHMMSS.zip   （PC 端命名 flunotes_backup_*.zip，格式相同）
├── notes.db                       # SQLite，上述 schema
└── images/                        # 图片文件，文件名与 notes.images 字段对应
    └── *.png
```

---

## 2. JotMe 安卓端设计

### 2.1 技术选型

| 项 | 选型 |
|:---|:---|
| 语言 | Kotlin |
| UI | Jetpack Compose + Material 3 |
| 架构 | MVC 多层（见 2.2） |
| 数据库 | Room（schema 与 PC 端 1:1） |
| 依赖注入 | Hilt |
| 异步 | kotlinx.coroutines + Flow |
| 图片 | Coil |
| 构建 | Gradle (KTS)，minSdk 26，targetSdk 34 |
| 打包互通 | ZIP（`notes.db` + `images/`） |

### 2.2 MVC 分层架构

```
┌─────────────────────────────────────────────┐
│ View 层（ui/）                               │
│  Compose Screen / Component，只渲染状态       │
├─────────────────────────────────────────────┤
│ Controller 层（controller/）                 │
│  ViewModel：持有 UiState，处理用户事件         │
│  Activity：宿主 + 导航宿主                    │
├─────────────────────────────────────────────┤
│ Model 层（data/）                            │
│  Service：业务逻辑（导入导出/图片/格式化）      │
│  Repository：数据仓库门面                     │
│  DAO：Room 数据访问                          │
│  Entity：表映射                              │
└─────────────────────────────────────────────┘
```

### 2.3 目录结构 —— data 代码与 data 数据严格区分

**代码包**（`app/src/main/java/com/jotme/app/`）：

```
com.jotme.app/
├── data/                      # ★ data 代码层（Model）
│   ├── db/                    # Room：AppDatabase / NoteEntity / CategoryEntity / NoteDao / CategoryDao
│   ├── repository/            # NoteRepository / CategoryRepository
│   ├── service/               # BackupService(zip导入导出) / ImageService / FormatterService
│   └── model/                 # UI 用 DTO（NoteWithCategory 等）
├── controller/                # ★ Controller 层
│   ├── NotesViewModel         # 列表/卡片/表格/单文件 共用
│   ├── EditorViewModel        # 编辑器
│   └── CategoryViewModel
├── ui/                        # ★ View 层
│   ├── theme/                 # Material3 亮暗主题
│   ├── navigation/            # NavHost + 路由
│   ├── screens/
│   │   ├── cards/             # 卡片视图
│   │   ├── table/             # 表格视图
│   │   ├── single/            # 单文件（时间流）视图
│   │   ├── editor/            # 完整编辑器
│   │   └── category/          # 分类管理
│   └── components/            # NoteCard / TagChip / ImageViewer 等通用组件
├── di/                        # Hilt 模块（DatabaseModule / RepositoryModule）
└── util/                      # 日期、扩展函数
```

**运行时数据目录**（设备存储，与代码包无关）：

```
/data/data/com.jotme.app/files/jotme/
├── notes.db                   # Room 数据库（自定义路径，非默认 databases/）
└── images/                    # 图片目录
```

> 关键点：Room 通过 `databaseBuilder(...)` 指定自定义路径 `files/jotme/notes.db`，使运行时数据目录结构与 PC 端 `data/notes/` 完全同构，导入导出只需整目录操作，零转换成本。

### 2.4 UI 设计

**单 Activity + Compose Navigation**，主界面 Scaffold：

```
┌──────────────────────────────────────┐
│ TopBar: 标题+计数 | 搜索 | 视图切换 | 主题 │
├──────────────────────────────────────┤
│                                      │
│          内容区（三种视图切换）          │
│                                      │
├──────────────────────────────────────┤
│ NavigationBar: 全部|收藏|归档|分类|设置 │  ← 移动端用底部导航替代 PC 侧边栏
│ FAB: ＋ 快速添加                      │
└──────────────────────────────────────┘
```

**三种布局视图**：

| 视图 | 说明 | 安卓实现 |
|:---|:---|:---|
| 卡片式 | 笔记卡片流，默认视图 | `LazyVerticalGrid`(2列) + NoteCard |
| 表格式 | 迷你 Excel，行=笔记，列=字段 | 自定义 `LazyColumn` + 行内编辑 / 或 `HorizontalPager` 分列 |
| 单文件 | 时间流连续滚动，一屏多篇，突出速记 | `LazyColumn` 全宽卡片 + 顶部输入框直接追加（类 flomo） |

**交互映射**（PC → Android）：

| PC 交互 | 安卓交互 |
|:---|:---|
| 侧边栏导航 | 底部 NavigationBar（全部/收藏/归档）+ 分类页 |
| 右键菜单 | 长按卡片 → DropdownMenu（编辑/删除/收藏/归档） |
| 分类拖拽排序 | 分类管理页 `detectDragGesturesAfterLongPress` + `sort_order` 持久化 |
| Ctrl+Enter 保存 | FAB 快速添加：输入框右侧发送图标 |
| Enter 保存（标题框） | IME action Done |
| 双击卡片编辑 | 点卡片进编辑器页 |
| 主题切换按钮 | 跟随系统 + 设置页手动覆盖 |

### 2.5 数据互通（一键导入导出）

**导出**（`BackupService.export()`）：
1. `db.close()` 关闭 Room（或 `PRAGMA wal_checkpoint(TRUNCATE)`）
2. 压缩 `files/jotme/notes.db` + `files/jotme/images/*` → zip
3. `ActivityResultContracts.CreateDocument` 保存，或 `ShareCompat` 分享

**导入**（`BackupService.import(uri)`）：
1. SAF 选择 zip → 解压校验（必须含 `notes.db`）
2. 关闭 Room 所有连接
3. 覆盖 `files/jotme/notes.db`，合并 `images/`
4. 重建 Room（`databaseBuilder` 重新实例化）
5. Flow 自动刷新 UI

**与 PC 端对接验证**：PC 端"导出"产生的 `flunotes_backup_*.zip` → 安卓导入；安卓导出 zip → 恢复到 PC `data/notes/`（用现有备份恢复流程）。两个方向都要跑通。

---

## 3. 分步开发流程与交接事项

### Phase 0 — 项目初始化
**任务**：新建 Android Studio 项目（Empty Compose Activity）、配置 Gradle KTS / minSdk 26 / Hilt / Room / Coil、建立 2.3 的包骨架。
**交付**：可编译运行的空壳 App + CI 可执行 `./gradlew assembleDebug`。
**交接事项**：确认包名 `com.jotme.app`（一旦上架不可改）、应用图标占位、主题色确定。

### Phase 1 — 数据层（Model）
**任务**：Room Entity（schema 1:1 复刻 1.3 节，字段名类型完全一致）、DAO（get_all/get_favorites/get_archived/get_by_category/search/CRUD）、`AppDatabase` 指定自定义路径、Repository、Hilt 模块。
**交付**：DAO 单元测试全绿（in-memory Room）。
**交接事项**：用 PC 端真实 `notes.db` 文件做只读打开测试，确认无 schema 冲突；`code_blocks` 序列化格式与 PC 端对齐（读取 PC 导出数据验证）。

### Phase 2 — 备份互通（核心契约，最早打通）
**任务**：`BackupService` 导入/导出 zip、SAF 集成、Room 重建逻辑。
**交付**：PC 导出 zip → 安卓导入成功显示数据；安卓导出 → PC 恢复成功。双向手动验证记录。
**交接事项**：导入前必须关库否则报文件占用；记录 PC 端 `flunotes_backup_*.zip` 与安卓 zip 的字段兼容性测试结论（此为两个应用的对接契约基线）。

### Phase 3 — 主列表 UI（卡片视图 + CRUD）
**任务**：Scaffold/底部导航/路由、NotesViewModel（UiState + Flow）、NoteCard 组件、删除二次确认、收藏/归档切换、搜索框。
**交付**：可日常使用的最小可用版本（MVP）。
**交接事项**：搜索行为对齐 PC（标题/内容/标签/备注四字段 LIKE）；空态/加载态设计稿确认。

### Phase 4 — 编辑器
**任务**：快速添加（FAB → BottomSheet）、完整编辑器页（全字段 + 分类下拉）、图片插入（相册选取，文件名规则对齐 PC `标题_时间戳_序号_hash.png`）。
**交付**：编辑器全功能可用，图片可插入显示。
**交接事项**：`updated_at` 必须应用层手动更新（Room 无触发器）；图片文件名冲突策略确认（追加 hash）。

### Phase 5 — 多视图（表格 + 单文件）
**任务**：表格视图（自定义 Composable 表格、行内编辑）、单文件时间流视图（顶部输入直接追加笔记）、三视图切换持久化（DataStore 记住上次视图）。
**交付**：三视图可切换，各自可用。
**交接事项**：表格视图移动端交互范围收敛（确认哪些列可编辑）；单文件视图是否支持富文本（建议纯文本 + 代码块高亮）。

### Phase 6 — 分类管理
**任务**：分类页（增删改列表）、长按拖拽排序（`sort_order` 持久化）、删除分类置 NULL 逻辑、笔记卡片分类过滤。
**交付**：分类全功能。
**交接事项**：拖拽排序与 PC 端 `sort_order` 互通验证（PC 排序 → 安卓导入显示一致）。

### Phase 7 — 体验完善
**任务**：代码高亮（代码块渲染）、图片查看器（Coil + 缩放）、亮暗主题（跟随系统+手动）、空态/错误态、事件驱动刷新（Room Flow invalidation）。
**交付**：功能完整版（RC）。
**交接事项**：亮暗主题下卡片配色对齐 PC 端视觉；性能基线（千条笔记滚动 60fps）。

### Phase 8 — 发布
**任务**：图标/启动屏、混淆规则（Room/Compose keep）、签名打包、真机回归（含 PC 双向导入导出回归）。
**交付**：签名 APK / AAB。
**交接事项**：签名密钥备份；版本号策略（v1.0.0 起，与 PC 端备份格式版本解耦——格式无版本字段，以 schema 为准）。

---

## 4. 风险与注意点

1. **schema 即契约**：两端字段名/类型/外键约束不可单方面变更；任何一端加字段必须走 DEFAULT + 两端同步。
2. **Room 自定义路径**：不用默认 `databases/` 目录，保证 zip 导入导出路径同构。
3. **导入时文件占用**：Android 上关库相对可靠，但仍需处理 `SQLiteDatabaseLockedException`，导入失败要回滚保留原库。
4. **`code_blocks` 序列化**：PC 端是分隔符序列化文本，安卓端需写解码器，Phase 1 用真实数据验证。
5. **时间戳格式**：PC 端 `CURRENT_TIMESTAMP` 是 UTC `YYYY-MM-DD HH:MM:SS`，安卓展示需本地化转换。
