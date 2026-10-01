"""全局常量 - 细分类别中文标签等共享常量。"""

# DATA-004：诊断记录里 JSON 结构（scheme / detection_boxes）的版本号。
# 结构发生不兼容变更时递增，读取端据此选择解析方式，老数据仍可正常展示。
SCHEMA_VERSION = 1

FINE_LABELS_ZH = {
    "rice_blast": "稻瘟病", "rice_bacterial_blight": "水稻白叶枯病",
    "rice_sheath_blight": "水稻纹枯病", "rice_brown_planthopper": "褐飞虱",
    "wheat_rust": "小麦锈病", "wheat_powdery_mildew": "小麦白粉病",
    "wheat_aphid": "麦蚜", "wheat_scab": "小麦赤霉病",
    "corn_leaf_blight": "玉米大斑病", "corn_borer": "玉米螟",
    "cucumber_powdery_mildew": "黄瓜白粉病", "cucumber_downy_mildew": "黄瓜霜霉病",
    "tomato_early_blight": "番茄早疫病", "tomato_late_blight": "番茄晚疫病",
    "tomato_leaf_miner": "番茄潜叶蝇", "apple_scab": "苹果黑星病", "apple_aphid": "苹果蚜虫",
    "citrus_canker": "柑橘溃疡病", "citrus_red_mite": "柑橘红蜘蛛",
    "general_nitrogen_deficiency": "缺氮黄化", "general_potassium_deficiency": "缺钾焦枯",
    "general_phosphorus_deficiency": "缺磷紫红", "general_pesticide_injury": "农药药害斑驳",
    "general_pest": "其他农业害虫",
}