# 上传 GitHub 清单

> 目标：把 `photo-selector` 传到 GitHub，**既能给别人看，又不泄漏私人东西**。
> 本文里的数字都是本机实测的（2026-10）。

---

## 一、一句话结论

**能传**：全部源码、文档、bat、模型（12 MB）、6 张测试样图。
**别传**：`.venv`、你上传的照片（`received/`）、数据集（`datasets/`）、密码（`secret.txt`）、
标注工具缓存（`.toolconfig/`）、54 MB 的 `cloudflared.exe`、导出包（`dist/`）。

实测结果：**72 个文件，共 13.43 MB**，单文件最大是模型 12.2 MB（GitHub 限 100 MB，安全）。

---

## 二、已经帮你准备好的东西

| 文件 | 作用 |
|---|---|
| `.gitignore` | 挡住 venv / 照片 / 数据集 / 密码 / 缓存 / 大二进制 |
| `.gitattributes` | 强制 `.bat` 用 CRLF（否则 clone 到 Linux 后 bat 会失效）；图片/模型标记为二进制 |
| `LICENSE` | MIT 协议模板（**把里面的署名改成你的**） |
| `.github/workflows/tests.yml` | 推上去后 GitHub 自动跑 11 个测试（CI 绿勾，答辩/简历都好看） |

另外做了**隐私脱敏**：

| 原来 | 改成 | 原因 |
|---|---|---|
| 你的真实局域网 IP | `192.168.1.23` | 别暴露内网结构 |
| 你的公网出口 IP 段 | `1.1.1.1` | 别暴露 ISP/地区 |
| 原默认密码（同时也是你 secret.txt 里的真密码） | `changeme` | **公开仓库不能带真密码** |

> ⚠️ 你的真实密码仍保存在 `secret.txt`（已被 gitignore，不会上传）。

---

## 三、会被上传的文件（72 个）

| 目录/文件 | 数量 | 体积 | 说明 |
|---|---|---|---|
| 根目录文件（`*.py`、`*.bat`、README、配置等） | 21 | 96 KB | 8 个核心 py + 8 个 bat + README + requirements 等 |
| `tools/` | 20 | 100 KB | 16 个脚本 + `datasets_util` 等（**不含 `tools/bin/`**） |
| `tests/` | 13 | 38 KB | 11 个测试 + 2 个引导 |
| `modules/` | 5 | 19 KB | 四个分析模块 + `__init__.py` |
| `docs/` | 5 | 74 KB | 代码地图 / 数据标注教程 / 数据标注指南 / 接口字典 / 接口设计规范 |
| `samples/` | 6 | 899 KB | 测试样图（通用壁纸，非私人照片） |
| `models/` | 1 | **12.2 MB** | `yolov8n.onnx`，必须传，否则别人跑不起来主体检测 |
| `.streamlit/` | 1 | 0.5 KB | 上传大小限制等配置 |

---

## 四、不会被上传的（以及为什么）

| 路径 | 体积 | 为什么不能传 |
|---|---|---|
| `.venv/` | ~400 MB | 含本机绝对路径，别人机器上必坏；且体积太大 |
| `received/` | 11 MB | **你上传的私人照片**（21 张真实照片） |
| `datasets/` | 取决于标注量 | 训练数据集（照片 + 标注），属于个人数据 |
| `secret.txt` | — | **访问密码** |
| `.toolconfig/` | 小 | 标注工具的本地配置（含本机绝对路径） |
| `tools/bin/` | 54 MB | cloudflared.exe / uv.exe，需要时脚本自己下载 |
| `dist/` | 11 MB | 打包好的发布 zip |
| `output/` `runs/` `.tmp/` | — | 运行时产物 |
| `data/` | — | 评估标注表（个人数据） |
| `__pycache__/` `*.pyc` | — | 编译缓存 |

> 校验命令（自己可以再查一遍）：
> ```bat
> git add -A
> git ls-files | findstr /i "received datasets venv secret toolconfig bin dist"
> ```
> 应该**没有任何输出**。

---

## 五、上传前你还需要手动做 3 件事

### 1. 改 LICENSE 里的署名

```text
Copyright (c) 2026 <把这里换成你的名字或 GitHub 用户名>
```

不想开源可以换成别的协议；课程设计建议就用 MIT（最宽松，别人引用你也不用问）。

### 2. 设置 GitHub 用的 git 身份

你现在的 git 身份是 **Gitee** 的邮箱：

```
user.name  = CHILIN
user.email = 17526640+chilink01@user.noreply.gitee.com
```

这样提交到 GitHub 上**不会关联到你的 GitHub 头像**。改成 GitHub 的：

```bat
git config --global user.name "你的 GitHub 用户名"
git config --global user.email "你的GitHub邮箱"
:: 或者用 GitHub 提供的隐私邮箱（推荐，不暴露真实邮箱）：
:: 在 GitHub → Settings → Emails 里可以查到 xxxxx+用户名@users.noreply.github.com
```

### 3.（可选）确认 README 首屏够吸引人

GitHub 上别人只看首屏。当前 README 750+ 行、内容很全，但**开头没有截图**。
建议补：

- 一张界面截图（跑 `启动.bat` 后截一张，存成 `docs/screenshots/ui.png`）
- 一张检测效果图（`output/` 里的标注图）
- 在 README 第 1 节插一行：`![界面截图](docs/screenshots/ui.png)`
- 上面加几个 badge（CI 通过、Python 版本、License）

---

## 六、上传步骤（从零到推上去）

### 1. 在 GitHub 建空仓库

网页 → New repository → 名字比如 `photo-selector` →
**不要**勾 "Add a README/license/gitignore"（本地已经有了）→ Create。

### 2. 本地提交

```bat
cd C:\Users\CHI\Desktop\sdt\photo-selector

:: 确认要传的文件（重要！看一眼有没有私人东西）
git status --short

:: 提交
git add -A
git commit -m "feat: 照片智能筛选系统（4 模块 + Streamlit 界面 + 自动归档 + 公网访问）"
```

### 3. 关联远程并推送

```bat
git remote add origin https://github.com/你的用户名/photo-selector.git
git branch -M main
git push -u origin main
```

> 第一次 push 会弹出登录。密码位置要填 **Personal Access Token**（GitHub 已不支持账号密码）：
> GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → 勾 `repo` → 生成。
> 或者配 SSH key（`ssh-keygen` → 把公钥传到 GitHub → 用 `git@github.com:...` 地址）。

### 4. 检查

- 仓库首页文件数 ~72，体积显示 ~13 MB
- Actions 标签里 `tests` 应该跑起来（第一次约 1-2 分钟）
- 点进任一文件，`.bat` 不应该显示成一行（说明换行正常）

---

## 七、上传后建议（加分项）

| 做什么 | 怎么做 |
|---|---|
| **填仓库 About** | 右上角 ⚙️ About：一句简介 + Topics：`python` `opencv` `yolo` `streamlit` `image-processing` `photo-culling` |
| **发 Release** | Releases → Draft new release → 把 `dist/photo-selector-20261023.zip` 传上去。这样不懂代码的人也能直接下 zip 用 |
| **README 顶部加 badge** | `![tests](https://github.com/你/photo-selector/actions/workflows/tests.yml/badge.svg)` |
| **补截图** | 见第五节第 3 条 |
| **Issue 模板**（可选） | 课程项目不必 |

---

## 八、常见坑

**Q：已经把私人照片/密码传上去了怎么办？**
改 `.gitignore` **不管用**，历史记录里还有。要么删仓库重建（最简单），要么用 `git filter-repo` 重写历史：

```bat
pip install git-filter-repo
git filter-repo --path received/ --invert-paths
git filter-repo --path secret.txt --invert-paths
```
> 已经 push 过的话，还要 `git push --force`，并且**假设已泄漏**（改掉那个密码）。

**Q：模型 12 MB 会不会太大？**
不会。GitHub 单文件 < 50 MB 无警告，< 100 MB 直接接受。整个仓库 13 MB，clone 很快。

**Q：`.venv` 传上去别人能用吗？**
不能，而且会被拒（太多文件）。别人用 `1-安装环境.bat` 自己建，这正是我们准备安装脚本的原因。

**Q：中文文件名有没有问题？**
Git 存的是 UTF-8，GitHub 网页正常显示。只是 Windows 控制台里 `git status` 可能显示成 `\346\225...`
（那是 `core.quotepath` 的转义显示，不影响文件本身）。想看中文：

```bat
git config --global core.quotepath false
```

**Q：`.bat` 传上去之后别人 clone 下来会坏吗？**
不会，`.gitattributes` 里已经强制 `.bat` 用 CRLF 检出。`tests/test_bat_files.py` 会守住这条。

**Q：想做成私有仓库？**
建仓库时选 Private 即可，其余步骤一样。私有仓库 Actions 也免费（有额度）。

---

## 九、清单速查

上传前：

- [ ] LICENSE 里署名改成自己
- [ ] git 身份改成 GitHub 的邮箱
- [ ] `git status --short` 里没有 `received/` `datasets/` `secret.txt` `.venv/` `tools/bin/`
- [ ] 11 个测试本地全绿（`双击 跑测试.bat`）

上传后：

- [ ] 仓库首页体积约 13 MB、文件 ~72 个
- [ ] Actions 里 tests 是绿勾
- [ ] About + Topics 填了
- [ ] Release 里挂了 zip 包
