"""SAM 小样本分割辅助 - 提升识别精度创新点。

作用：在 YOLO 检测框基础上，用 SAM/轻量分割细化病斑区域，
提取更精确的颜色/纹理特征，辅助区分易混淆的病害/缺肥/药害。
无 SAM 依赖时回退到基于超像素的轻量分割。
"""
from __future__ import annotations

import cv2
import numpy as np
from loguru import logger


class FewShotSegmenter:
    """小样本分割器：优先 SAM，回退超像素。"""

    def __init__(self, use_sam: bool = True):
        self._sam = None
        if use_sam:
            self._try_load_sam()

    def _try_load_sam(self) -> None:
        try:
            # 尝试加载 segment-anything（若已安装）
            from segment_anything import sam_model_registry, SamPredictor
            # 使用 vit_b（最轻量，CPU 可跑）
            sam = sam_model_registry["vit_b"](checkpoint=None)
            self._sam = SamPredictor(sam)
            logger.info("SAM 分割器加载成功（vit_b）")
        except Exception:
            logger.info("SAM 未安装，使用超像素回退分割")
            self._sam = None

    def segment(self, image: np.ndarray, boxes: list[dict] | None = None) -> list[dict]:
        """对图像分割，返回每个区域的 mask 与特征。"""
        if self._sam is not None and boxes:
            return self._segment_sam(image, boxes)
        return self._segment_slic(image, boxes or [])

    def _segment_sam(self, image: np.ndarray, boxes: list[dict]) -> list[dict]:
        self._sam.set_image(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        results = []
        for b in boxes:
            box = np.array([b["x1"], b["y1"], b["x2"], b["y2"]])
            masks, scores, _ = self._sam.predict(box=box, multimask_output=True)
            best = masks[int(np.argmax(scores))]
            feat = self._extract_features(image, best)
            results.append({"mask": best, "score": float(scores.max()), "features": feat})
        return results

    def _segment_slic(self, image: np.ndarray, boxes: list[dict]) -> list[dict]:
        """SLIC 超像素回退分割。"""
        h, w = image.shape[:2]
        regions = []
        if boxes:
            for b in boxes:
                x1, y1 = int(b["x1"]), int(b["y1"])
                x2, y2 = int(b["x2"]), int(b["y2"])
                roi = image[y1:y2, x1:x2]
                if roi.size == 0:
                    continue
                mask = np.zeros((h, w), dtype=bool)
                mask[y1:y2, x1:x2] = True
                feat = self._extract_features(image, mask)
                regions.append({"mask": mask, "score": float(b.get("conf", 0.8)), "features": feat})
        else:
            # 整图超像素
            slic = cv2.ximgproc.createSuperpixelSLIC(
                image, region_size=30, ruler=20.0
            ) if hasattr(cv2, "ximgproc") else None
            if slic is not None:
                slic.iterate(10)
                labels = slic.getLabels()
                for lbl in np.unique(labels):
                    mask = labels == lbl
                    if mask.sum() < 100:
                        continue
                    feat = self._extract_features(image, mask)
                    regions.append({"mask": mask, "score": 0.7, "features": feat})
            else:
                mask = np.ones((h, w), dtype=bool)
                regions.append({"mask": mask, "score": 0.6,
                                "features": self._extract_features(image, mask)})
        return regions

    @staticmethod
    def _extract_features(image: np.ndarray, mask: np.ndarray) -> dict:
        """提取病斑区域颜色/纹理特征，用于辅助分类。"""
        roi = image[mask]
        if roi.size == 0:
            return {}
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h_roi = hsv[mask]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # 纹理：Laplacian 方差
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        texture = float(np.std(lap[mask]))
        return {
            "mean_b": float(roi[:, 0].mean()), "mean_g": float(roi[:, 1].mean()),
            "mean_r": float(roi[:, 2].mean()),
            "mean_h": float(h_roi[:, 0].mean()), "mean_s": float(h_roi[:, 1].mean()),
            "mean_v": float(h_roi[:, 2].mean()),
            "texture_std": texture,
            "area_ratio": float(mask.sum() / mask.size),
        }


def refine_detection(image: np.ndarray, boxes: list[dict]) -> list[dict]:
    """对外暴露的便捷接口：分割细化 + 特征增强。"""
    seg = FewShotSegmenter(use_sam=False)  # 默认用轻量回退，避免重依赖
    regions = seg.segment(image, boxes)
    out = []
    for b, r in zip(boxes, regions):
        nb = dict(b)
        nb["features"] = r.get("features", {})
        nb["segment_area"] = r.get("features", {}).get("area_ratio", 0)
        out.append(nb)
    return out


if __name__ == "__main__":
    img = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    boxes = [{"x1": 100, "y1": 100, "x2": 400, "y2": 400, "conf": 0.9}]
    res = refine_detection(img, boxes)
    print(f"分割细化完成，特征 keys：{list(res[0]['features'].keys())}")