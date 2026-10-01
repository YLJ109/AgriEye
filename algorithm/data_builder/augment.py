"""田间复杂环境数据增强 - 小样本训练核心。

针对野外遮挡、逆光、复杂背景等痛点，组合多种增强策略，
使少量真实样本也能训练出泛化能力强的模型（小样本创新点）。
"""
from __future__ import annotations

import random
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


class FieldAugmentor:
    """模拟田间真实环境的增强管线。"""

    def __init__(self, target_count: int = 50, seed: int = 42):
        self.target_count = target_count  # 每张原图扩增到多少张
        self.rng = random.Random(seed)

    def augment_one(self, image: np.ndarray) -> list[np.ndarray]:
        """对单张图像生成一组增强样本。"""
        results = [image.copy()]
        for _ in range(self.target_count - 1):
            aug = image.copy()
            aug = self._random_geometry(aug)
            aug = self._random_color(aug)
            aug = self._random_noise_blur(aug)
            aug = self._random_occlusion(aug)
            aug = self._random_weather(aug)
            results.append(aug)
        return results

    # ---------- 几何 ----------
    def _random_geometry(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        # 随机旋转 -15~15 度（模拟手持拍照倾斜）
        angle = self.rng.uniform(-15, 15)
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        img = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REFLECT)
        # 随机水平/垂直翻转
        if self.rng.random() > 0.5:
            img = cv2.flip(img, 1)
        if self.rng.random() > 0.5:
            img = cv2.flip(img, 0)
        # 随机裁剪缩放（模拟不同拍摄距离）
        scale = self.rng.uniform(0.7, 1.3)
        nh, nw = int(h * scale), int(w * scale)
        img = cv2.resize(img, (nw, nh))
        # 中心裁回原尺寸
        y0 = max(0, (nh - h) // 2)
        x0 = max(0, (nw - w) // 2)
        img = img[y0:y0 + h, x0:x0 + w]
        if img.shape[0] < h or img.shape[1] < w:
            img = cv2.resize(img, (w, h))
        return img

    # ---------- 色彩（模拟逆光/光照变化）----------
    def _random_color(self, img: np.ndarray) -> np.ndarray:
        pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        # 亮度（模拟逆光、阴天、强光）
        pil = ImageEnhance.Brightness(pil).enhance(self.rng.uniform(0.5, 1.5))
        # 对比度
        pil = ImageEnhance.Contrast(pil).enhance(self.rng.uniform(0.7, 1.4))
        # 饱和度（模拟不同生长期叶色）
        pil = ImageEnhance.Color(pil).enhance(self.rng.uniform(0.6, 1.4))
        # 色调微调（模拟白平衡偏差）
        pil = ImageEnhance.Color(pil).enhance(self.rng.uniform(0.9, 1.1))
        return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

    # ---------- 噪声与模糊（模拟低质量手机拍摄）----------
    def _random_noise_blur(self, img: np.ndarray) -> np.ndarray:
        if self.rng.random() > 0.5:
            sigma = self.rng.uniform(0, 2.5)
            img = cv2.GaussianBlur(img, (0, 0), sigma)
        if self.rng.random() > 0.6:
            noise = np.random.normal(0, self.rng.uniform(2, 15), img.shape)
            img = np.clip(img + noise, 0, 255).astype(np.uint8)
        return img

    # ---------- 遮挡（模拟叶片遮挡、杂草）----------
    def _random_occlusion(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        for _ in range(self.rng.randint(0, 3)):
            x1 = self.rng.randint(0, w - 20)
            y1 = self.rng.randint(0, h - 20)
            x2 = min(w, x1 + self.rng.randint(15, 60))
            y2 = min(h, y1 + self.rng.randint(15, 60))
            color = (self.rng.randint(0, 255),) * 3
            cv2.rectangle(img, (x1, y1), (x2, y2), color, -1)
        return img

    # ---------- 天气（模拟雨雾）----------
    def _random_weather(self, img: np.ndarray) -> np.ndarray:
        if self.rng.random() > 0.7:  # 雾
            fog = np.ones_like(img) * self.rng.randint(180, 230)
            img = cv2.addWeighted(img, 0.7, fog, 0.3, 0)
        if self.rng.random() > 0.8:  # 雨丝
            rain = np.zeros_like(img)
            for _ in range(self.rng.randint(50, 200)):
                x = self.rng.randint(0, img.shape[1])
                y = self.rng.randint(0, img.shape[0] - 10)
                cv2.line(rain, (x, y), (x + 2, y + 10), (200, 200, 200), 1)
            img = cv2.addWeighted(img, 0.85, rain, 0.15, 0)
        return img


def augment_directory(src_dir: str | Path, dst_dir: str | Path,
                      target_count: int = 50, exts=(".jpg", ".jpeg", ".png")) -> int:
    """对目录下所有图片执行增强，输出到 dst_dir。返回生成总数。"""
    src_dir, dst_dir = Path(src_dir), Path(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    aug = FieldAugmentor(target_count=target_count)
    total = 0
    for fp in src_dir.rglob("*"):
        if fp.suffix.lower() not in exts:
            continue
        img = cv2.imdecode(np.fromfile(str(fp), dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        for i, out in enumerate(aug.augment_one(img)):
            out_path = dst_dir / f"{fp.stem}_aug{i:03d}.jpg"
            cv2.imwrite(str(out_path), out, [cv2.IMWRITE_JPEG_QUALITY, 92])
            total += 1
    return total


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else "data/raw"
    dst = sys.argv[2] if len(sys.argv) > 2 else "data/augmented"
    n = augment_directory(src, dst)
    print(f"数据增强完成，共生成 {n} 张样本 -> {dst}")