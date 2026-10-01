"""YOLOv8 轻量化推理引擎（开源植物病害模型 + 开源虫害检测模型）。

设计要点：
1. 双模型本地推理（离线、CPU、onnxruntime，无 torch 依赖），适配农村弱网场景：
   - 病害模型：GitHub GithubSpy/Plant_Disease_Detection_YOLOv8n（YOLOv8n，55 类植物叶病害）
   - 虫害模型：HuggingFace Mustafa5645344/insect-detection-yolov8（YOLOv8m，21 类农田昆虫，MIT）
2. 推理链：病害模型 → 虫害模型 → 启发式回退，保证任何图片都有可用结果且优先真实模型。
3. 输出四大类（真菌病害/虫害/缺肥/药害）+ 细分类别 + 置信度 + 检测框。
4. 未映射/中性类别（健康叶、天敌昆虫等）在后处理置零，避免误报。
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from dataclasses import dataclass

import numpy as np
import cv2
from PIL import Image
from loguru import logger

from app.config import settings


# ============================================================
# 开源植物病害检测模型（YOLOv8n，55 类）— 类别名 -> 本项目细分类
# 来源：GitHub GithubSpy/Plant_Disease_Detection_YOLOv8n（Plants Disease 数据集）
# 映射原则：病害类映射到最接近的已有细分类；"healthy"/未覆盖作物类 -> None（视为无检测）
# ============================================================
PLANT_MODEL_NAMES = [
    'Apple black rot', 'Apple cedar rust', 'Apple healthy', 'Apple scab',
    'Bell pepper bacterial_spot', 'Bell pepper healthy', 'Blueberry healthy',
    'Cassava bacterial blight', 'Cassava brown leaf spot', 'Cassava healthy', 'Cassava mosaic', 'Cassava root rot',
    'Cherry healthy', 'Cherry powdery mildew',
    'Citrus haunglongbing',
    'Corn brown spots', 'Corn charcoal', 'Corn chlorotic leaf spot', 'Corn gray leaf spot', 'Corn healthy',
    'Corn insects damages', 'Corn leaf blight', 'Corn mildew', 'Corn purple discoloration', 'Corn rust leaf',
    'Corn smut', 'Corn streak', 'Corn stripe', 'Corn violet decoloration', 'Corn yellow spots', 'Corn yellowing',
    'Grape Esca -Black_Measles-', 'Grape black rot', 'Grape healthy', 'Grape leaf blight',
    'Peach bacterial spot', 'Peach healthy',
    'Potato early blight', 'Potato healthy', 'Potato late blight',
    'Raspberry healthy', 'Soybean healthy',
    'Squash powdery mildew',
    'Strawberry healthy', 'Strawberry leaf scorch',
    'Tomato bacterial wilt', 'Tomato blight leaf', 'Tomato brown spots', 'Tomato healthy', 'Tomato late blight leaf',
    'Tomato leaf mosaic virus', 'Tomato leaf yellow virus', 'Tomato septoria leaf spot', 'Tomato spider mites', 'Tomato target spot',
]
PLANT_CLASS_FINE = {
    'Apple black rot': 'apple_scab', 'Apple cedar rust': 'apple_scab', 'Apple healthy': None, 'Apple scab': 'apple_scab',
    'Bell pepper bacterial_spot': 'tomato_early_blight', 'Bell pepper healthy': None, 'Blueberry healthy': None,
    'Cassava bacterial blight': 'tomato_early_blight', 'Cassava brown leaf spot': 'tomato_early_blight',
    'Cassava healthy': None, 'Cassava mosaic': 'tomato_early_blight', 'Cassava root rot': 'tomato_late_blight',
    'Cherry healthy': None, 'Cherry powdery mildew': 'cucumber_powdery_mildew',
    'Citrus haunglongbing': 'citrus_canker',
    'Corn brown spots': 'corn_leaf_blight', 'Corn charcoal': 'corn_leaf_blight', 'Corn chlorotic leaf spot': 'corn_leaf_blight',
    'Corn gray leaf spot': 'corn_leaf_blight', 'Corn healthy': None, 'Corn insects damages': 'corn_borer',
    'Corn leaf blight': 'corn_leaf_blight', 'Corn mildew': 'corn_leaf_blight', 'Corn purple discoloration': 'general_phosphorus_deficiency',
    'Corn rust leaf': 'corn_leaf_blight', 'Corn smut': 'corn_leaf_blight', 'Corn streak': 'corn_leaf_blight',
    'Corn stripe': 'corn_leaf_blight', 'Corn violet decoloration': 'general_nitrogen_deficiency', 'Corn yellow spots': 'corn_leaf_blight',
    'Corn yellowing': 'general_nitrogen_deficiency',
    'Grape Esca -Black_Measles-': 'tomato_late_blight', 'Grape black rot': 'tomato_late_blight', 'Grape healthy': None, 'Grape leaf blight': 'tomato_late_blight',
    'Peach bacterial spot': 'tomato_early_blight', 'Peach healthy': None,
    'Potato early blight': 'tomato_early_blight', 'Potato healthy': None, 'Potato late blight': 'tomato_late_blight',
    'Raspberry healthy': None, 'Soybean healthy': None,
    'Squash powdery mildew': 'cucumber_powdery_mildew',
    'Strawberry healthy': None, 'Strawberry leaf scorch': 'tomato_late_blight',
    'Tomato bacterial wilt': 'tomato_early_blight', 'Tomato blight leaf': 'tomato_late_blight', 'Tomato brown spots': 'tomato_early_blight',
    'Tomato healthy': None, 'Tomato late blight leaf': 'tomato_late_blight', 'Tomato leaf mosaic virus': 'tomato_early_blight',
    'Tomato leaf yellow virus': 'tomato_early_blight', 'Tomato septoria leaf spot': 'tomato_early_blight', 'Tomato spider mites': 'tomato_leaf_miner',
    'Tomato target spot': 'tomato_early_blight',
}

# ============================================================
# 开源虫害检测模型（YOLOv8m，21 类）— 类别名 -> 本项目细分类
# 来源：HuggingFace Mustafa5645344/insect-detection-yolov8（MIT，农田昆虫检测）
# 映射原则：
#   - 有对应细分类的直接映射（蚜虫/飞虱/螟虫等）；
#   - 无对应但确属害虫的映射到 general_pest（其他农业害虫）；
#   - 天敌/传粉/中性昆虫（瓢虫、蜻蜓、蜜蜂、蜘蛛、螳螂、草蛉、蝴蝶、蚂蚁）-> None，
#     这些是生态益虫，判成"虫害"会误导农户；undefined -> None。
# ============================================================
INSECT_MODEL_NAMES = [
    'ant', 'aphid', 'bees', 'butterfly', 'caterpillar', 'cicada', 'dragonfly',
    'grasshopper', 'green_lacewing', 'ladybug', 'leafhopper', 'mantis',
    'mole_cricket', 'planthopper', 'rhino_beetle', 'rice_bug', 'spider',
    'stem_borer', 'stink_bug', 'undefined', 'weevil',
]
INSECT_CLASS_FINE = {
    'ant': None,               # 中性：常见与蚜虫共生但不直接危害
    'aphid': 'wheat_aphid',    # 蚜虫 -> 麦蚜
    'bees': None,              # 传粉益虫
    'butterfly': None,         # 传粉/中性
    'caterpillar': 'corn_borer',           # 鳞翅目幼虫 -> 螟虫类
    'cicada': 'general_pest',
    'dragonfly': None,         # 捕食性益虫
    'grasshopper': 'general_pest',
    'green_lacewing': None,    # 草蛉：捕食性益虫
    'ladybug': None,           # 瓢虫：捕食性益虫
    'leafhopper': 'rice_brown_planthopper',  # 叶蝉与飞虱近缘
    'mantis': None,            # 捕食性益虫
    'mole_cricket': 'general_pest',
    'planthopper': 'rice_brown_planthopper',  # 飞虱 -> 褐飞虱
    'rhino_beetle': 'general_pest',
    'rice_bug': 'rice_brown_planthopper',     # 稻作害虫归入稻虫细分类
    'spider': None,            # 捕食性益虫
    'stem_borer': 'corn_borer',               # 螟虫类
    'stink_bug': 'general_pest',
    'undefined': None,
    'weevil': 'general_pest',
}


@dataclass
class DetectionResult:
    coarse_category: str
    fine_class: str | None
    confidence: float
    severity: str
    boxes: list[dict]
    mode: str = "model"  # "model"(真实ONNX) | "heuristic"(启发式回退) | "unknown"


class InferenceEngine:
    """单例推理引擎，懒加载模型。"""

    def __init__(self) -> None:
        self._session = None      # 病害模型 onnxruntime session
        self._pest_session = None  # 虫害模型 onnxruntime session
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        model_path = settings.model_path
        if model_path.exists():
            try:
                import onnxruntime as ort
                self._session = ort.InferenceSession(
                    str(model_path),
                    providers=["CPUExecutionProvider"],
                )
                logger.info(f"已加载 ONNX 模型：{model_path.name}")
            except Exception as e:
                logger.warning(f"ONNX 加载失败，将使用启发式回退：{e}")
        else:
            logger.warning(f"模型文件不存在：{model_path}，使用启发式回退识别")
        pest_path = settings.pest_model_path
        if pest_path.exists():
            try:
                import onnxruntime as ort
                self._pest_session = ort.InferenceSession(
                    str(pest_path),
                    providers=["CPUExecutionProvider"],
                )
                logger.info(f"已加载虫害 ONNX 模型：{pest_path.name}")
            except Exception as e:
                logger.warning(f"虫害模型加载失败（不影响病害识别）：{e}")
        else:
            logger.warning(f"虫害模型文件不存在：{pest_path}，虫害识别走启发式")
        self._loaded = True

    def predict(self, image: np.ndarray) -> DetectionResult:
        """对单张图像推理。三段式：病害模型 -> 虫害模型 -> 启发式回退。

        病害模型是"叶部病害"模型，对虫害图片（如蚜虫特写）只会给出不相关的
        低分病害响应，因此专门接一个虫害检测模型；两模型都无可信检出时才
        回退启发式，并以 mode="heuristic" 标记。
        """
        self.load()
        # 域检查门（放在所有模型之前）：图片里得先有农作物/植物特征，
        # 否则任何模型都可能在域外图片上给出高置信度误检
        # （实例：教室监控图被虫害模型以 0.86 误判为玉米螟）。
        if not self._looks_like_plant(image):
            logger.info("图片无农作物特征（未通过域检查），返回未识别")
            return DetectionResult("unknown", None, 0.0, "none", [], mode="unknown")
        if self._session is not None:
            try:
                result = self._predict_disease(image)
                if result.boxes:  # 病害模型有可信检测
                    return result
                logger.info("病害模型未检出可信目标，尝试虫害模型")
            except Exception as e:
                logger.warning(f"病害 ONNX 推理失败，尝试虫害模型：{e}")
        if self._pest_session is not None:
            try:
                result = self._predict_pest(image)
                if result.boxes:  # 虫害模型有可信检测
                    return result
                logger.info("虫害模型未检出可信目标，回退启发式识别")
            except Exception as e:
                logger.warning(f"虫害 ONNX 推理失败，回退启发式识别：{e}")
        try:
            return self._heuristic_predict(image)
        except Exception as e:
            logger.warning(f"启发式识别也失败：{e}")
            return DetectionResult("unknown", None, 0.0, "none", [], mode="unknown")

    @staticmethod
    def _looks_like_plant(image: np.ndarray) -> bool:
        """判断图片是否含农作物/叶片特征（所有模型与启发式之前的域检查门）。

        三个轻量特征（阈值全部用真实图片实测标定）：
        - 植被绿占比：Hue 35~85 且有一定饱和度/亮度（OpenCV 色域）
        - 黄叶占比：Hue 20~35（缺氮黄化/枯黄叶片是本项目的合法识别对象，
          但橙色食物也会贡献该通道，故阈值取 0.6 的高门）
        - 边缘密度：Canny；截图/UI/文字边缘密度明显偏高，用于排除屏幕截图

        标定数据（green/yellow/edge）：
        植物：蚜虫叶(0.080/0.007/0.037)、玉米病叶(0.95/0.001/0.004)、虫卵叶(0.695/0.107/0.067)
        非植物：篮球截图(0.018/0.001/0.062)、食物(0.006/0.278/0.100)、教室监控(0.003/0.046/0.108)
        """
        # ARCH-001：阈值统一从 config 读取，调参不必改推理代码
        if not settings.domain_gate_enabled:
            return True
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        green_ratio = float(np.mean((h >= 35) & (h <= 85) & (s > 40) & (v > 50)))
        yellow_ratio = float(np.mean((h >= 20) & (h < 35) & (s > 60) & (v > 50)))
        edge_density = float(np.mean(cv2.Canny(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), 80, 160) > 0))
        logger.debug(
            f"域检查特征 green={green_ratio:.3f} yellow={yellow_ratio:.3f} edge={edge_density:.3f}"
        )
        return (
            green_ratio >= settings.domain_gate_green_min
            or yellow_ratio >= settings.domain_gate_yellow_min
        ) and edge_density <= settings.domain_gate_edge_max

    # ---------- ONNX 推理 ----------
    def _predict_disease(self, image: np.ndarray) -> DetectionResult:
        img, transform = self._letterbox(image, settings.img_size)
        inp_name = self._session.get_inputs()[0].name
        out = self._session.run(None, {inp_name: img})[0]
        return self._postprocess_yolov8(
            out, image.shape, transform,
            names=PLANT_MODEL_NAMES, class_map=PLANT_CLASS_FINE,
            threshold=settings.conf_threshold, max_boxes=1,
        )

    def _predict_pest(self, image: np.ndarray) -> DetectionResult:
        img, transform = self._letterbox(image, settings.img_size)
        inp_name = self._pest_session.get_inputs()[0].name
        out = self._pest_session.run(None, {inp_name: img})[0]
        return self._postprocess_yolov8(
            out, image.shape, transform,
            names=INSECT_MODEL_NAMES, class_map=INSECT_CLASS_FINE,
            threshold=settings.pest_conf_threshold, max_boxes=5,
        )

    def _letterbox(self, image: np.ndarray, size: int) -> tuple:
        """等比缩放 + 居中灰边填充到 size×size（对齐 ultralytics 默认推理方式）。

        返回 (NCHW 张量, (scale, pad_x, pad_y))，后者用于把检测框还原到原图坐标。
        """
        h, w = image.shape[:2]
        scale = min(size / h, size / w)
        nh, nw = int(round(h * scale)), int(round(w * scale))
        resized = cv2.resize(image, (nw, nh))
        canvas = np.full((size, size, 3), 114, dtype=np.uint8)
        pad_x, pad_y = (size - nw) / 2.0, (size - nh) / 2.0
        canvas[int(pad_y):int(pad_y) + nh, int(pad_x):int(pad_x) + nw] = resized
        canvas = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        tensor = canvas.astype(np.float32) / 255.0
        tensor = tensor.transpose(2, 0, 1)[None, ...]  # NCHW
        return tensor, (scale, pad_x, pad_y)

    def _postprocess_yolov8(self, output: np.ndarray, orig_shape: tuple,
                            transform: tuple = (1.0, 0.0, 0.0),
                            names: list[str] | None = None,
                            class_map: dict | None = None,
                            threshold: float | None = None,
                            max_boxes: int = 1) -> DetectionResult:
        """YOLOv8 输出后处理：output shape (1, 4+NC, 8400)。

        关键：YOLOv8 的输出**没有独立的 objectness 通道**，格式为
        [cx, cy, w, h, cls0, cls1, ...] —— 类别分从第 4 个通道开始。
        早期按「有 objectness」解析（obj=[:,4]、cls=[:,5:]）会漏掉第 0 类、
        并使类别索引整体偏移一位、置信度被错误相乘，导致框全被阈值抹平。

        names/class_map/threshold 由调用方按所用模型传入（病害模型 or 虫害模型）。
        """
        names = names if names is not None else PLANT_MODEL_NAMES
        class_map = class_map if class_map is not None else PLANT_CLASS_FINE
        threshold = settings.conf_threshold if threshold is None else threshold
        output = np.asarray(output).squeeze(0).transpose(1, 0)  # (8400, 4+NC)
        boxes = output[:, :4]        # cx, cy, w, h（相对 size×size 输入）
        class_probs = output[:, 4:]  # 类别分数 (8400, NC)
        ncls = class_probs.shape[1]
        # 仅保留有映射的类别；健康叶/天敌昆虫/未覆盖类别置零，避免误报
        valid = np.array([
            class_map.get(names[c]) is not None
            if c < len(names) else False
            for c in range(ncls)
        ], dtype=bool)
        class_probs = class_probs * valid
        conf = np.max(class_probs, axis=1)  # 无 objectness，类别分即置信度
        mask = conf > threshold
        if not np.any(mask):
            return DetectionResult("unknown", None, 0.0, "none", [])
        # 按置信度取前 max_boxes 个目标；高分候选极少，中心距去重即可
        order = np.argsort(-conf[mask])[:max_boxes * 4]
        picked: list[dict] = []
        best_fine: str | None = None
        best_conf = 0.0
        scale, pad_x, pad_y = transform
        h_img, w_img = orig_shape[:2]
        for idx in order:
            b = boxes[mask][idx]
            c = float(conf[mask][idx])
            cls = int(np.argmax(class_probs[mask][idx]))
            fine = class_map.get(names[cls] if cls < len(names) else "")
            cx, cy, bw, bh = b
            x1 = float(max(0.0, (cx - bw / 2 - pad_x) / scale))
            y1 = float(max(0.0, (cy - bh / 2 - pad_y) / scale))
            x2 = float(min(w_img, (cx + bw / 2 - pad_x) / scale))
            y2 = float(min(h_img, (cy + bh / 2 - pad_y) / scale))
            ccx, ccy = (x1 + x2) / 2, (y1 + y2) / 2
            dup = any(abs(ccx - (p["x1"] + p["x2"]) / 2) < 0.4 * (p["x2"] - p["x1"] + 1)
                      and abs(ccy - (p["y1"] + p["y2"]) / 2) < 0.4 * (p["y2"] - p["y1"] + 1)
                      for p in picked)
            if dup:
                continue
            picked.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "conf": c, "class": fine})
            if c > best_conf:
                best_conf, best_fine = c, fine
            if len(picked) >= max_boxes:
                break
        if not picked:
            return DetectionResult("unknown", None, 0.0, "none", [])
        coarse = self._coarse_of(best_fine)
        return DetectionResult(coarse, best_fine, float(best_conf),
                               self._severity(best_conf), picked)

    # ---------- 启发式回退（无模型时可用，保证可演示）----------
    def _heuristic_predict(self, image: np.ndarray) -> DetectionResult:
        """基于颜色/纹理特征的轻量启发式识别，用于无训练模型时的演示回退。"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        # 缺肥（黄化）：H 偏黄(20-40)、S 低、V 高
        yellow_ratio = np.mean((h > 20) & (h < 40) & (s < 80) & (v > 120))
        # 病斑（褐斑）：V 低、S 中
        brown_ratio = np.mean((v < 90) & (s > 40))
        # 虫害（啃食缺刻/白色）：高亮白点
        white_ratio = np.mean((v > 200) & (s < 40))
        # 虫群/霉斑（蚜虫等深灰色密集集群）
        dark_ratio = np.mean((v < 100) & (s < 70))
        # 药害（斑驳灼伤）：局部高对比
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        local_std = float(np.std(cv2.Laplacian(gray, cv2.CV_64F)))

        scores = {
            "deficiency": float(yellow_ratio * 4.0),
            "fungal_disease": float(brown_ratio * 5.0),
            "pest": float(white_ratio * 3.0 + dark_ratio * 2.5 + local_std / 200),
            "phytotoxicity": float(local_std / 150),
        }
        coarse = max(scores, key=scores.get)
        conf = min(0.80, max(0.45, scores[coarse] + 0.35))  # 启发式上限 0.80，避免"假自信"
        fine = self._default_fine(coarse)
        h_img, w_img = image.shape[:2]
        boxes = [{"x1": 0.1 * w_img, "y1": 0.1 * h_img,
                  "x2": 0.9 * w_img, "y2": 0.9 * h_img,
                  "conf": conf, "class": fine}]
        return DetectionResult(coarse, fine, conf, self._severity(conf), boxes, mode="heuristic")

    # ---------- 辅助 ----------
    @staticmethod
    def _coarse_of(fine: str | None) -> str:
        if not fine:
            return "fungal_disease"
        if fine == "general_pest":
            return "pest"
        if "deficiency" in fine:
            return "deficiency"
        if "phytotoxicity" in fine or "injury" in fine:
            return "phytotoxicity"
        if any(k in fine for k in ("aphid", "planthopper", "borer", "mite", "miner")):
            return "pest"
        return "fungal_disease"

    @staticmethod
    def _default_fine(coarse: str) -> str:
        return {
            "fungal_disease": "rice_blast",
            "pest": "wheat_aphid",
            "deficiency": "general_nitrogen_deficiency",
            "phytotoxicity": "general_pesticide_injury",
        }.get(coarse, "rice_blast")

    @staticmethod
    def _severity(conf: float) -> str:
        if conf >= 0.75:
            return "severe"
        if conf >= 0.55:
            return "moderate"
        return "mild"

    @staticmethod
    def image_hash(image) -> str:
        """内容哈希（全量字节）。

        早期版本只取前 1024 字节做哈希，不同图片（尤其同一来源连拍）容易撞名，
        导致 uploads 目录越堆越多。改为全内容 md5 后，同一张图重复上传会落到同一
        文件名并覆盖，目录不再堆积（配合 CONC-001 入库幂等）。
        """
        data = image.tobytes() if hasattr(image, "tobytes") else bytes(image)
        return hashlib.md5(data).hexdigest()[:16]


inference_engine = InferenceEngine()