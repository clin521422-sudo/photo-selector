# 截图目录

README 里引用的图片都放在这里。

## 命名规则

- **只用 ASCII 小写字母、数字、短横线**：`demo-detection.jpg`、`ui-main.png`
- 不要用空格、中文、大写（GitHub 在 Linux 上区分大小写，`UI.png` 和 `ui.png` 是两个文件）
- 格式：界面截图用 `.png`，效果图用 `.jpg`

## 现有图片

| 文件 | 内容 | 来源 |
|---|---|---|
| `demo-detection.jpg` | YOLOv8n 主体检测效果（狗，置信度 0.91） | `tools/run_demo.py` 生成的标注图 |
| `demo-scene.jpg` | 另一张标注效果图（花卉场景） | 同上 |

## 建议补的图

| 建议文件名 | 内容 | 怎么来 |
|---|---|---|
| `ui-main.png` | 主界面：上传框 + 汇总表 + 统计卡 | 双击 `启动.bat` → 上传 `samples/` 里 6 张图 → 截图 |
| `ui-detail.png` | 逐张详情：检测框 + 直方图 + 四个评分卡 | 展开某张图的"逐张详情"后再截图 |
| `ui-mobile.png` | 手机端访问（可选） | 手机连局域网打开后截图 |

## 截图与压缩

1. 按 `Win + Shift + S` 选区截图，自动进剪贴板
2. 粘到画图 / Snipaste，另存为 `docs/screenshots/xxx.png`
3. 宽度建议 **1200~1600 px**，单张压到 **1 MB 以内**（原图太大的话用画图"调整大小"或在线压缩）

## 在 README 里引用

相对路径（推荐，图片跟着仓库走）：

```markdown
![主界面](docs/screenshots/ui-main.png)
```

控制大小和居中（GitHub 支持这种 HTML 写法）：

```markdown
<p align="center">
  <img src="docs/screenshots/ui-main.png" alt="主界面" width="820">
</p>
```

两张图并排：

```markdown
| 主界面 | 逐张详情 |
|---|---|
| <img src="docs/screenshots/ui-main.png" width="380"> | <img src="docs/screenshots/ui-detail.png" width="380"> |
```
