"""
app.py —— Streamlit 表现层（批量版）

功能：
  1. 批量上传（手机/电脑都行）→ 四个维度评分 → 综合建议
  2. 汇总表：可按任意列排序、按建议筛选、一键导出 CSV
  3. 自动归档：上传的照片按"建议保留/复核/回避"保存到 received/ 下的分类文件夹
  4. 侧边栏显示手机访问地址 + 二维码（局域网内手机直接上传）

运行：
    python -m streamlit run app.py --server.headless true --server.port 8501
"""

from __future__ import annotations

import pathlib
import socket
import sys
from io import BytesIO

import cv2
import numpy as np
import pandas as pd
import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import auth  # noqa: E402
import storage  # noqa: E402
from config import DEFAULT_CONFIG  # noqa: E402
from pipeline import MODULE_TITLES, analyze_image  # noqa: E402

st.set_page_config(page_title="照片选片辅助系统", page_icon="📷", layout="wide")


# ---------------------------------------------------------------- 访问控制
# 局域网直连 → 免密码；内网穿透 / 公网访问 → 必须密码（见 auth.py）
ACCESS = auth.access_info()
auth.login_gate(ACCESS)



# ---------------------------------------------------------------- 工具函数
def get_lan_ip() -> str:
    """拿本机在局域网里的 IP（手机要访问的那个）。"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


@st.cache_data(show_spinner=False)
def qr_png(url: str) -> bytes | None:
    try:
        import qrcode

        img = qrcode.make(url)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


def draw_boxes(image: np.ndarray, boxes: list[dict]) -> np.ndarray:
    vis = image.copy()
    for b in boxes:
        x1, y1, x2, y2 = (int(v) for v in b["xyxy"])
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 200, 0), 2)
        text = f"{b['cls_name']} {b['conf']:.2f}"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
        cv2.rectangle(vis, (x1, max(0, y1 - th - 6)), (x1 + tw + 4, y1), (0, 200, 0), -1)
        cv2.putText(vis, text, (x1 + 2, max(12, y1 - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    return vis


SUGGEST_UI = {
    "建议保留": (st.success, "✅"),
    "建议复核": (st.warning, "⚠️"),
    "建议淘汰": (st.error, "❌"),
}


# ---------------------------------------------------------------- 侧边栏
with st.sidebar:
    st.header("参数设置")
    use_fake = st.toggle("使用假数据（联调 UI 用）", value=False,
                         help="打开后不跑真实算法，只验证界面")
    auto_save = st.toggle("自动归档到电脑", value=True,
                          help="把上传的照片按综合建议保存到 received/ 下的分类文件夹")

    st.subheader("清晰度")
    blur_thr = st.slider("模糊阈值（拉普拉斯方差）", 10.0, 500.0,
                         float(DEFAULT_CONFIG["blur_threshold"]), 10.0)
    st.subheader("曝光")
    over_max = st.slider("过曝像素占比上限", 0.0, 0.5,
                         float(DEFAULT_CONFIG["exposure_over_max"]), 0.01)
    under_max = st.slider("欠曝像素占比上限", 0.0, 0.5,
                          float(DEFAULT_CONFIG["exposure_under_max"]), 0.01)
    st.subheader("主体")
    subj_min = st.slider("主体最小面积占比", 0.0, 0.8,
                         float(DEFAULT_CONFIG["subject_min_area_ratio"]), 0.01)

    config = {
        **DEFAULT_CONFIG,
        "blur_threshold": blur_thr,
        "exposure_over_max": over_max,
        "exposure_under_max": under_max,
        "subject_min_area_ratio": subj_min,
    }

    st.divider()
    st.subheader("📱 手机访问")
    phone_url = f"http://{get_lan_ip()}:8501"
    st.code(phone_url, language=None)
    qr = qr_png(phone_url)
    if qr:
        st.image(qr, width=160)
        st.caption("手机与电脑连同一 WiFi，扫码打开即可上传照片")
    else:
        st.caption("（装 qrcode 包后会显示二维码）")

    st.divider()
    st.subheader("📁 已归档")
    s = storage.stats()
    st.caption(f"保留 {s['建议保留']} ｜ 复核 {s['建议复核']} ｜ 回避 {s['建议淘汰']}")
    st.caption(f"累计 {s['总计']} 张 → received/")

    st.divider()
    st.subheader("🔐 访问方式")
    if ACCESS["needs_password"]:
        st.caption(f"公网访问（已密码保护）· 来源 {ACCESS['ip'] or '未知'}")
        auth.logout_button()
    else:
        st.caption(ACCESS["reason"])


# ---------------------------------------------------------------- 标题
st.title("📷 照片选片辅助系统")
st.caption("批量上传照片，从清晰度、曝光、色彩、主体四个维度量化评分，辅助筛选；"
           "照片会自动按评分归档到电脑上的分类文件夹。")

uploaded_files = st.file_uploader(
    "上传照片（支持多选 / 手机相册）",
    type=["jpg", "jpeg", "png", "bmp", "webp"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("请上传至少一张照片开始分析。手机上打开侧边栏的地址或扫码即可上传。")
    st.stop()


# ---------------------------------------------------------------- 批量分析
rows: list[dict] = []
progress = st.progress(0.0, text="正在分析…")
for i, uploaded in enumerate(uploaded_files, start=1):
    progress.progress(i / len(uploaded_files),
                      text=f"正在分析 {i}/{len(uploaded_files)}：{uploaded.name}")
    data = uploaded.getvalue()
    try:
        result = analyze_image(data, config, fake=use_fake)
    except Exception as e:
        st.error(f"「{uploaded.name}」分析失败：{type(e).__name__}: {e}")
        continue

    mods = result["modules"]
    rows.append({
        "name": uploaded.name,
        "data": data,
        "md5": storage.md5_bytes(data),
        "result": result,
        "suggestion": result["overall"]["suggestion"],
        "pass_ratio": result["overall"]["pass_ratio"],
        "modules": mods,
        "fail_text": {
            name: "；".join(r["details"].get("fail_reason", []))
            for name, r in mods.items()
        },
    })
progress.empty()

if not rows:
    st.stop()

# ---------------------------------------------------------------- 自动归档
saved_info = {"new": 0, "deduped": 0, "failed": 0}
if auto_save and not use_fake:
    for r in rows:
        info = storage.save_photo(r["data"], r["name"], r)
        r["saved_path"] = info.get("path", "")
        if info.get("saved"):
            saved_info["deduped" if info.get("deduped") else "new"] += 1
            if info.get("error"):
                saved_info["failed"] += 1
        else:
            saved_info["failed"] += 1
else:
    for r in rows:
        r["saved_path"] = ""

# ---------------------------------------------------------------- 汇总
total = len(rows)
n_keep = sum(1 for r in rows if r["suggestion"] == "建议保留")
n_review = sum(1 for r in rows if r["suggestion"] == "建议复核")
n_reject = sum(1 for r in rows if r["suggestion"] == "建议淘汰")

st.divider()
c1, c2, c3, c4 = st.columns(4)
c1.metric("共分析", f"{total} 张")
c2.metric("建议保留", f"{n_keep} 张")
c3.metric("建议复核", f"{n_review} 张")
c4.metric("建议淘汰", f"{n_reject} 张")

if auto_save and not use_fake:
    msg = f"已归档：新增 {saved_info['new']} 张，重复跳过 {saved_info['deduped']} 张"
    if saved_info["failed"]:
        msg += f"，失败 {saved_info['failed']} 张"
    st.caption(f"📁 {msg} → `received/建议保留｜建议复核｜建议回避`"
               f"（清单见 `received/manifest.csv`）")

table = pd.DataFrame([
    {
        "文件名": r["name"],
        "综合建议": r["suggestion"],
        "通过率": round(r["pass_ratio"], 2),
        "清晰度": round(r["modules"]["blur"]["score"], 1),
        "清晰度判定": r["modules"]["blur"]["label"],
        "曝光": round(r["modules"]["exposure"]["score"], 1),
        "曝光判定": r["modules"]["exposure"]["label"],
        "色彩": round(r["modules"]["color"]["score"], 1),
        "色彩判定": r["modules"]["color"]["label"],
        "主体": round(r["modules"]["subject"]["score"], 1),
        "主体判定": r["modules"]["subject"]["label"],
        "主体类别": r["modules"]["subject"]["details"].get("top_class", ""),
        "未通过原因": "；".join(v for v in r["fail_text"].values() if v),
        "归档路径": r["saved_path"],
    }
    for r in rows
]).sort_values(by=["通过率", "清晰度"], ascending=False).reset_index(drop=True)
table.index = table.index + 1

st.markdown("#### 批量汇总（点表头可排序）")
picked = st.multiselect(
    "按综合建议筛选", ["建议保留", "建议复核", "建议淘汰"],
    default=["建议保留", "建议复核", "建议淘汰"],
)
view = table[table["综合建议"].isin(picked)] if picked else table
st.dataframe(view, use_container_width=True, height=min(420, 40 + 35 * len(view)))

dl1, dl2 = st.columns(2)
dl1.download_button(
    "⬇️ 导出汇总 CSV",
    data=table.to_csv(index_label="序号").encode("utf-8-sig"),
    file_name="选片汇总.csv",
    mime="text/csv",
    use_container_width=True,
)
with dl2:
    if st.button("📄 查看归档清单 manifest.csv", use_container_width=True):
        if storage.MANIFEST_FILE.exists():
            st.code(storage.MANIFEST_FILE.read_text(encoding="utf-8-sig")[:4000])
        else:
            st.caption("还没有归档记录")

# ---------------------------------------------------------------- 逐张详情
st.divider()
st.markdown("#### 逐张详情")
ordered = sorted(rows, key=lambda x: (-x["pass_ratio"], -x["modules"]["blur"]["score"]))
for idx, r in enumerate(ordered, start=1):
    result, mods = r["result"], r["modules"]
    head = f"{idx}. {r['name']} ｜ {r['suggestion']} ｜ 通过率 {r['pass_ratio'] * 100:.0f}%"
    with st.expander(head, expanded=(idx == 1)):
        col_img, col_info = st.columns([2, 1])
        with col_img:
            boxes = mods["subject"]["details"].get("boxes", [])
            vis = draw_boxes(result["image"], boxes) if boxes else result["image"]
            st.image(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB),
                     caption="绿框为主体检测结果", use_container_width=True)
        with col_info:
            meta = result["meta"]
            ow, oh = meta["origin_size"]
            pw, ph = meta["proc_size"]
            st.metric("原始分辨率", f"{ow} × {oh}")
            st.metric("分析分辨率", f"{pw} × {ph}",
                      delta="已缩放" if meta["resized"] else "未缩放", delta_color="off")
            st.metric("分析耗时", f"{meta['elapsed_ms']:.0f} ms")
            if r["saved_path"]:
                st.caption(f"归档：`received/{r['saved_path']}`")

        cols = st.columns(4)
        for col, (name, m) in zip(cols, mods.items()):
            with col:
                st.metric(MODULE_TITLES.get(name, name), f"{m['score']:.1f}",
                          delta=m["label"],
                          delta_color="normal" if m["passed"] else "inverse")
                if m["passed"]:
                    st.success("通过", icon="✅")
                else:
                    st.error("未通过", icon="❌")
                for reason in m["details"].get("fail_reason", []):
                    st.caption(f"· {reason}")
                for note in m["details"].get("notes", []):
                    st.caption(f"ℹ️ {note}")

        ui_fn, icon = SUGGEST_UI.get(r["suggestion"], (st.info, "ℹ️"))
        ui_fn(f"**综合建议：{r['suggestion']} {icon}**")
        st.progress(r["pass_ratio"], text=f"通过率 {r['pass_ratio'] * 100:.0f}%")

        t1, t2, t3, t4 = st.tabs(["曝光直方图", "主色块", "主体检测", "原始返回值"])
        with t1:
            gray = cv2.cvtColor(result["image"], cv2.COLOR_BGR2GRAY)
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
            st.bar_chart(hist, height=200)
            d = mods["exposure"]["details"]
            a, b, c, e = st.columns(4)
            a.metric("过曝比例", f"{d['over_ratio']:.1%}")
            b.metric("欠曝比例", f"{d['under_ratio']:.1%}")
            c.metric("平均亮度", f"{d['mean_brightness']:.0f}")
            e.metric("动态范围", f"{d['dynamic_range']:.0f}")
        with t2:
            d = mods["color"]["details"]
            hues, weights = d.get("main_hues", []), d.get("main_weights", [])
            if hues:
                sw = st.columns(len(hues))
                for cc, hh, ww in zip(sw, hues, weights):
                    rgb = cv2.cvtColor(np.uint8([[[int(hh), 220, 220]]]), cv2.COLOR_HSV2RGB)[0][0]
                    hexc = "#{:02x}{:02x}{:02x}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))
                    cc.markdown(
                        f'<div style="background:{hexc};height:52px;border-radius:8px;'
                        f'border:1px solid #ddd"></div>', unsafe_allow_html=True)
                    cc.caption(f"H={hh:.0f} · {ww:.0%}")
            st.write(f"饱和度 **{d['sat_mean']:.1f}** ｜ 对比度 **{d['contrast']:.1f}** ｜ "
                     f"色彩丰富度 **{d['richness']:.2f}** ｜ 色相集中度 **{d.get('harmony', 0):.2f}**")
        with t3:
            d = mods["subject"]["details"]
            a, b, c = st.columns(3)
            a.metric("目标数", d.get("num_objects", 0))
            b.metric("最大主体占比", f"{d.get('max_area_ratio', 0):.1%}")
            c.metric("中心偏移", f"{d.get('center_offset', 0):.2f}")
            if d.get("boxes"):
                st.dataframe([{"类别": x["cls_name"], "置信度": x["conf"], "框": f"{x['xyxy']}"}
                              for x in d["boxes"]],
                             use_container_width=True, hide_index=True)
            else:
                st.caption("未检测到目标（YOLO 只认 COCO 80 类）")
        with t4:
            st.json(mods)

st.divider()
st.caption("说明：本系统只提供辅助建议，不做自动删除。归档只是复制保存，不会动你的原图。")
