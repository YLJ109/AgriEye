"""模型压缩量化导出 - 离线轻量化部署核心。

流程：PyTorch best.pt -> ONNX (FP16) -> INT8 动态量化 -> 部署到后端。
INT8 量化后体积减少约 4 倍，CPU 推理速度提升 2-3 倍，适配手机端离线。
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from loguru import logger


def export_onnx(weights: str, imgsz: int = 640, simplify: bool = True,
                half: bool = True, out_dir: str | None = None) -> str:
    """导出 ONNX 模型。"""
    from ultralytics import YOLO
    model = YOLO(weights)
    out_dir = Path(out_dir) if out_dir else Path(weights).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    onnx_path = out_dir / "yolov8_lite_agri.onnx"
    model.export(
        format="onnx", imgsz=imgsz, simplify=simplify, dynamic=False,
        half=half, opset=12,
    )
    # ultralytics 默认导出到 weights 同目录，重命名
    default_onnx = Path(weights).with_suffix(".onnx")
    if default_onnx.exists() and default_onnx != onnx_path:
        default_onnx.rename(onnx_path)
    logger.info(f"ONNX 导出完成：{onnx_path} （FP16={'开' if half else '关'}）")
    return str(onnx_path)


def quantize_int8(onnx_path: str, out_path: str | None = None) -> str:
    """对 ONNX 模型做 INT8 动态量化。"""
    import onnx
    from onnxruntime.quantization import quantize_dynamic, QuantType

    out_path = out_path or onnx_path.replace(".onnx", "_int8.onnx")
    quantize_dynamic(
        onnx_path, out_path,
        weight_type=QuantType.QUInt8,
        op_types_to_quantize=["MatMul", "Gemm", "Conv"],
    )
    # 体积统计
    orig = Path(onnx_path).stat().st_size / 1024
    quant = Path(out_path).stat().st_size / 1024
    logger.info(f"INT8 量化完成：{out_path}")
    logger.info(f"体积变化：{orig:.1f}KB -> {quant:.1f}KB（压缩率 {quant/orig*100:.0f}%）")
    return out_path


def benchmark(onnx_path: str, imgsz: int = 640, runs: int = 30) -> dict:
    """推理性能基准测试。"""
    import onnxruntime as ort
    import cv2, time

    sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0].name
    dummy = np.random.rand(1, 3, imgsz, imgsz).astype(np.float32)

    # warmup
    for _ in range(5):
        sess.run(None, {inp: dummy})
    t0 = time.perf_counter()
    for _ in range(runs):
        sess.run(None, {inp: dummy})
    avg_ms = (time.perf_counter() - t0) / runs * 1000
    size_kb = Path(onnx_path).stat().st_size / 1024
    logger.info(f"推理基准：{avg_ms:.1f} ms/张，模型 {size_kb:.1f} KB")
    return {"avg_ms": round(avg_ms, 2), "size_kb": round(size_kb, 1), "runs": runs}


def main():
    ap = argparse.ArgumentParser(description="模型量化压缩导出")
    ap.add_argument("--weights", required=True, help="best.pt 路径")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--out-dir", default="backend/data/models")
    ap.add_argument("--no-int8", action="store_true")
    args = ap.parse_args()

    onnx = export_onnx(args.weights, args.imgsz, out_dir=args.out_dir)
    if not args.no_int8:
        quantize_int8(onnx)
    benchmark(onnx)


if __name__ == "__main__":
    main()