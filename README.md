# 照片选片辅助系统

> 课程设计项目 · 完整可运行工程
> 技术栈：**Python 3.13 + OpenCV 4.13 + numpy + Streamlit + YOLOv8n ONNX（cv2.dnn 推理）**
> **不需要 PyTorch**：项目运行环境只有 `opencv-python / numpy / streamlit / qrcode` 四个包。

上传照片 → 从**清晰度、曝光、色彩、主体**四个维度量化评分 → 给出综合建议（建议保留 / 建议复核 / 建议淘汰）。
**辅助筛选，不做自动删除**，最终决定权留给用户。

---

## 目录

- [1. 项目简介](#1-项目简介)
- [2. 快速开始](#2-快速开始)
- [3. 完整文件清单](#3-完整文件清单) ← **文件全在这**
- [4. 系统架构](#4-系统架构)
- [5. 四个分析模块](#5-四个分析模块)
- [6. 接口契约（摘要）](#6-接口契约摘要)
- [7. 使用手册](#7-使用手册)
- [8. 测试与验证](#8-测试与验证)
- [9. 团队分工](#9-团队分工)
- [10. 常见问题 FAQ](#10-常见问题-faq)
- [11. 已知限制](#11-已知限制)
- [12. 待办](#12-待办)
- [13. 打包与分发](#13-打包与分发拷给别人就能用)
- [附录 A：文件状态速查](#附录-a文件状态速查)
- [附录 B：环境与版本](#附录-b环境与版本)

---

## 1. 项目简介

### 1.1 它做什么

| 能力 | 说明 |
|---|---|
| **四维量化评分** | 清晰度（拉普拉斯方差）、曝光（直方图+分区加权）、色彩（HSV+色相熵+KMeans）、主体（YOLOv8n） |
| **综合建议** | 四项通过率 1.0 → 建议保留；≥0.5 → 建议复核；<0.5 → 建议淘汰 |
| **批量处理** | 一次上传多张，汇总表可按任意列排序、按建议筛选 |
| **CSV 导出** | 一键导出 `选片汇总.csv`（UTF-8-BOM，Excel 不乱码） |
| **NAS 式归档** | 上传的照片按评分自动分到 `received/建议保留|建议复核|建议回避/`，并写台账 `manifest.csv` |
| **手机上传** | 手机浏览器打开电脑 IP 即可上传（同 WiFi，免密码） |
| **公网访问** | 内网穿透/公网访问**强制密码**，局域网自动免密码 |
| **一键公网演示** | 双击 `公网演示.bat` 自动出公网 HTTPS 地址 + 二维码 |

### 1.2 核心特点

1. **每个分数都有可解释的物理/统计依据**，不是黑箱模型 —— 答辩能逐条讲清楚
2. **模块化 + 统一接口**：四个人可以并行开发，模块之间零依赖，单模块崩了不拖垮整体
3. **阈值可校准**：界面有滑块实时调；`tools/calibrate.py` 用自己样本统计分布定阈值
4. **工程完整度**：测试、网格界面、归档、导出、访问控制、局域网/公网部署都有

### 1.3 当前状态

| 项目 | 状态 |
|---|---|
| 代码 | ✅ 可运行，46 个 Python 文件 / 4460 行 |
| 测试 | ✅ **11 个测试全部通过**（含 GitHub CI） |
| 四模块 | ✅ 全部真实实现（不是占位） |
| 界面 | ✅ Streamlit 批量版 |
| 手机上传 + 归档 | ✅ **已实测：手机上传统计 21 张真实照片并自动分类归档** |
| 公网访问 | ✅ Cloudflare Tunnel 实测连通，密码门禁生效 |
| **打包分发** | ✅ **已生成发布包（11.5 MB），在干净目录实测：解压 → 双击安装 → 9 测试全绿 → 应用可启动** |
| 摄像头 | ⚠️ 与本项目无关（本系统处理照片文件，不接摄像头） |

---

## 2. 快速开始

### 2.1 九个双击入口

| 双击这个 | 作用 | 需要管理员 |
|---|---|---|
| **`1-安装环境.bat`** | **新电脑第一次用**：自动建 venv + 装依赖 + 跑测试（约 2-3 分钟） | 否 |
| **`启动.bat`** | 启动界面，约 8 秒后浏览器自动打开 http://localhost:8501 | 否 |
| **`跑测试.bat`** | 跑全部 11 个测试，全绿才算环境正常 | 否 |
| **`局域网访问开关.bat`** | 开关 Windows 防火墙，让手机能连上你的电脑 | **是**（会自动请求 UAC） |
| **`公网演示.bat`** | 一键出公网 HTTPS 地址 + 二维码（Cloudflare Tunnel），回车即关 | 否 |
| **`数据标注.bat`** | 打开标注工具 X-AnyLabeling（自动选数据集/建配置），给训练集画框 | 否 |
| **`整理数据.bat`** | 标注完成后一键：JSON→YOLO txt + 划验证集 + 体检 | 否 |
| **`训练模型.bat`** | 训练自己的 YOLO 模型并导出 ONNX（用 yolo 环境的 torch） | 否 |

### 2.2 新电脑第一次部署（两种方式）

**方式 A（推荐）：双击 `1-安装环境.bat`** —— 它自动完成下面所有步骤，并在装完时跑一遍测试确认可用。

**方式 B：手动敲命令**

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py --server.headless true
```

> 不想跑 `pip` 慢？加清华源：
> `pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`
>
> ⚠️ 如果 `python -m venv` 报 `ensurepip ... returned non-zero exit status 1`，
> 说明这台机器的 Python 装坏了（缺 ensurepip）。`1-安装环境.bat` 会自动改用 **uv**
> 兜底（没装 uv 就自动下载），所以直接用方式 A 即可。

### 2.3 命令行方式

```bat
:: 启动界面（必须带 --server.headless true，原因见 FAQ）
python -m streamlit run app.py --server.headless true --server.port 8501

:: 不开浏览器，命令行跑一遍样图
python tools\run_demo.py

:: 跑全部测试
python tests\run_all.py
```

---

## 3. 完整文件清单

> 统计口径：33 个 `.py`（2656 行，119 KB）+ 4 个 `.bat` + 2 个配置/密码 + 1 个模型 + 6 张样图。

### 3.1 根目录：入口与文档

| 文件 | 大小 / 行数 | 作用 | 谁维护 |
|---|---|---|---|
| `README.md` | 23 KB | 本文件：总览 + 文件清单 + 使用手册 | 组长 |
| `requirements.txt` | 4 行 | 依赖锁版本：opencv-python 4.13 / numpy 2.5.4 / streamlit 1.66.1 / qrcode 8.2 | 组长 |
| `.gitignore` | — | 忽略 venv / 缓存 / received / output / secret.txt / tools/bin | 组长 |
| `.streamlit/config.toml` | 7 行 | 上传上限 20 MB、headless、关闭统计上报 | 组长 |
| `secret.txt` | 4 行 | **公网访问密码**（已 gitignore，不进仓库） | 自己改 |
| `1-安装环境.bat` | 4.6 KB | **一键装环境**：建 venv（Python → uv 多路兜底）→ 装依赖 → 跑测试 | — |
| `启动.bat` | 1.3 KB | 一键启动界面，自动打开浏览器 | — |
| `跑测试.bat` | 0.5 KB | 一键跑全部测试 | — |
| `局域网访问开关.bat` | 0.6 KB | 一键开关防火墙（自动提权） | — |
| `公网演示.bat` | 1.3 KB | 一键公网演示（自动出地址+二维码） | — |
| `数据标注.bat` | 3.4 KB | 标注工具（自动选数据集 + 修 .anylabelingrc 权限 + 带类别表/输出目录） | — |
| `整理数据.bat` | 1.9 KB | 标注后一键：JSON→txt 转换 + 划 val + 体检 | — |
| `训练模型.bat` | 1.4 KB | 训练自定义 YOLO → 导出 ONNX → 放进 models/ | — |

> 所有 `.bat` 都是 **纯 ASCII + CRLF 换行**（中文会被 cmd 按 GBK 解析截断；纯 LF 会让 goto/括号块解析出错）。
> 这条规则由 `tests/test_bat_files.py` 自动检查，改 bat 后跑一次测试即可确认。

### 3.2 根目录：核心代码（8 个）

| 文件 | 行数 | 职责 |
|---|---|---|
| `app.py` | 308 | **Streamlit 表现层**：批量上传、进度条、汇总表排序筛选、CSV 导出、逐张详情（检测框/直方图/主色块/原始返回值）、侧边栏参数与二维码 |
| `auth.py` | 176 | **访问控制**：判定 LAN/公网、密码门禁、暴力尝试限制、退出登录；含 `PHOTO_FORCE_PASSWORD` 调试开关 |
| `storage.py` | 118 | **自动归档**：MD5 去重、按建议分目录、写 `manifest.csv` 台账、统计各分类数量 |
| `pipeline.py` | 95 | **调度层**：统一缩放 → 依次调 4 模块（try/except 隔离）→ 汇总通过率 → 返回统一结构 |
| `config.py` | 63 | **全部阈值集中处** + 密码读取（环境变量 > secret.txt > 默认值） |
| `utils.py` | 55 | 图像加载（兼容中文路径/bytes）、长边缩放（只缩不放、INTER_AREA） |
| `pipeline_fakes.py` | 30 | 假数据桩函数，用于"先跑通 UI 再填算法"（`analyze_image(..., fake=True)`） |
| `schema.py` | 26 | **接口契约**：`make_result()` 锁死五键返回格式（禁止改） |

### 3.3 `modules/`：四个分析模块

| 文件 | 行数 | 职责 | 核心算法 |
|---|---|---|---|
| `__init__.py` | 1 | 包声明（缺了会 `ModuleNotFoundError`） | — |
| `blur.py` | 31 | 清晰度 | 灰度 → 高斯降噪 → 拉普拉斯 → 方差 |
| `exposure.py` | 83 | 曝光 | 直方图过曝/欠曝比例 + **3×3 中心加权** + 平均亮度 + P99-P1 动态范围 |
| `color.py` | 100 | 色彩 | HSV 饱和度均值 / 灰度标准差 / 色相直方图熵 / **K-Means 主色**（固定种子可复现） |
| `subject.py` | 171 | 主体 | **YOLOv8n ONNX + cv2.dnn**，letterbox → 推理 → NMS → 框映射回原图 → 最大主体占比/中心偏移 |

### 3.4 `tests/`：测试（11 个测试 + 2 个引导）

| 文件 | 行数 | 验证内容 |
|---|---|---|
| `_bootstrap.py` | 7 | 把项目根加进 `sys.path`，提供 `SAMPLES` 路径 |
| `run_all.py` | 36 | 一键跑全部测试并汇总 |
| `test_blur.py` | 33 | 格式断言 + 清晰图分数 > 模糊图分数 + 判定正确 |
| `test_exposure.py` | 38 | 提亮后过曝比例升高、压暗后欠曝比例升高、判定正确 |
| `test_color.py` | 39 | 去色图饱和度更低且不通过 + **K-Means 可复现性** |
| `test_subject.py` | 41 | 狗照片识别为 `dog` 且通过；纯色图不误检 |
| `test_pipeline.py` | 54 | 链路通、**单模块异常不拖垮整体**、假数据模式、统一缩放生效 |
| `test_auth.py` | 90 | 8 项访问控制断言（LAN 免密/公网要密/伪造头绕不过/密码优先级/暴力限制…） |
| `test_public_url.py` | 33 | 隧道 URL 识别回归（防止把 `api.trycloudflare.com` 当隧道地址） |
| `test_doc_consistency.py` | 105 | **文档一致性**：从代码提取配置键/公共函数/details 字段，校验《接口字典》没漏写 |
| `test_bat_files.py` | 78 | **bat 规范**：全部 `.bat` 必须是纯 ASCII + CRLF 换行（防 cmd 解析错乱） |
| `test_evaluate.py` | 111 | **评估脚本**：标注全对→100%、故意标错→准确率下降、阈值扫描、模板生成 |
| `test_dataset_tools.py` | 118 | **训练标注工具链**：建数据集/划分/体检（能查出 class_id 越界、坐标越界、孤儿标注）/类别名 sidecar |

### 3.5 `tools/`：20 个工具脚本

| 文件 | 行数 | 用途 | 什么时候用 |
|---|---|---|---|
| `make_samples.py` | 63 | 从原图生成 6 张测试样图（模糊/过曝/欠曝/去色/主体） | 初始化 `samples/` |
| `calibrate.py` | 60 | 打印所有指标分布，用于**定阈值** | 换数据集后必跑 |
| `run_demo.py` | 81 | 命令行批量演示，存带框标注图到 `output/` | 不开浏览器时 |
| `simulate_upload.py` | 67 | 模拟手机上传，验证分类归档 + 去重 | 测归档逻辑 |
| `verify_ui.py` | 35 | 无头验证界面能渲染（Streamlit AppTest） | 改 UI 后 |
| `verify_ui_upload.py` | 98 | 验证上传后的汇总表 / CSV 构造 | 改批量逻辑后 |
| `verify_login.py` | 65 | 验证密码门禁（未登录/错密码/对密码/LAN 免密） | 改 auth 后 |
| `lan_switch.py` | 207 | 防火墙入站规则开关（自动提权、状态诊断） | 手机连不上时 |
| `public_demo.py` | 259 | 公网演示编排：起服务+隧道+抓 URL+二维码+验证+清理；支持 `--selftest` | 答辩演示前 |
| `get_cloudflared.py` | 67 | 下载 cloudflared（走 gh-proxy 镜像，GitHub 直链国内常超时） | 换电脑/误删时 |
| `init_streamlit.py` | 26 | 预置 Streamlit 凭据（非 headless 模式才需要，可选） | 一般用不上 |
| `make_release.py` | 145 | **打发布包**：生成可拷贝的 zip（排除 venv/照片/大二进制） | 要发给别人时 |
| `evaluate.py` | 387 | **准确率评估**：吃 `data/labels.csv` → 准确率/混淆矩阵/误判清单/阈值扫描 → 输出报告 | **答辩量化评估** |
| `init_dataset.py` | 141 | **建训练数据集**：一条命令生成 classes.txt / data.yaml / 目录，`--split` 自动划分验证集 | 想做自定义模型时 |
| `check_dataset.py` | 180 | **训练数据集体检**：格式/class_id/坐标/孤儿标注/类别框数，训练前必跑 | 训练前 |
| `json2yolo.py` | 190 | **JSON→YOLO txt**：把标注工具的 .json 转成训练用的 .txt（自动归一化、报告未知标签） | 双击 整理数据.bat |
| `pick_dataset.py` | 78 | 多数据集选择器（只有 1 个直接用，多个弹菜单，记住选择） | 各 bat 调用 |
| `datasets_util.py` | 78 | 多数据集工具：列出/当前数据集/路径解析 | 被其它工具 import |
| `finalize_dataset.py` | 95 | 整理数据：json 转换 + 划 val + 体检 一条龙 | 双击 整理数据.bat |
| `train_custom.py` | 175 | **训练+导出**：跑 ultralytics 训练 → 导出 ONNX → 复制进 models/ + 写 `.names.txt`（用 yolo 环境运行） | 双击 `训练模型.bat` |

### 3.6 `docs/`：给团队的文档

| 文件 | 行数 | 内容 |
|---|---|---|
| **`代码地图.md`** | 300 | **"我想改 X 去哪个文件哪一行"**：功能→文件→行号索引、逐文件锚点、加模块 5 步、调试地图 |
| `数据标注指南.md` | 254 | 评估标注 vs 训练标注两条路线、标注表字段、工作量、半自动预标注、训练换模型流程 |
| `数据标注教程.md` | 250 | **0 基础教程**：3 个词、6 步流程、画框操作/快捷键、5 条规矩、多个数据集、检查清单、FAQ |
| `数据标注指南.md` | 424 | 进阶版：评估标注 vs 训练标注两条路线、工作量、质检、半自动、训练换模型 |
| `GitHub发布清单.md` | 240 | **传到 GitHub 前必看**：会传/不传哪些文件、隐私脱敏记录、上传命令、常见坑 |
| `接口字典.md` | 571 | 全工程接口参考：函数签名、返回字段、配置键、枚举值、环境变量、CLI 参数 |
| `接口设计规范.md` | 154 | **直接发给组员和他们的 AI**：函数签名、返回格式、必填 details 键、依赖白名单、禁止清单、测试模板、常见错误对照表、压缩版 prompt |

### 3.7 资源与数据

| 路径 | 大小 | 说明 | 进 git？ |
|---|---|---|---|
| `models/yolov8n.onnx` | 12.2 MB | YOLOv8n 导出模型，组员**不用装 torch** 直接用 | ✅ 是 |
| `samples/` | 0.9 MB / 6 张 | 测试样图：normal / blurred / over / under / gray / subject_dog | ✅ 是 |
| `sources/` | 空（可选） | 原图素材；为空时 `make_samples.py` 回退到 `../yolo/images` | ✅ 是 |
| `tools/bin/cloudflared.exe` | 52.8 MB | 穿透工具（要重新下就 `python tools\get_cloudflared.py`） | ❌ 否 |

### 3.8 运行时生成目录（不进 git）

| 路径 | 当前 | 说明 |
|---|---|---|
| `received/` | **21 张真实照片 / 11.4 MB** | 归档结果：`建议保留/`(4) `建议复核/`(16) `建议回避/`(1) + `manifest.csv` + `.index.json` |
| `output/` | 8 个文件 | 标注图 `anno_*.jpg`、局域网二维码 `lan_qr.png`、公网二维码 `public_demo_qr.png` |
| `.venv/` | 400 MB | 虚拟环境（每台机器自己建） |
| `.tmp/` | 临时 | 跑演示时的日志 |
| `dist/` | 11.5 MB | **发布包输出目录**（`python tools\make_release.py` 生成，不进 git） |

### 3.9 文件统计

```
Python 文件   46 个 / 4460 行
批处理文件     8 个（全部纯 ASCII + CRLF）
文档           7 个（README + 代码地图 + 数据标注教程 + 数据标注指南
                   + 接口字典 + 接口设计规范 + GitHub发布清单）
测试          11 个（全部通过）
分析模块       4 个（全部真实实现）
工具脚本      20 个
GitHub 仓库   74 个文件 / 13.4 MB（含 12 MB 模型，不含 venv 和照片）
发布包        11.6 MB（含模型，不含 venv 和照片）
```

---

## 4. 系统架构

### 4.1 分层

```
┌────────────────────────────────────────────────────────────┐
│ 表现层   app.py（Streamlit）                                │
│   批量上传 / 汇总表排序筛选 / CSV 导出 / 逐张详情 / 二维码    │
├────────────────────────────────────────────────────────────┤
│ 接入层   auth.py  +  .streamlit/config.toml                │
│   LAN 免密码 / 公网要密码 / 上传上限 20MB / 暴力尝试限制      │
├────────────────────────────────────────────────────────────┤
│ 调度层   pipeline.py                                       │
│   统一缩放 → 依次调 4 模块（try/except 隔离）→ 汇总建议       │
├────────────────────────────────────────────────────────────┤
│ 分析层   modules/（互相零 import）                          │
│   blur.py  exposure.py  color.py  subject.py               │
│   统一接口：analyze(image, config) -> dict（固定五键）       │
├────────────────────────────────────────────────────────────┤
│ 基础层   schema.py（契约） config.py（阈值） utils.py（IO）   │
│ 存储层   storage.py（分类归档 + MD5 去重 + 台账）            │
└────────────────────────────────────────────────────────────┘
```

**依赖方向是单向的**：`app → pipeline → modules → schema/config/utils`。
`modules/` 之间**零 import**，所以谁改自己的模块都不会影响别人。

### 4.2 一次分析的完整数据流

```
用户上传照片（手机或电脑）
   │
   ├─→ auth.py 判定来源：LAN 免密 / 公网要密码
   │
   ├─→ utils.load_and_resize()：长边缩到 ≤1024（只缩不放、INTER_AREA、保留宽高比）
   │
   ├─→ pipeline 依次调用四个模块（同一张缩放后的图，保证分数可比）
   │     blur      → 拉普拉斯方差
   │     exposure  → 过曝/欠曝/亮度/动态范围
   │     color     → 饱和度/对比度/色相熵/主色
   │     subject   → letterbox 640 → YOLO → NMS → 框映射回原图
   │
   ├─→ 汇总：通过率 → 建议保留 / 建议复核 / 建议淘汰
   │
   ├─→ storage.save_photo()：MD5 去重 → 按建议存进 received/<分类>/ → 追加 manifest.csv
   │
   └─→ 界面渲染：汇总表 + 逐张详情 + 可导出 CSV
```

**统一缩放为什么重要**：拉普拉斯方差强依赖分辨率，4000×3000 和 800×600 的分数没有可比性。
统一到长边 1024 后，不同比例照片的像素密度接近，分数才能横向比较。

### 4.3 异常隔离

pipeline 里每个模块都包在 `try/except`：某个模块抛异常 → 该模块返回
`make_result(name, 0.0, "分析失败", False, {"error": ...})`，**其他三个照常出结果**。
`tests/test_pipeline.py` 专门验证了这一点（故意让 color 抛异常）。

---

## 5. 四个分析模块

### 5.1 原理一句话版

| 模块 | 核心指标 | 原理 | 异常标签 |
|---|---|---|---|
| **清晰度** | 拉普拉斯方差 | 清晰图边缘锐利、灰度突变强 → 方差大；模糊图边缘弥散 → 方差小 | 清晰 / 疑似模糊 |
| **曝光** | 过曝比例、欠曝比例、平均亮度、动态范围 | 直方图两端像素占比过高即溢出；3×3 中心加权避免"天空过曝但人脸正常"被误判 | 曝光正常 / 过曝 / 欠曝 |
| **色彩** | 饱和度、对比度、色相熵、主色 | HSV 饱和度反映鲜艳度，灰度标准差反映层次，色相熵反映色彩丰富度 | 色彩正常 / 色彩平淡 / 色彩杂乱 |
| **主体** | 最大主体面积占比、中心偏移 | YOLOv8n 检测 COCO 目标，最大框面积占比衡量主体是否突出 | 主体突出 / 主体偏小 / 未检测到主体 |

**综合建议规则**：`通过率 = 通过项数 / 4`
→ `1.0` 建议保留 ｜ `≥0.5` 建议复核 ｜ `<0.5` 建议淘汰

### 5.2 实测结果（`samples/` 六张样图）

| 图片 | 清晰度 | 曝光 | 色彩 | 主体 | 综合建议 |
|---|---|---|---|---|---|
| `normal.jpg`（花，基准） | 124 ✓ | 99 ✓ | 100 ✓ | 53 ✓ | **建议保留** |
| `blurred.jpg`（高斯模糊） | 3 ✗ | 100 ✓ | 100 ✓ | 51 ✓ | 建议复核 |
| `gray.jpg`（去色） | 124 ✓ | 99 ✓ | 35 ✗ | 54 ✓ | 建议复核 |
| `over.jpg`（过曝） | 88 ✓ | 43 ✗ | 88 ✗ | 52 ✓ | 建议复核 |
| `under.jpg`（欠曝） | 7 ✗ | 85 ✗ | 82 ✗ | 52 ✓ | 建议淘汰 |
| `subject_dog.jpg`（暗调人像式） | 51 ✓ | 80 ✗ | 100 ✓ | 51 ✓ | 建议复核 |

单张全链路 **100~250 ms**（CPU；YOLOv8n 640 约 50 ms）。主体检测正确识别 `dog`，占比 50.8%。

### 5.3 阈值是校准过的，不是抄的

网上都说拉普拉斯方差阈值取 **100**，但本项目那张暗调人像式照片只有 **51** —— 用 100 会把**清晰的**照片误判成模糊。
实测 6 张样图分布后（清晰 51~124，模糊 2.8），本项目定的是 **40**。

**这是答辩可以讲的点**：阈值必须用自己的样本集统计分布来定，不能套网上经验值。
换数据集后用 `python tools\calibrate.py` 重新校准，界面也提供滑块可现场调。

---

## 6. 接口契约（摘要）

所有分析模块对外只有**一个函数**，返回**固定五键字典**：

```python
def analyze(image: np.ndarray, config: dict) -> dict:
    return make_result("blur", 124.1, "清晰", True, {"laplacian_var": 124.1})
    #                  module  score  label  passed  details
```

| 规则 | 说明 |
|---|---|
| `image` | BGR 三通道，**已由 pipeline 缩放到长边 ≤1024**，模块内禁止再整体 resize（模型要固定尺寸就在内部 letterbox） |
| `config` | 阈值一律 `config.get("xxx", 默认值)`，**禁止硬编码数字** |
| import 白名单 | 只允许 `cv2`、`numpy`、`schema`、`utils`、`config` |
| 禁止 | import 其他模块 / 写 UI / 改 `schema.py` `config.py` `pipeline.py` |
| 容错 | 抛异常不会拖垮系统，但会被记为"分析失败" |

完整规范（含给组员 AI 的压缩 prompt、测试模板、错误对照表）见
**[docs/接口设计规范.md](docs/接口设计规范.md)** —— 直接把那个文件发给组员即可。

要查某个字段/配置键/枚举值的准确定义，看 **[docs/接口字典.md](docs/接口字典.md)**。

---

## 7. 使用手册

### 7.1 局域网手机上传

1. 电脑双击 `启动.bat`（黑窗口保持开着）
2. 看侧边栏「📱 手机访问」：有地址 `http://<电脑IP>:8501` 和**二维码**
3. 手机连**同一 WiFi**，扫码打开
4. 选照片上传（可多选）→ 电脑上立刻出评分

> **手机连不上？** 99% 是防火墙 → 双击 `局域网访问开关.bat`，选 `[1]` 开启（会自动提权）。
> 还不行就是校园网「AP 隔离」→ 换热点（手机开热点给电脑连）。

### 7.2 NAS 式自动归档

上传的照片会自动**复制**（不动原图）到：

```
received/
  建议保留/      ← 四维全通过
  建议复核/      ← 有 1~2 项没通过
  建议回避/      ← 多项不合格（界面里叫"建议淘汰"）
  manifest.csv   ← 台账：时间/文件名/分类/四维分数与判定/主体类别/未通过原因/路径/MD5
  .index.json    ← MD5 去重索引
```

三个设计细节：

1. **MD5 去重** —— Streamlit 每次交互都会重跑脚本，不去重会把同一张图存出多份副本
2. **不覆盖同名文件** —— 同名不同内容时自动加 `哈希前缀_原名`
3. **只复制不移动** —— `received/` 是可删副本

侧边栏可随时关掉「自动归档到电脑」开关。**实测已归档 21 张真实照片。**

### 7.3 批量排序与 CSV 导出

- 汇总表**点表头任意排序**（按通过率/清晰度/曝光…）
- 按「建议保留/复核/淘汰」**多选筛选**
- 点「⬇️ 导出汇总 CSV」得到 `选片汇总.csv`（Excel 双击不乱码）
- 逐张详情：检测框、曝光直方图、主色色块、原始返回值 JSON

### 7.4 公网访问（密码保护）

| 访问方式 | 结果 |
|---|---|
| 同 WiFi 直连私网 IP | **免密码** ✅ |
| 内网穿透 / 公网服务器 | **必须密码** 🔒 |
| 本机 localhost | 免密码 |

判定逻辑（`auth.py`）：**只要出现任何代理转发头**（`x-forwarded-for` / `cf-connecting-ip` / `x-real-ip` / `forwarded`）
→ 一律当公网要密码。**伪造 `x-forwarded-for: 192.168.1.1` 也绕不过**（只会更严格）。

密码优先级：**环境变量 > `secret.txt` > `config.py` 默认值**。默认 `changeme`，**上公网前务必改 `secret.txt`**。

其它保护：上传上限 **20 MB**（`.streamlit/config.toml`）、密码错误 **5 次/5 分钟**锁定、侧边栏可退出登录。

**本机测公网模式（不用真穿透）**：

```bat
set PHOTO_FORCE_PASSWORD=1
python -m streamlit run app.py --server.headless true
```

### 7.5 一键公网演示

双击 **`公网演示.bat`**：

1. 启动本地服务（若未运行）
2. 建立 Cloudflare Quick Tunnel（免费、免注册、自动 HTTPS）
3. 抓出公网地址 + 生成二维码（自动弹图）+ **验证公网真能访问**
4. 按**回车**关闭隧道（服务是它起的也一起关）

两个已踩过的坑（脚本已处理）：

- **必须 `--protocol http2`**：这台网络 QUIC(UDP 7844) 有一个区不通，默认协议直接 530 失败
- **日志里的 `api.trycloudflare.com` 不是隧道地址**：已加过滤 + 健康检查确认
- Cloudflare 偶尔分到坏隧道（公网一直 530）→ 脚本会自动重开一条

无头自检：`python tools\public_demo.py --selftest`

### 7.6 阈值校准

```bat
python tools\calibrate.py              :: 跑 samples/
python tools\calibrate.py data\imgs    :: 跑你自己的图片目录
```

打印每张图的 `blur_var / over / under / mean / sat / contrast / rich / 主体占比` 及分布区间，
据此改 `config.py`。

### 7.7 数据标注与准确率评估（答辩必备）

详细指南见 **[docs/数据标注指南.md](docs/数据标注指南.md)**，这里只给最短路径：

```bat
python tools\evaluate.py --init        :: 生成 data\labels.csv 模板 + data\imgs 目录
:: 把 60~100 张照片放进 data\imgs\，用 Excel 填 labels.csv
python tools\evaluate.py               :: 出准确率 + 混淆矩阵 + 误判清单
python tools\evaluate.py --scan        :: 额外扫描 blur_threshold，找最优阈值
```

`labels.csv` 只需填两列就能跑：**`文件名`** + **`人工建议`**（建议保留/复核/淘汰）。
拿不准的行留空即可（自动跳过）。单模块真值（清晰度/曝光/色彩/主体）可选填。

输出：

- 控制台：总体准确率、3×3 混淆矩阵、每类 Precision/Recall/F1、单模块准确率、误判清单
- 文件：`output/eval_report_YYYYMMDD_HHMM.md` —— **可以直接贴进答辩 PPT**

> **注意**：这是"评估标注"（Excel 打结论标签，100 张约 15 分钟），
> 不是"训练标注"（画边界框，要按天算）。本项目用预训练 YOLOv8n，**不需要画框**。
> 只有想换成自己的模型时才需要训练标注，流程也在那份指南里（含半自动预标注技巧）。

### 7.8 训练自己的模型（当 COCO 认不出你的主体时）

COCO 只有 80 类，你的主体如果是商品/乐器/菜品/特定物件，模型会报"未检测到主体"→ 误判。
这时才需要训练标注。本项目已经把链路做成工具：

```bat
python tools\init_dataset.py --names "person,pet,goods"   :: 建数据集（自动生成 classes.txt/data.yaml）
:: 放照片到 datasets\mydata\images\train\  （每类 150~300 张，先 20 张跑通）
双击 数据标注.bat                                        :: X-AnyLabeling 画框
python tools\init_dataset.py --split 0.2                  :: 划出验证集
python tools\check_dataset.py                             :: 体检（训练前必跑）
双击 训练模型.bat --epochs 30                             :: 训练 → 自动导出 models/mydata.onnx
:: 改 config.py: subject_model_path = "models/mydata.onnx"
双击 跑测试.bat
```

三个关键设计，让你**不用改代码**：

1. 类别名写在 `datasets/mydata/classes.txt`，`data.yaml` 自动生成（不用手写）
2. 训练脚本会写 `models/mydata.names.txt`，`subject.py` 优先读它（见 `load_class_names()`），
   所以换模型只改 `config.py` 一行
3. `check_dataset.py` 能在训练前查出 class_id 越界、坐标越界、孤儿标注、某类零框

完整细节（工作量、标多少、常见坑）见 **[docs/数据标注指南.md](docs/数据标注指南.md)** 第五节。

---

## 8. 测试与验证

### 8.1 一键跑全部测试

```bat
双击 跑测试.bat
:: 或
python tests\run_all.py
```

当前结果：**11 个测试全部通过**

```
✅ blur 模块测试通过
✅ exposure 模块测试通过
✅ color 模块测试通过
✅ subject 模块测试通过
✅ pipeline 集成测试通过
✅ auth 模块测试通过
✅ public_url 测试通过
✅ doc_consistency 测试通过
✅ bat_files 测试通过
✅ evaluate 测试通过
✅ 训练标注工具链测试通过
✅ 全部 11 个测试通过
```

### 8.2 各验证脚本

| 脚本 | 验证什么 |
|---|---|
| `tools/verify_ui.py` | 界面能渲染（标题/上传框/滑块） |
| `tools/verify_ui_upload.py` | 上传后的汇总表 + CSV 构造逻辑 |
| `tools/verify_login.py` | 未登录进不去 / 错密码被拒 / 对密码能进 / 局域网免密 |
| `tools/simulate_upload.py` | 归档分类正确 + 二次上传全部去重 |
| `tools/public_demo.py --selftest` | 公网隧道能建立且真正可达 |

---

## 9. 团队分工

| 谁 | 负责文件 | 交付标准 |
|---|---|---|
| **组长（你）** | `schema / config / utils / pipeline / app / auth / storage` + 集成 | 已在仓库，别人不许改 |
| 2 号 | `modules/exposure.py` + `tests/test_exposure.py` | 跑通测试打印 ✅ |
| 4 号 | `modules/color.py` + `tests/test_color.py` | 跑通测试打印 ✅ |
| 5 号 | `modules/subject.py` + `tests/test_subject.py` | 跑通测试打印 ✅（ONNX 模型已备好，不用装 torch） |
| 3 号 | `data/` 测试照片 + `labels.csv` | 60~100 张 + 人工标注 |
| 6 号 | `docs/设计文档.md` | 按本 README 的架构和原理整理 |
| 7 号 | 演示录屏 + 截图素材 | 3 分钟视频 |

**验收话术（发群里）**：

> 每个人交模块时，请保证 `python tests/test_你的模块.py` 能在你自己电脑上跑通并打印 ✅。
> 跑不通的模块我不收。测试里必须有：格式断言（五键齐全、类型正确）+ 业务逻辑断言
> （如清晰图分数 > 模糊图分数、过曝图 `passed=False`）。

**绝对不许改的三个文件**：`schema.py`、`config.py`、`pipeline.py`（组长的地盘）。

---

## 10. 常见问题 FAQ

**Q1: 双击 `启动.bat` 报 `'tivate' 不是内部或外部命令` / `'equirements.txt'`？**
那个 `.bat` 里写了中文。**cmd.exe 按系统代码页（中文 Windows = GBK/936）逐行解析批处理文件**，
UTF-8 中文的多字节序列会"吃掉"后面的英文字符（`activate` → `tivate`）。
**规则：`.bat` 只写英文和 ASCII**，中文放 Python 脚本和 md 里。本项目所有 bat 已确认纯 ASCII。

**Q2: 启动报 `[WinError 5] 拒绝访问。: 'C:\Users\CHI\.streamlit'` 然后退出？**
Streamlit **非 headless** 模式启动时会往用户目录写 `~/.streamlit/credentials.toml`，这台机器该目录被安全策略禁止创建
（通常是 Windows Defender「受控文件夹访问」或杀软）。
**解法：用 headless 模式**（`启动.bat` 已带 `--server.headless true`）。自己敲命令时也必须带。

**Q3: 首次启动卡在 `Welcome to Streamlit! Email:`？**
非 headless 模式的首次运行提示。本项目走 headless，不会出现；如遇到按回车跳过，
或先跑 `python tools\init_streamlit.py` 预置凭据。

**Q4: 界面是 exe 还是网页？**
浏览器网页（本地服务，不联网）。双击 `启动.bat` 就是"双击即用"效果，不用打包 exe。

**Q5: `models/yolov8n.onnx` 哪来的？**
组长用 ultralytics 导出一次（`yolo export model=yolov8n.pt format=onnx`）。
**组员不需要装 PyTorch**，`cv2.dnn.readNetFromONNX` 直接加载。

**Q6: 为什么用 OpenCV 4.13 而不是 5.x？**
OpenCV 5.0 的 `cv2.dnn` / 摄像头 API 还不稳，4.13 稳定版最省事。`requirements.txt` 已锁版本。

**Q7: YOLO 检不出主体？**
只认 COCO 80 类（人/车/狗/猫/杯子等）。雕塑、花卉、建筑这类类别外物体它会"视而不见" ——
答辩时作为"未来扩展（更大类别模型 / 显著性检测兜底）"讲。

**Q8: 模块之间会互相影响吗？**
不会。模块之间零 import，pipeline 用 try/except 隔离，单模块崩了只显示"分析失败"，
其他三个照常出结果（`tests/test_pipeline.py` 验证）。

**Q9: 想不写算法先把界面跑通？**
侧边栏打开「使用假数据」开关，或 `pipeline.analyze_image(img, fake=True)`。

**Q10: 手机连不上（一直转圈/无法访问）？**
① 双击 `局域网访问开关.bat` 选 `[1]` 开防火墙 ② 确认同一 WiFi ③ 校园网可能 AP 隔离 → 换热点
④ IP 会变，重开 `启动.bat` 看侧边栏最新地址。

**Q11: 公网演示时提示 530？**
Cloudflare 隧道没连上。确认命令带 `--protocol http2`；脚本会自动重试一次，仍失败可稍后再试。

**Q12: `received/` 会不会动我的原图？**
不会。只**复制**归档，原图永远不动。

**Q13: 上传大小有限制吗？**
有，**20 MB/张**（`.streamlit/config.toml` 的 `maxUploadSize`）。

**Q14: 双击 `1-安装环境.bat` 报 `ensurepip ... returned non-zero exit status 1`？**
这台机器的 Python 装坏了（缺 ensurepip，`python -m venv` 必然失败）。**不用管它**：
安装脚本会依次尝试 `py -3.13` → `py -3` → `python` → 最后自动改用 **uv**（没装 uv 会自动下载到
`tools/bin/uv.exe`），uv 能自己准备 Python 3.13 并建 venv。所以正常情况下直接走安装脚本即可。
彻底修的话：`winget install Python.Python.3.13`。

**Q15: 双击 `1-安装环境.bat` 报 `'oto' 不是内部或外部命令` / `'nstall'`？**
那是我早期版本的 bug，已修复（`bat` 里混入了中文文件名 + LF 换行）。
现在 `tests/test_bat_files.py` 会强制检查所有 bat 必须是**纯 ASCII + CRLF 换行**。

---

## 11. 已知限制

1. **YOLO 只认 COCO 80 类** —— 类别外主体（雕塑/花卉/建筑）检测不到，会被判"未检测到主体"
2. **全图模糊度会误伤"背景虚化、主体清晰"的人像** —— 背景虚化是刻意的摄影手法，但全图拉普拉斯方差会被拉低。
   改进方向：用主体检测框内的 ROI 算清晰度（需要打破模块零依赖，属下一版工作）
3. **色彩"和谐度"没进 passed 判定** —— 色相圆形统计会误判互补色（橙+蓝是经典配色但色相分散），
   故意只放 `details` 里作参考
4. **单机单进程** —— 多人同时上传会写同一个 `received/`，适合个人/小团队演示
5. **公网密码是基础保护** —— 无 HTTPS 时密码理论上可被嗅探，没有用户体系

---

## 12. 待办

- [ ] **3 号的真实数据集 + `labels.csv`** → 工具已就绪：`python tools\evaluate.py --init` 生成模板，
      填完跑 `evaluate.py` 出准确率/混淆矩阵，`--scan` 还能反推最优阈值（见 7.7 与 `docs/数据标注指南.md`）
- [ ] **`docs/设计文档.md` + 答辩 PPT**（架构图、原理图、界面截图、分工表）
- [ ] **部署**：Streamlit Community Cloud（需加 `packages.txt` 装 libGL + 密码改读 `st.secrets`），
      或轻量云服务器 + Docker（可持久化 `received/`）
- [ ] 可选加分项：闭眼检测、显著性检测兜底、主体 ROI 算清晰度、多进程批量加速
- [ ] **训练自定义模型**（工具链已就绪，见 7.8）：`init_dataset.py` → `数据标注.bat` → `check_dataset.py`
      → `训练模型.bat` → 改 `subject_model_path`。适合"COCO 认不出你的主体"时做，是很好的加分项

---

## 13. 打包与分发（拷给别人就能用）

### 13.1 生成发布包

```bat
python tools\make_release.py            :: 生成到 dist/photo-selector-YYYYMMDD.zip
python tools\make_release.py --list     :: 只看会打包哪些文件
```

实测产物：**`dist/photo-selector-20261023.zip`，54 个文件，11.5 MB**。

| 打进去 | 不打进去（原因） |
|---|---|
| 全部 `.py` / `.bat` / `.md` / `.toml` | `.venv/`（400 MB，且含本机绝对路径，拷过去必坏） |
| `models/yolov8n.onnx`（12 MB） | `received/`（你的照片）、`output/`、`dist/` |
| `samples/` 6 张样图 | `tools/bin/`（cloudflared 53 MB，需要时用脚本重新下） |
| `secret.txt`（**重新生成**的默认密码模板） | `__pycache__/`、`.tmp/` |

### 13.2 收包的人怎么做（三步）

1. **解压**到任意目录（路径带不带中文都行）
2. **双击 `1-安装环境.bat`** —— 自动建 venv + 装依赖 + 跑测试确认（约 2-3 分钟）
3. **双击 `启动.bat`** —— 浏览器自动打开界面

> 目标机器**需要 Python 3.10+**；如果 Python 坏了/没装，脚本会自动改用 uv
> （会自动下载 uv 到 `tools/bin/`，uv 自己准备 Python 3.13），所以**通常什么都不用管**。

### 13.3 这个流程已经实测过

我在一个**全新的空目录**里解压发布包，然后执行 `1-安装环境.bat`，结果：

```
[1/3] Creating virtual environment ...
       python -m venv failed, trying uv ...      ← 本机 Python 坏了，自动兜底
       .venv ready
[2/3] Installing dependencies ...                 ← 38 个包从清华源装完
[3/3] Verifying environment (running all tests) ...
✅ 全部 9 个测试通过
 SETUP OK
```

然后从包内的 `.venv` 启动应用，`/_stcore/health` 返回 **HTTP 200**，界面可用。

### 13.4 打包相关的目录约定

| 路径 | 说明 |
|---|---|
| `dist/` | 发布包输出目录（已 gitignore） |
| `1-安装环境.bat` | 收包人的第一步 |
| `tools/make_release.py` | 打包脚本（改完代码重新跑一次即可） |

---

## 附录 A：文件状态速查

**会进 git（应该提交）：**

```
README.md  requirements.txt  .gitignore  .streamlit/config.toml
*.py（33 个）
1-安装环境.bat  启动.bat  跑测试.bat  局域网访问开关.bat  公网演示.bat
models/yolov8n.onnx（12 MB）
samples/*.jpg（6 张）
docs/接口设计规范.md  docs/接口字典.md  docs/代码地图.md
LICENSE  .gitattributes  .github/workflows/tests.yml
docs/数据标注教程.md  docs/数据标注指南.md  docs/GitHub发布清单.md
```

**不进 git（已配 .gitignore）：**

```
.venv/             虚拟环境
received/          归档的照片（个人图片）
output/            生成的标注图/二维码
dist/              发布包 zip
tools/bin/         cloudflared.exe（53 MB）/ uv.exe
secret.txt         访问密码
data/              自己的数据集
.tmp/  __pycache__/
```

---

## 附录 B：环境与版本

| 组件 | 版本 | 说明 |
|---|---|---|
| Python | 3.13.13 | 用 uv 装的独立解释器（不污染系统 Python） |
| opencv-python | 4.13.0.92 | 稳定版，避开 5.0 的坑 |
| numpy | 2.5.4 | |
| streamlit | 1.66.1 | |
| qrcode | 8.2 | 生成手机访问二维码 |
| pandas | 3.1.0 | 随 streamlit 安装，用于汇总表 |
| YOLO 模型 | YOLOv8n ONNX（12.2 MB） | 由 ultralytics 导出，运行时**不需要 torch** |
| 开发机 | Windows + RTX 5060 Laptop | GPU 只用来导出 ONNX 一次，运行时纯 CPU |

**运行时不依赖**：PyTorch、CUDA、TensorFlow、任何 GPU。

---

> 本项目的设计原则：**每个分数都可解释、每个模块都可独立测试、系统永远有一条能演示的路径。**
