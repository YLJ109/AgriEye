"""识别引擎域检查门回归（ARCH-001 / 域检查前置）。

用合成图像做断言，保证测试零外部素材依赖、可离线复现：
- 纯绿块           -> 像植物，应通过域检查
- 枯黄块           -> 黄叶是合法识别对象，应通过
- 灰阶噪声（截图感）-> 不像植物，应拦截
若有真实样本放在 tests/fixtures/ 下（plant_*.jpg / nonplant_*.jpg），会一并纳入回归。
"""
from pathlib import Path

import cv2
import numpy as np
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _solid(hsv_color) -> np.ndarray:
    """生成指定 HSV 颜色的纯色图（BGR 返回）。"""
    h, s, v = hsv_color
    img = np.zeros((160, 160, 3), dtype=np.uint8)
    img[:, :] = (h, s, v)
    return cv2.cvtColor(img, cv2.COLOR_HSV2BGR)


def _noise_gray() -> np.ndarray:
    """灰阶高频噪声：模拟屏幕截图/文字页面的高边缘密度特征。"""
    rng = np.random.default_rng(42)          # 固定种子，保证可复现
    gray = rng.integers(0, 256, (240, 320), dtype=np.uint8)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def test_green_leaf_passes_gate(engine):
    engine._looks_like_plant(_solid((60, 180, 180)))   # 植被绿
    assert engine._looks_like_plant(_solid((60, 180, 180))) is True


def test_yellow_leaf_passes_gate(engine):
    assert engine._looks_like_plant(_solid((25, 200, 200))) is True  # 枯黄叶片


def test_gray_noise_blocked_by_gate(engine):
    assert engine._looks_like_plant(_noise_gray()) is False


def test_unknown_mode_returned_for_off_domain_image(engine):
    """域外图必须返回 mode=unknown，且置信度为 0，绝不走模型误检。"""
    result = engine.predict(_noise_gray())
    assert result.mode == "unknown"
    assert result.coarse_category == "unknown"
    assert result.confidence == 0.0


def test_predict_never_crashes_on_plain_white(engine):
    white = np.full((200, 200, 3), 255, dtype=np.uint8)
    result = engine.predict(white)            # 不应抛异常
    assert result is not None
    assert result.mode in {"model", "heuristic", "unknown"}


# ---------- 真实样本（可选）----------
def _collect(name_pattern: str):
    return sorted(FIXTURES.glob(name_pattern))


@pytest.mark.skipif(not _collect("plant_*.*"), reason="tests/fixtures 下无 plant_* 样本")
def test_real_plant_samples_are_recognized(engine):
    for path in _collect("plant_*.*"):
        img = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
        assert img is not None, f"{path.name} 无法解码（中文路径请用 np.fromfile）"
        assert engine._looks_like_plant(img) is True, f"{path.name} 应通过域检查"


@pytest.mark.skipif(not _collect("nonplant_*.*"), reason="tests/fixtures 下无 nonplant_* 样本")
def test_real_nonplant_samples_are_blocked(engine):
    for path in _collect("nonplant_*.*"):
        img = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
        assert img is not None
        assert engine.predict(img).mode == "unknown", f"{path.name} 应被域检查拦截"
