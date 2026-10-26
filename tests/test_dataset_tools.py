"""
test_dataset_tools.py —— 训练标注工具链测试

覆盖：
  1. init_dataset：建目录 + classes.txt + data.yaml + --split 划分
  2. check_dataset：合法数据集通过；坏数据集（class_id 越界/坐标越界/孤儿标注）能查出来
  3. subject.load_class_names：有 .names.txt 时读自定义类别，否则回退 COCO 80 类
"""

import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _bootstrap import ROOT  # noqa: E402

INIT = ROOT / "tools" / "init_dataset.py"
CHECK = ROOT / "tools" / "check_dataset.py"
WORK = ROOT / ".dstest"


def call(script: pathlib.Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), *args],
                          cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def write_img(path: pathlib.Path) -> None:
    """写一个 1x1 的假图片文件（内容不重要，工具只看扩展名和文件名）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xff\xd8\xff\xd9")


def run():
    import shutil

    ds = WORK / "mydata"
    shutil.rmtree(WORK, ignore_errors=True)
    try:
        # ---------- 1. init_dataset ----------
        r = call(INIT, "--names", "person,pet,goods", "--root", str(ds))
        assert r.returncode == 0, f"init 失败:\n{r.stdout[-600:]}{r.stderr[-600:]}"
        for sub in ("images/train", "images/val", "labels/train", "labels/val"):
            assert (ds / sub).is_dir(), f"缺目录 {sub}"
        classes = [l for l in (ds / "classes.txt").read_text(encoding="utf-8").splitlines() if l]
        assert classes == ["person", "pet", "goods"], f"classes.txt 内容不对: {classes}"
        yaml_text = (ds / "data.yaml").read_text(encoding="utf-8")
        for i, n in enumerate(classes):
            assert f"{i}: {n}" in yaml_text, f"data.yaml 缺 {n}"
        print(f"  [OK] init_dataset：目录 + classes.txt({len(classes)}类) + data.yaml")

        # ---------- 2. 造一个合法数据集 ----------
        for i in range(4):
            write_img(ds / "images" / "train" / f"img{i}.jpg")
            # 每张 2 个框，类别交替
            (ds / "labels" / "train" / f"img{i}.txt").write_text(
                "0 0.500 0.500 0.200 0.300\n1 0.300 0.400 0.100 0.150\n2 0.700 0.600 0.100 0.100\n", encoding="utf-8")
        r = call(INIT, "--split", "0.25", "--root", str(ds))
        assert r.returncode == 0, f"split 失败:\n{r.stdout[-400:]}"
        n_val = len(list((ds / "images" / "val").glob("*.jpg")))
        n_train = len(list((ds / "images" / "train").glob("*.jpg")))
        assert n_val == 1 and n_train == 3, f"划分比例不对: train={n_train} val={n_val}"
        # 标注文件也应跟着移动
        assert (ds / "labels" / "val").exists() and len(list((ds / "labels" / "val").glob("*.txt"))) == n_val
        print(f"  [OK] --split：train {n_train} / val {n_val}，标注一起移动")

        r = call(CHECK, "--root", str(ds))
        assert r.returncode == 0, f"合法数据集应通过检查，实际:\n{r.stdout[-800:]}"
        assert "检查通过" in r.stdout
        print("  [OK] check_dataset：合法数据集通过")

        # ---------- 3. 造坏数据，必须被查出来 ----------
        # 注意：--split 会随机把一张图挪到 val，所以动态取 train 里实际存在的图片名，
        # 不能硬编码 img0/img1（否则可能刚好是被挪走的那张，会被误判成孤儿标注）
        train_imgs = sorted((ds / "images" / "train").glob("*.jpg"))
        assert len(train_imgs) >= 3, f"train 图片不足: {len(train_imgs)}"
        a, b, c = train_imgs[:3]
        good_text = "0 0.500 0.500 0.200 0.300\n1 0.300 0.400 0.100 0.150\n2 0.700 0.600 0.100 0.100\n"
        (ds / "labels" / "train" / f"{a.stem}.txt").write_text(
            "9 0.5 0.5 0.2 0.2\n", encoding="utf-8")          # class_id 越界（只有 0~2）
        (ds / "labels" / "train" / f"{b.stem}.txt").write_text(
            "0 1.5 0.5 0.2 0.2\n", encoding="utf-8")          # 坐标 > 1
        (ds / "labels" / "train" / f"{c.stem}.txt").write_text(
            "0 0.5 0.5\n", encoding="utf-8")                  # 字段数不对
        (ds / "labels" / "train" / "orphan.txt").write_text(
            good_text, encoding="utf-8")                      # 没有对应图片

        r = call(CHECK, "--root", str(ds))
        out = r.stdout + r.stderr
        assert r.returncode == 1, "坏数据集应返回非 0"
        assert "class_id=9" in out or "超出范围" in out, f"应报 class_id 越界:\n{out[-800:]}"
        assert "坐标不在 0~1" in out, f"应报坐标越界:\n{out[-800:]}"
        assert "字段数" in out, f"应报字段数不对:\n{out[-800:]}"
        assert "孤儿标注" in out or "没有对应图片" in out, f"应报孤儿标注:\n{out[-800:]}"
        print("  [OK] check_dataset：class_id 越界 / 坐标越界 / 字段数 / 孤儿标注 全部查出")

        # ---------- 4. 类别名 sidecar 文件 ----------
        from modules.subject import COCO_NAMES, load_class_names

        fake_model = WORK / "models" / "mydata.onnx"
        fake_model.parent.mkdir(parents=True, exist_ok=True)
        fake_model.write_bytes(b"not a real model")          # 只需要路径存在
        assert load_class_names(fake_model) == COCO_NAMES, "没有 .names.txt 时应回退 COCO 80 类"

        (WORK / "models" / "mydata.names.txt").write_text("person\npet\ngoods\n", encoding="utf-8")
        names = load_class_names(fake_model)
        assert names == ["person", "pet", "goods"], f"应读到自定义类别，实际 {names}"
        print("  [OK] load_class_names：有 .names.txt 读自定义类别，否则回退 COCO")

        # ---------- 5. json2yolo：标注工具的 json -> YOLO txt ----------
        import json as _json

        # 造一张有标注的图 + 一个 anylabeling 的 json
        real = ds / "images" / "train" / "jtest.jpg"
        write_img(real)
        (ds / "labels" / "train" / "jtest.txt").unlink(missing_ok=True)
        (ds / "labels" / "train" / "jtest.json").write_text(_json.dumps({
            "imageWidth": 1000,
            "imageHeight": 800,
            "shapes": [
                # person（class 0）：100,100 -> 300,400
                {"label": "person", "shape_type": "rectangle",
                 "points": [[100, 100], [300, 400]]},
                # 不在 classes.txt 里的标签，应被跳过并报告
                {"label": "unknown_label", "shape_type": "rectangle",
                 "points": [[10, 10], [50, 50]]},
            ],
        }, ensure_ascii=False), encoding="utf-8")

        r = call(ROOT / "tools" / "json2yolo.py", "--root", str(ds))
        out = r.stdout + r.stderr
        assert r.returncode == 0, f"json2yolo 失败:\n{out[-800:]}"
        txt = ds / "labels" / "train" / "jtest.txt"
        assert txt.exists(), "应生成 jtest.txt"
        lines = [l for l in txt.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 1, f"应只转换 1 个框（unknown_label 被跳过），实际 {lines}"
        cid, cx, cy, bw, bh = lines[0].split()
        assert cid == "0", f"person 应是 class 0，实际 {cid}"
        assert abs(float(cx) - 0.2) < 1e-4, f"cx 应为 0.2，实际 {cx}"
        assert abs(float(cy) - 0.3125) < 1e-4, f"cy 应为 0.3125，实际 {cy}"
        assert abs(float(bw) - 0.2) < 1e-4 and abs(float(bh) - 0.375) < 1e-4, "宽高不对"
        assert "unknown_label" in out, f"应提示未知标签:\n{out[-600:]}"
        print("  [OK] json2yolo：JSON→YOLO txt 坐标归一化正确，未知标签被跳过并提示")

        # ---------- 6. 多数据集：路径解析（只读检查，不改动用户的 .current） ----------
        sys.path.insert(0, str(ROOT / "tools"))
        import datasets_util as du

        assert isinstance(du.list_datasets(), list), "list_datasets 应返回列表"
        assert du.resolve_root("mydata").name == "mydata", "resolve_root 解析错误"
        assert du.resolve_root("").name != "", "空参数应回退到当前数据集"
        print("  [OK] datasets_util：多数据集路径解析正常（不改动当前数据集）")

        print("✅ 训练标注工具链测试通过")
    finally:
        shutil.rmtree(WORK, ignore_errors=True)


if __name__ == "__main__":
    run()
