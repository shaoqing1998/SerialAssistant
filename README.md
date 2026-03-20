# SerialAssistant — 串口调试助手

> 🤖 这是一个纯 AI 项目 — 基于 Python + PySide6 + pyserial 的串口调试工具，
> 支持多 Tab 数据过滤、实时日志记录、自定义波特率，以及 Win11 原生窗口体验。

---

## 版本历史

### v0.45 — 设置弹窗 UI 精细打磨
- 重置按钮改为无边框设计，hover/pressed 仅显示背景色
- 合并「全选」与「全部 Tab」按钮功能，新增 record_all 标记控制自动勾选
- TagChip 列表设计（蓝色竖线指示器替代 QCheckBox，支持 disabled 灰色状态）
- QScrollArea 圆角容器（QPainter 抗锯齿 + BorderOverlay 叠加层边框）
- 地址框 QLabel → QLineEdit（可手动输入路径，长路径光标归位到开头）
- Radio 按钮紧凑样式（10×10px）、Checkbox 紧凑样式（12×12px）
- 浏览按钮无边框设计 + 地址框白色背景
- 关闭按钮居中修复（QPointF 浮点精度）
- 左侧导航栏宽度优化（100 → 80px）
- 未启用日志记录时，Tab 选框和地址框正确置灰

### v0.44 — 圆润标题栏按钮 + 设置弹窗统一 + Snap Layout
- 覆盖 qframelesswindow 库 min/max/close 按钮 paintEvent（Notion 风格圆润图标）
- 设置弹窗关闭按钮与主窗口一致（灰色×号 + hover 圆圈背景）
- 设置弹窗标题栏：左侧齿轮图标 +「设置」文字
- Snap Layout 通过 nativeEvent 覆写实现（WM_NCHITTEST → HTMAXBUTTON）

### v0.43 — SVG 齿轮图标 + 代码清理
- 设置按钮改用 Lucide SVG 齿轮图标（支持 HiDPI）
- 右键菜单字号微调
- 移除冗余间距和废弃代码
- 页面代码重构清理

### v0.42 — Snap Layout + Tab 另存为
- Win11 Snap Layout 贴靠支持（初始实现）
- Tab 右键菜单新增「另存为」功能
- 圆角菜单字号 12px、行高 30px 统一
- 移除 filter_manager.py 中的冗余样式常量

### v0.38 — 无边框窗口迁移
- 迁移至 PySideSix-Frameless-Window（FramelessMainWindow 基类）
- 原生窗口阴影 + 无边框设计
- 设置弹窗全屏遮罩模式（半透明置灰 + 点击外部关闭）
- 标题栏齿轮设置按钮

### v0.37 — 通用设置弹窗
- 设置弹窗框架（左侧导航栏 + 右侧内容页）
- 日志设置页：启用日志、保存目录、文件格式、Tab 选择
- 实时自动保存 + 重置功能
- QPainter 圆角面板 + 边框

### v0.35 — 多 Tab 数据过滤 + 日志管理
- 多 Tab 过滤器管理（关键词匹配、新增/删除/重命名 Tab）
- 日志管理器（LogManager）：串口会话自动记录、按 Tab 分文件
- 右键菜单统一为圆角风格
- Tab 栏折叠/展开发送区按钮

### v0.3 — 右键菜单 + UI 优化
- 自定义圆角弹出菜单（RoundedMenu），解决 Windows 黑边问题
- 统一清空按钮、Tab 右键、日志区、发送区的右键菜单样式
- 改进菜单项布局和视觉表现

### v0.2 — UI 现代化
- 统一的配色方案和控件样式
- 改进的布局和间距
- 更现代的视觉设计（浅色主题、圆角控件）

### v0.1 — 基础串口工具
- 串口连接与断开
- 数据发送与接收
- 日志显示功能

---

## 功能特性

### 串口通信
- ✅ 自动扫描并列出可用串口（800ms 轮询）
- ✅ 支持常用波特率（1200 ~ 921600）+ 自定义波特率
- ✅ 后台线程读取串口数据，不阻塞 UI
- ✅ 支持文本 / HEX 两种收发模式
- ✅ 可选追加 \r\n 换行符
- ✅ 支持 Ctrl+Enter / 回车快速发送
- ✅ 循环发送（可配置间隔）
- ✅ 时间戳显示（可配置超时换行）

### 数据过滤
- ✅ 多 Tab 关键词过滤
- ✅ Tab 新增 / 删除 / 重命名 / 关键词编辑
- ✅ 重新过滤（Refilter）功能
- ✅ Tab 右键菜单（重命名、关键词、另存为）

### 日志记录
- ✅ 实时日志自动保存（按串口会话 + Tab 分文件）
- ✅ 可配置保存目录、文件格式（.log / .txt）
- ✅ 可选择记录哪些 Tab
- ✅ 全选 / 按需勾选，新增 Tab 自动纳入

### 窗口与 UI
- ✅ Win11 原生无边框窗口（阴影 + Snap Layout 贴靠）
- ✅ Notion 风格标题栏按钮（圆润图标 + hover 状态）
- ✅ 设置弹窗（全屏遮罩 + 圆角面板 + 点击外部关闭）
- ✅ 自定义圆角右键菜单
- ✅ 底部状态栏（连接状态、收发计数、速率、计时器）
- ✅ 配置自动保存 / 加载（config.json）

### 规划功能
- 🔲 关键词高亮（自定义颜色）
- 🔲 正则表达式过滤
- 🔲 数据录制与回放

---

## 快速开始

### 1. 安装依赖
    pip install -r requirements.txt

### 2. 运行程序
    python main.py

### 3. 打包为 exe（可选）
    build.bat

---

## 项目结构

SerialAssistant/
├── main.py              # 主入口、主窗口 UI、全局样式
├── title_bar.py         # 标题栏组件（SVG 齿轮按钮 + 自定义 min/max/close）
├── settings_dialog.py   # 通用设置弹窗（全屏遮罩 + 日志设置页）
├── filter_manager.py    # 过滤器管理（多 Tab 过滤 + 关键词匹配）
├── serial_manager.py    # 串口连接管理（pyserial 封装）
├── log_manager.py       # 日志文件管理（自动记录 + 按 Tab 分文件）
├── log_viewer.py        # 日志显示组件
├── rounded_menu.py      # 自定义圆角右键菜单
├── config.py            # 配置文件加载 / 保存
├── config.json          # 默认配置
├── requirements.txt     # 依赖包
├── build.bat            # PyInstaller 打包脚本
└── README.md            # 本文件

---

## 配置文件说明（config.json）

| 字段                      | 说明               | 默认值              |
|---------------------------|--------------------|--------------------|
| serial.port               | 上次使用的串口      | ""                 |
| serial.baudrate           | 波特率             | 115200             |
| serial.custom_baudrates   | 自定义波特率列表    | []                 |
| ui.window_width           | 窗口宽度           | 1100               |
| ui.window_height          | 窗口高度           | 650                |
| send.add_newline          | 发送时追加换行      | true               |
| logging.enabled           | 是否启用实时日志记录 | false              |
| logging.root_dir          | 日志保存目录        | "" (程序目录/logs)  |
| logging.file_format       | 日志文件格式        | .log               |
| logging.record_all_tabs   | 是否记录所有 Tab    | true               |

---

## 依赖环境

- Python >= 3.10
- PySide6 >= 6.5.0
- pyserial >= 3.5
- PySideSix-Frameless-Window >= 0.8.0