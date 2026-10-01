"""农作物病虫害数据集自动构建。

国赛创新点：无需人工采集上万样本，通过程序合成 + 病害纹理生成 + 增强管线，
自动构建覆盖水稻/小麦/果蔬 20+ 类灾害的小样本训练集。
真实场景中可混入少量真实样本，本脚本保证零样本即可跑通训练流程。
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import cv2
import numpy as np

from algorithm.data_builder.augment import FieldAugmentor


# 类别 -> (作物, 大类, 病斑颜色范围, 病斑形态)
CLASS_SPEC = {
    "rice_blast": ("水稻", "fungal_disease", (40, 30, 90), "spot"),
    "rice_bacterial_blight": ("水稻", "fungal_disease", (200, 200, 150), "streak"),
    "rice_sheath_blight": ("水稻", "fungal_disease", (180, 160, 120), "cloud"),
    "rice_brown_planthopper": ("水稻", "pest", (120, 90, 60), "small_spot"),
    "wheat_rust": ("小麦", "fungal_disease", (0, 80, 200), "stripe"),
    "wheat_powdery_mildew": ("小麦", "fungal_disease", (220, 220, 220), "powdery"),
    "wheat_aphid": ("小麦", "pest", (80, 120, 60), "small_spot"),
    "wheat_scab": ("小麦", "fungal_disease", (200, 180, 100), "spot"),
    "corn_leaf_blight": ("玉米", "fungal_disease", (60, 120, 40), "streak"),
    "corn_borer": ("玉米", "pest", (100, 80, 50), "hole"),
    "cucumber_powdery_mildew": ("黄瓜", "fungal_disease", (230, 230, 230), "powdery"),
    "cucumber_downy_mildew": ("黄瓜", "fungal_disease", (150, 180, 80), "angular"),
    "tomato_early_blight": ("番茄", "fungal_disease", (40, 100, 60), "concentric"),
    "tomato_late_blight": ("番茄", "fungal_disease", (60, 130, 40), "cloud"),
    "tomato_leaf_miner": ("番茄", "pest", (240, 240, 200), "mine"),
    "apple_scab": ("苹果", "fungal_disease", (30, 30, 30), "spot"),
    "apple_aphid": ("苹果", "pest", (90, 130, 70), "small_spot"),
    "citrus_canker": ("柑橘", "fungal_disease", (100, 150, 30), "ring"),
    "citrus_red_mite": ("柑橘", "pest", (180, 60, 40), "small_spot"),
    "general_nitrogen_deficiency": ("通用", "deficiency", (180, 200, 80), "yellowing"),
    "general_potassium_deficiency": ("通用", "deficiency", (180, 150, 60), "edge_burn"),
    "general_phosphorus_deficiency": ("通用", "deficiency", (120, 60, 120), "purpling"),
    "general_pesticide_injury": ("通用", "phytotoxicity", (200, 200, 180), "mottle"),
}


def generate_leaf_background(size: int = 640, crop: str = "水稻") -> np.ndarray:
    """生成叶片背景（绿色渐变 + 叶脉）。"""
    # 基础绿色
    base = np.full((size, size, 3), (40, 120 + random.randint(-20, 20), 30), dtype=np.uint8)
    # 渐变（模拟光照）
    grad = np.linspace(0.7, 1.2, size).reshape(-1, 1, 1)
    base = np.clip(base * grad, 0, 255).astype(np.uint8)
    # 叶脉
    for _ in range(5):
        y = random.randint(0, size)
        cv2.line(base, (0, y), (size, y + random.randint(-30, 30)), (30, 90, 20), 1)
    # 纹理噪声
    noise = np.random.normal(0, 8, base.shape)
    base = np.clip(base + noise, 0, 255).astype(np.uint8)
    return base


def draw_lesion(img: np.ndarray, color: tuple, shape: str) -> list[tuple[int, int, int, int]]:
    """在叶片上绘制病斑/虫害痕迹，返回边界框 [x1,y1,x2,y2]。"""
    h, w = img.shape[:2]
    boxes = []
    n = random.randint(3, 12)
    for _ in range(n):
        cx = random.randint(40, w - 40)
        cy = random.randint(40, h - 40)
        r = random.randint(10, 50)
        x1, y1, x2, y2 = cx - r, cy - r, cx + r, cy + r
        if shape == "spot":
            cv2.circle(img, (cx, cy), r, color, -1)
            cv2.circle(img, (cx, cy), r, (color[0]//2, color[1]//2, color[2]//2), 2)
        elif shape == "streak":
            cv2.ellipse(img, (cx, cy), (r, r // 3), random.randint(0, 180), 0, 360, color, -1)
        elif shape == "cloud":
            for _ in range(3):
                ox = cx + random.randint(-r, r)
                oy = cy + random.randint(-r, r)
                cv2.circle(img, (ox, oy), r // 2, color, -1)
        elif shape == "small_spot":
            cv2.circle(img, (cx, cy), random.randint(3, 8), color, -1)
        elif shape == "stripe":
            cv2.line(img, (cx - r, cy), (cx + r, cy + random.randint(-10, 10)), color, random.randint(3, 8))
        elif shape == "powdery":
            cv2.circle(img, (cx, cy), r, color, -1)
            cv2.circle(img, (cx, cy), r, (255, 255, 255), 1)
        elif shape == "hole":
            cv2.circle(img, (cx, cy), r, (20, 20, 20), -1)
        elif shape == "angular":
            pts = np.array([[cx, cy - r], [cx + r, cy], [cx, cy + r], [cx - r, cy]])
            cv2.fillPoly(img, [pts], color)
        elif shape == "concentric":
            for k in range(3):
                cv2.circle(img, (cx, cy), r - k * 6, color, 2)
        elif shape == "mine":
            pts = [(cx, cy)]
            for _ in range(5):
                cx += random.randint(-15, 15)
                cy += random.randint(5, 15)
                pts.append((cx, cy))
            cv2.polylines(img, [np.array(pts)], False, color, 2)
        elif shape == "ring":
            cv2.circle(img, (cx, cy), r, color, 3)
            cv2.circle(img, (cx, cy), r - 6, (255, 255, 255), 2)
        elif shape == "yellowing":
            cv2.rectangle(img, (x1, y1), (x2, y2), color, -1)
        elif shape == "edge_burn":
            cv2.rectangle(img, (0, 0), (w, 30), color, -1)
            cv2.rectangle(img, (0, h - 30), (w, h), color, -1)
        elif shape == "purpling":
            cv2.rectangle(img, (x1, y1), (x2, y2), color, -1)
        elif shape == "mottle":
            for _ in range(5):
                cv2.circle(img, (random.randint(x1, x2), random.randint(y1, y2)),
                           random.randint(5, 15), color, -1)
        boxes.append((max(0, x1), max(0, y1), min(w, x2), min(h, y2)))
    return boxes


def build_dataset(root: str | Path = "data/dataset",
                  per_class: int = 30, img_size: int = 640,
                  augmented_per: int = 20) -> dict:
    """构建完整数据集，返回统计信息。"""
    root = Path(root)
    images_dir = root / "images"
    labels_dir = root / "labels"
    for d in (images_dir / "train", images_dir / "val", labels_dir / "train", labels_dir / "val"):
        d.mkdir(parents=True, exist_ok=True)

    aug = FieldAugmentor(target_count=augmented_per)
    stats = {"classes": {}, "total": 0}
    for cls_id, (cls_name, (crop, coarse, color, shape)) in enumerate(CLASS_SPEC.items()):
        count = 0
        for i in range(per_class):
            img = generate_leaf_background(img_size, crop)
            boxes = draw_lesion(img, color, shape)
            # 划分 train/val（90/10）
            split = "train" if i < int(per_class * 0.9) else "val"
            name = f"{cls_name}_{i:03d}"
            img_path = images_dir / split / f"{name}.jpg"
            cv2.imwrite(str(img_path), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
            # YOLO 标签
            label_path = labels_dir / split / f"{name}.txt"
            lines = []
            for x1, y1, x2, y2 in boxes:
                xc = ((x1 + x2) / 2) / img_size
                yc = ((y1 + y2) / 2) / img_size
                w = (x2 - x1) / img_size
                h = (y2 - y1) / img_size
                if w > 0.01 and h > 0.01:
                    lines.append(f"{cls_id} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}")
            label_path.write_text("\n".join(lines))
            count += 1
        # 小样本增强（仅训练集）
        train_dir = images_dir / "train"
        train_imgs = list(train_dir.glob(f"{cls_name}_*.jpg"))
        for fp in train_imgs[:5]:  # 每类取5张做增强
            base = cv2.imread(str(fp))
            for j, out in enumerate(aug.augment_one(base)[1:]):
                out_path = train_dir / f"{fp.stem}_aug{j:02d}.jpg"
                cv2.imwrite(str(out_path), out, [cv2.IMWRITE_JPEG_QUALITY, 92])
                # 复制标签
                src_lbl = labels_dir / "train" / f"{fp.stem}.txt"
                dst_lbl = labels_dir / "train" / f"{out_path.stem}.txt"
                if src_lbl.exists():
                    dst_lbl.write_text(src_lbl.read_text())
                count += 1
        stats["classes"][cls_name] = count
        stats["total"] += count

    # 写 data.yaml
    yaml_text = f"""path: {root.resolve()}
train: images/train
val: images/val
nc: {len(CLASS_SPEC)}
names: {[k for k in CLASS_SPEC]}
"""
    (root / "data.yaml").write_text(yaml_text, encoding="utf-8")
    (root / "classes.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


if __name__ == "__main__":
    s = build_dataset()
    print(f"数据集构建完成：共 {s['total']} 张，{len(s['classes'])} 类")
    for k, v in s["classes"].items():
        print(f"  {k}: {v}")