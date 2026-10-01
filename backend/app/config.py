"""全局配置中心 - 集中管理所有可调参数，便于国赛演示与离线部署。"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---------- 服务 ----------
    app_name: str = "农智 AI 顾问系统"
    host: str = "0.0.0.0"
    port: int = 8001
    # 前端固定 5188（5173 属另一个项目，勿占用）。如需其他端口，用环境变量 CORS_ORIGINS 覆盖。
    cors_origins: list[str] = [
        "http://localhost:5188", "http://127.0.0.1:5188",
        "http://localhost:5173", "http://127.0.0.1:5173",  # 兼容老 dev 端口
    ]

    # ---------- 路径 ----------
    base_dir: Path = Path(__file__).resolve().parents[1]
    upload_dir: Path = base_dir / "uploads"
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
    # 细分 20 类（水稻/小麦/果蔬常见灾害）
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

    # ---------- RAG ----------
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    rag_top_k: int = 5
    rag_score_threshold: float = 0.25

    # ---------- 限流与上传 ----------
    max_upload_mb: int = 10
    allowed_extensions: list[str] = [".jpg", ".jpeg", ".png", ".webp", ".bmp"]

    def ensure_dirs(self) -> None:
        for d in (self.upload_dir, self.db_path.parent, self.vector_db_path,
                  self.model_path.parent, self.knowledge_dir):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()