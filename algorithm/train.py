"""算法模块统一入口 - 一键执行：构建数据集 -> 训练 -> 量化 -> 部署。

用法：
    python -m algorithm.train            # 全流程
    python -m algorithm.train --skip-data  # 跳过数据集构建
"""
from __future__ import annotations

import argparse
from pathlib import Path
from loguru import logger


def run_pipeline(skip_data: bool = False, skip_train: bool = False,
                 epochs: int = 50, device: str = "cpu") -> None:
    root = Path(__file__).resolve().parents[1]

    # 1. 数据集构建
    if not skip_data:
        logger.info("【1/4】构建农作物病虫害数据集...")
        from algorithm.data_builder.build_dataset import build_dataset
        stats = build_dataset(root / "data" / "dataset", per_class=30)
        logger.info(f"数据集完成：{stats['total']} 张，{len(stats['classes'])} 类")
    else:
        logger.info("【1/4】跳过数据集构建")

    data_yaml = str(root / "data" / "dataset" / "data.yaml")
    if not Path(data_yaml).exists():
        logger.error("数据集不存在，请先构建")
        return

    # 2. 小样本训练
    best = None
    if not skip_train:
        logger.info("【2/4】小样本训练 YOLOv8-lite...")
        from algorithm.yolov8_lite.train import train
        best = train(data_yaml, epochs=epochs, device=device)
    else:
        logger.info("【2/4】跳过训练")
        best = str(root / "runs" / "train" / "agri_lite_stage2" / "weights" / "best.pt")

    # 3. 量化导出
    if best and Path(best).exists():
        logger.info("【3/4】模型量化压缩导出...")
        from algorithm.yolov8_lite.quantize import export_onnx, quantize_int8
        out_dir = root / "backend" / "data" / "models"
        onnx = export_onnx(best, out_dir=str(out_dir))
        try:
            quantize_int8(onnx)
        except Exception as e:
            logger.warning(f"INT8 量化跳过：{e}")
    else:
        logger.warning("【3/4】未找到训练模型，跳过量化（可后续训练后执行）")

    # 4. 知识库构建
    logger.info("【4/4】构建 RAG 向量知识库...")
    try:
        import sys
        sys.path.insert(0, str(root / "backend"))
        from knowledge.build_vector_db import build_vector_db
        build_vector_db()
        logger.info("知识库构建完成")
    except Exception as e:
        logger.warning(f"知识库构建跳过：{e}")

    logger.info("✅ 全流程完成！可启动后端：cd backend && uvicorn app.main:app --reload")


def main():
    ap = argparse.ArgumentParser(description="算法全流程一键执行")
    ap.add_argument("--skip-data", action="store_true")
    ap.add_argument("--skip-train", action="store_true")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()
    run_pipeline(args.skip_data, args.skip_train, args.epochs, args.device)


if __name__ == "__main__":
    main()