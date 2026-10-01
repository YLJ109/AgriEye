"""小样本训练脚本 - 国赛核心创新点。

策略：
1. 强数据增强（田间复杂环境模拟）弥补样本不足
2. 迁移学习：加载预训练权重，冻结 backbone，仅微调检测头
3. 渐进式解冻：后期解冻部分层提升精度
4. CPU 训练友好（batch 小 + 混合精度关闭）
"""
from __future__ import annotations

import argparse
from pathlib import Path

import torch
from loguru import logger


def train(data_yaml: str, epochs: int = 50, imgsz: int = 640,
          batch: int = 8, device: str = "cpu",
          weights: str = "yolov8n.pt", project: str = "runs/train",
          name: str = "agri_lite") -> str:
    """执行小样本训练，返回最佳模型路径。"""
    from ultralytics import YOLO

    logger.info(f"开始小样本训练：data={data_yaml} epochs={epochs} device={device}")

    model = YOLO(weights)

    # 阶段一：冻结 backbone，仅训练检测头（小样本防过拟合）
    logger.info("阶段一：冻结 backbone 微调检测头")
    model.train(
        data=data_yaml, epochs=max(10, epochs // 3), imgsz=imgsz,
        batch=batch, device=device, project=project, name=f"{name}_stage1",
        freeze=10,  # 冻结前 10 层
        lr0=0.01, lrf=0.1, patience=10,
        augment=True, hsv_h=0.02, hsv_s=0.7, hsv_v=0.4,  # 强色彩增强
        degrees=15.0, translate=0.15, scale=0.5,  # 几何增强
        fliplr=0.5, mosaic=1.0, mixup=0.1,  # 拼接增强
        workers=0, verbose=True,
    )

    # 阶段二：解冻全部，小学习率精调
    logger.info("阶段二：全网络小学习率精调")
    best_stage1 = Path(project) / f"{name}_stage1" / "weights" / "best.pt"
    if best_stage1.exists():
        model = YOLO(str(best_stage1))
    results = model.train(
        data=data_yaml, epochs=epochs - epochs // 3, imgsz=imgsz,
        batch=batch, device=device, project=project, name=f"{name}_stage2",
        freeze=0, lr0=0.001, lrf=0.01, patience=15,
        augment=True, workers=0, verbose=True,
    )

    best = Path(project) / f"{name}_stage2" / "weights" / "best.pt"
    logger.info(f"训练完成，最佳模型：{best}")
    return str(best)


def main():
    ap = argparse.ArgumentParser(description="农作物病虫害小样本训练")
    ap.add_argument("--data", default="data/dataset/data.yaml")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--weights", default="yolov8n.pt")
    args = ap.parse_args()

    torch.set_num_threads(max(1, torch.get_num_threads()))
    best = train(args.data, args.epochs, args.imgsz, args.batch,
                 args.device, args.weights)
    print(f"\n✅ 训练完成，最佳模型：{best}")
    print("下一步：python algorithm/yolov8_lite/quantize.py --weights", best)


if __name__ == "__main__":
    main()