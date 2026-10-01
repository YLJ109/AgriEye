"""批量推理基准（PERF-002 的验收依据）。

清单要求：一次传 10 张时，总耗时相对串行下降 ≥30%。
这里直接对推理引擎做端到端计时（不经过 HTTP，排除网络抖动），对比：
  - 串行：逐张推理
  - 并发 N：线程池并发（对应前端 DETECT_CONCURRENCY=3）

用法：
    cd backend
    python scripts/bench_batch.py            # 默认 10 张、并发 3
    python scripts/bench_batch.py 10 3       # 指定张数与并发数
"""
from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.model_inference import inference_engine

N_IMAGES = int(sys.argv[1]) if len(sys.argv) > 1 else 10
CONCURRENCY = int(sys.argv[2]) if len(sys.argv) > 2 else 3


def make_leaf(seed: int) -> np.ndarray:
    """合成一张「像农作物」的图：低频绿色底 + 柔和病斑。

    关键点：必须是**低频平滑**图像。域检查门要求 Canny 边缘密度 ≤0.08，
    逐像素随机噪声的边缘密度会到 0.33，直接被门挡掉、根本跑不到模型，
    基准就变成假的 11ms/张。这里用「小网格上采样 + 高斯模糊」保证平滑。
    """
    rng = np.random.default_rng(seed)
    h, w = 480, 640
    small = np.zeros((6, 8, 3), dtype=np.uint8)
    small[:, :, 0] = rng.integers(40, 75, (6, 8))        # 绿 hue
    small[:, :, 1] = rng.integers(120, 220, (6, 8))
    small[:, :, 2] = rng.integers(90, 200, (6, 8))
    hsv = cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)
    img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    img = cv2.GaussianBlur(img, (31, 31), 0)
    # 柔和病斑（模糊后边缘弱），让模型有东西可检
    for _ in range(rng.integers(3, 8)):
        cx, cy = rng.integers(0, w), rng.integers(0, h)
        r = rng.integers(20, 60)
        cv2.circle(img, (int(cx), int(cy)), int(r), (30, 40, 120), -1)
    return cv2.GaussianBlur(img, (21, 21), 0)


def bench(images: list[np.ndarray], workers: int) -> float:
    """同一批图跑不同并发，且每轮先清缓存。

    两个坑都踩过：
      1. 复用同一批图但不清缓存 -> 第二轮全命中，测的是字典查询；
      2. 每轮换新图避开缓存 -> 串行与并发测的不是同一批 workload，结果会离谱到 -22%。
    正确做法：同一批图 + 每轮 clear_result_cache()。
    """
    inference_engine.clear_result_cache()
    t0 = time.perf_counter()
    if workers <= 1:
        for im in images:
            inference_engine.predict(im)
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(inference_engine.predict, images))
    return time.perf_counter() - t0


def main() -> int:
    print(f"加载推理引擎（含懒加载的虫害模型）…")
    inference_engine.load()
    images = [make_leaf(i) for i in range(N_IMAGES)]

    # 预热：第一张会触发虫害模型懒加载，不计入基准
    inference_engine.predict(make_leaf(9999))
    print(f"预热完成。样本 {N_IMAGES} 张，并发上限 {CONCURRENCY}\n")

    serial = bench(images, 1)
    print(f"串行（1 线程）      : {serial:7.2f}s   平均 {serial / N_IMAGES * 1000:6.0f}ms/张")

    results = {}
    for wc in sorted({2, CONCURRENCY, 4}):
        if wc > N_IMAGES:
            continue
        t = bench(images, wc)
        results[wc] = t
        drop = (1 - t / serial) * 100
        print(f"并发 {wc}            : {t:7.2f}s   平均 {t / N_IMAGES * 1000:6.0f}ms/张   耗时下降 {drop:5.1f}%")

    target = results.get(CONCURRENCY)
    print()
    if target is not None:
        drop = (1 - target / serial) * 100
        verdict = "达标" if drop >= 30 else "未达标"
        print(f"验收口径（并发 {CONCURRENCY} 下降 ≥30%）：实测 {drop:.1f}% -> {verdict}")
    print("注：CPU 上 ONNX 推理受物理核数限制，并发超过核数后收益会趋于平缓。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
