"""全局配置中心 - 集中管理所有可调参数，便于国赛演示与离线部署。"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---------- 服务 ----------
    app_name: str = "农智 AI 顾问系统"
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False   # 仅调试时回显异常细节（SEC-009），生产保持 False
    # 前端固定 5188（5173 属另一个项目，勿占用）。如需其他端口，用环境变量 CORS_ORIGINS 覆盖。
    cors_origins: list[str] = [
        "http://localhost:5188", "http://127.0.0.1:5188",
        "http://localhost:5173", "http://127.0.0.1:5173",  # 兼容老 dev 端口
    ]

    # ---------- 路径 ----------
    base_dir: Path = Path(__file__).resolve().parents[1]
    upload_dir: Path = base_dir / "uploads"
    # DATA-003：预览检测（preview=true）的临时落盘目录，不入正式 uploads，
    # 审核通过时才搬到 upload_dir；启动时清理超过 24 小时的残留。
    preview_tmp_dir: Path = base_dir / "data" / "preview_tmp"
    preview_tmp_ttl_hours: int = 24
    db_path: Path = base_dir / "data" / "agri.db"
    knowledge_dir: Path = base_dir / "knowledge"
    vector_db_path: Path = base_dir / "data" / "vector_db"
    model_path: Path = base_dir / "data" / "models" / "plant_disease_yolov8n.onnx"
    pest_model_path: Path = base_dir / "data" / "models" / "insect_best.onnx"

    # ---------- 模型 ----------
    # 四分类大类别：真菌病害 / 虫害 / 土壤缺肥 / 农药药害
    coarse_categories: list[str] = ["fungal_disease", "pest", "deficiency", "phytotoxicity"]
    coarse_labels_zh: dict[str, str] = {
        "fungal_disease": "真菌病害",
        "pest": "虫害",
        "deficiency": "土壤缺肥",
        "phytotoxicity": "农药药害",
        "unknown": "未识别",
    }
    # 细分类别（水稻/小麦/果蔬常见灾害）。
    # ASSET-005：这里的数量随新增类别变化（当前 24 类），不要写死数字，
    # 需要展示数量时用 len(settings.fine_classes) 或 /api/system/info 的 fine_classes_count。
    # general_pest 为「无对应细分模型的其他农业害虫」兜底类。
    fine_classes: list[str] = [
        "rice_blast", "rice_bacterial_blight", "rice_sheath_blight", "rice_brown_planthopper",
        "wheat_rust", "wheat_powdery_mildew", "wheat_aphid", "wheat_scab",
        "corn_leaf_blight", "corn_borer",
        "cucumber_powdery_mildew", "cucumber_downy_mildew", "tomato_early_blight",
        "tomato_late_blight", "tomato_leaf_miner",
        "apple_scab", "apple_aphid",
        "citrus_canker", "citrus_red_mite",
        "general_nitrogen_deficiency", "general_potassium_deficiency", "general_phosphorus_deficiency",
        "general_pesticide_injury",
        "general_pest",
    ]
    img_size: int = 640
    conf_threshold: float = 0.35
    pest_conf_threshold: float = 0.40  # 虫害模型阈值略高，避免弱响应误报
    iou_threshold: float = 0.45
    device: str = "cpu"  # 强制 CPU 推理，适配农村离线场景

    # ---------- 推理线程（PERF-002：批量并发下的线程超订治理）----------
    # onnxruntime 默认 intra_op 线程数 = 物理核数。前端批量是 3 并发，
    # 3 × 核数会严重线程超订：实测并发 2 降 67%、并发 3 反而只降 14%（还抖动到 56%）。
    # 把单次推理的核内线程压到固定值，把并行度让给请求级并发，吞吐才稳定。
    onnx_intra_threads: int = 2
    onnx_inter_threads: int = 1

    # ---------- 域检查门（ARCH-001：阈值集中可调，不再硬编码在推理器里）----------
    # 作用：模型之前先判断「这张图像不像农作物」，不过门直接返回未识别，避免域外图被高置信度误检
    domain_gate_enabled: bool = True
    domain_gate_green_min: float = 0.05   # 植被绿占比下限（Hue 35~85）
    domain_gate_yellow_min: float = 0.60  # 黄叶占比下限（Hue 20~35，枯黄病害叶片）
    domain_gate_edge_max: float = 0.08    # Canny 边缘密度上限（排除文字/截图/建筑）

    # ---------- AI 顾问 ----------
    # 服务端配置后，浏览器侧无需保存明文 API Key（SEC-005）
    zhipu_api_key: str = ""

    # ---------- RAG ----------
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    rag_top_k: int = 5
    rag_score_threshold: float = 0.25

    # ---------- 限流与上传 ----------
    max_upload_mb: int = 10
    allowed_extensions: list[str] = [".jpg", ".jpeg", ".png", ".webp", ".bmp"]

    def ensure_dirs(self) -> None:
        for d in (self.upload_dir, self.db_path.parent, self.vector_db_path,
                  self.model_path.parent, self.knowledge_dir, self.preview_tmp_dir):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()