"""治理方案生成器 - 根据识别类别 + RAG 知识生成用药/施肥/绿色替代方案。"""
from __future__ import annotations

from app.config import settings
from app.core.rag_engine import rag_engine


# 内置方案模板（保证无 RAG 时也可输出完整方案，国赛演示稳定）
SCHEME_TEMPLATES: dict[str, dict] = {
    "fungal_disease": {
        "diagnosis": "真菌病害",
        "cause": "田间湿度大、通风不良，真菌孢子借风雨传播侵染叶片/茎秆。",
        "chemicals": [
            {"name": "苯醚甲环唑", "dose": "10% 水分散粒剂 1500 倍液", "freq": "7-10 天一次，连用 2-3 次"},
            {"name": "吡唑醚菌酯", "dose": "250 克/升乳油 1000 倍液", "freq": "发病初期使用"},
        ],
        "green_alternatives": [
            {"name": "枯草芽孢杆菌", "dose": "1000 亿芽孢/克可湿性粉剂 800 倍液", "note": "生物农药，安全间隔期短"},
            {"name": "小苏打溶液", "dose": "0.5% 碳酸氢钠水溶液叶面喷施", "note": "改变叶面 pH 抑菌，零残留"},
        ],
        "prevention": ["合理密植，改善通风透光", "发病初期及时清除病叶", "排水降湿，避免偏施氮肥"],
    },
    "pest": {
        "diagnosis": "虫害",
        "cause": "害虫成虫产卵孵化后幼虫/若虫取食叶片、吸食汁液造成危害。",
        "chemicals": [
            {"name": "氯虫苯甲酰胺", "dose": "20% 悬浮剂 3000 倍液", "freq": "卵孵盛期施药"},
            {"name": "高效氯氟氰菊酯", "dose": "4.5% 乳油 1500 倍液", "freq": "虫口密度大时使用"},
        ],
        "green_alternatives": [
            {"name": "苏云金杆菌 Bt", "dose": "8000 IU/mg 可湿性粉剂 500 倍液", "note": "对鳞翅目幼虫高效，对人畜安全"},
            {"name": "苦参碱水剂", "dose": "0.3% 水剂 800 倍液", "note": "植物源农药，低残留"},
            {"name": "黄板/蓝板诱杀", "dose": "每亩悬挂 25-30 块", "note": "物理诱杀，零农药"},
        ],
        "prevention": ["保护利用天敌（瓢虫、草蛉）", "利用性诱剂诱杀成虫", "清除田间杂草减少虫源"],
    },
    "deficiency": {
        "diagnosis": "土壤缺肥（缺素症）",
        "cause": "土壤该元素有效态含量不足或根系吸收受阻，表现为叶片黄化、失绿、焦枯。",
        "fertilization": [
            {"element": "氮(N)", "symptom": "老叶均匀黄化", "advice": "亩追施尿素 5-8 公斤或叶面喷 0.5% 尿素"},
            {"element": "磷(P)", "symptom": "叶片暗绿/紫红", "advice": "亩追施过磷酸钙 15 公斤或叶面喷 0.2% 磷酸二氢钾"},
            {"element": "钾(K)", "symptom": "叶缘焦枯似火烧", "advice": "亩追施硫酸钾 8-10 公斤或叶面喷 0.3% 磷酸二氢钾"},
            {"element": "镁/锌/铁", "symptom": "叶脉间失绿", "advice": "叶面喷施相应中微量元素水溶肥"},
        ],
        "green_alternatives": [
            {"name": "腐熟有机肥", "dose": "亩施 200-300 公斤", "note": "改良土壤，缓释养分"},
            {"name": "测土配方施肥", "dose": "依据土壤检测报告", "note": "精准施肥，减量增效"},
        ],
        "prevention": ["定期土壤检测，按需施肥", "增施有机肥改良土壤结构", "调节土壤 pH 提高元素有效性"],
    },
    "phytotoxicity": {
        "diagnosis": "农药药害",
        "cause": "农药浓度过高、高温施药、混用不当或敏感作物误用，造成叶片斑驳、卷曲、灼伤。",
        "chemicals": [],
        "green_alternatives": [
            {"name": "清水淋洗", "dose": "立即用清水反复喷淋叶面", "note": "降低残留药液浓度"},
            {"name": "叶面肥缓解", "dose": "喷施 0.01% 芸苔素内酯+氨基酸叶面肥", "note": "促进恢复生长"},
        ],
        "fertilization": [
            {"element": "芸苔素内酯", "symptom": "缓解药害促进生长", "advice": "0.01% 可溶性液剂 3000 倍液喷施"},
        ],
        "prevention": ["严格按推荐剂量稀释，不随意加大浓度", "避开中午高温时段施药", "不盲目混配多种农药"],
    },
}

SEVERITY_FACTOR = {"mild": 0.7, "moderate": 1.0, "severe": 1.3}


def generate_scheme(
    coarse_category: str,
    fine_class: str | None = None,
    crop: str | None = None,
    severity: str = "moderate",
) -> dict:
    """生成完整治理方案，并尝试用 RAG 补充针对性建议。"""
    template = SCHEME_TEMPLATES.get(coarse_category, SCHEME_TEMPLATES["fungal_disease"]).copy()
    factor = SEVERITY_FACTOR.get(severity, 1.0)

    # 根据严重程度调整用药频次说明
    scheme = {
        "diagnosis": template["diagnosis"],
        "cause": template["cause"],
        "chemicals": _scale(template.get("chemicals", []), factor),
        "green_alternatives": template.get("green_alternatives", []),
        "fertilization": template.get("fertilization", []),
        "prevention": template.get("prevention", []),
        "severity": severity,
        "crop": crop or "通用作物",
        "fine_class": fine_class,
    }

    # RAG 检索补充针对性建议
    try:
        query = f"{crop or ''} {template['diagnosis']} 治理方案"
        rag = rag_engine.answer(query, crop=crop, top_k=3)
        if rag.get("answer"):
            scheme["rag_advice"] = rag["answer"]
            scheme["rag_sources"] = rag.get("sources", [])
    except Exception:
        pass

    scheme["remark"] = _remark(severity, coarse_category)
    return scheme


def _scale(chemicals: list[dict], factor: float) -> list[dict]:
    out = []
    for c in chemicals:
        nc = dict(c)
        if factor != 1.0:
            nc["freq"] = f"{c.get('freq','')}（严重程度调整系数 {factor}）"
        out.append(nc)
    return out


def _remark(severity: str, coarse: str) -> str:
    label = settings.coarse_labels_zh.get(coarse, coarse)
    if severity == "severe":
        return f"{label}程度较重，建议立即处置并持续观察 7 天；大面积发生请上报农技部门。"
    if severity == "mild":
        return f"{label}程度较轻，以预防为主，加强田间管理即可。"
    return f"{label}中等程度，按方案处置并 7 天后复查。"