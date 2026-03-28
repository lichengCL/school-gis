# 🎓 CUIT 校园"噪音与卷度"时空分布热力图

> 成都信息工程大学（CUIT）航空港校区 · GIS 课程作业 · 基于 IDW 空间插值的校园噪音/人流时空分析

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Folium](https://img.shields.io/badge/Folium-0.15+-green) ![GeoPandas](https://img.shields.io/badge/GeoPandas-1.0+-orange) ![License](https://img.shields.io/badge/License-MIT-lightgrey)

## 效果预览

交互式热力图支持：
- 时间轴滑块（周一 7:00 → 周日 23:00，每 2 小时一帧，共 63 帧）
- 噪音分贝热力面（绿色=安静 → 红色=嘈杂）
- 10 个监测点标记（点击查看详情）
- 校园边界轮廓线（掩膜裁剪，热力不溢出校外）
- 高德地图底图

## 技术栈

| 模块 | 用途 |
|------|------|
| GeoPandas | 矢量数据（GeoJSON 点/面图层） |
| rasterio | 栅格数据（GeoTIFF 输出） |
| Shapely | 几何运算（边界掩膜） |
| Folium | 交互式 Web 地图 |
| NumPy / Pandas | 数值计算 / 数据处理 |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 生成模拟数据（GeoJSON + CSV）
python generate_data.py

# 3. IDW 插值 + 生成地图
python build_map.py

# 4. 打开地图
# 用浏览器打开 output/campus_heatmap.html
```

## 项目结构

```
school-gis/
├── config.py              # 全局配置（坐标、参数、时间）
├── idw.py                 # IDW 空间插值 + GeoTIFF 导出
├── generate_data.py       # 模拟数据生成（正态分布 + 时间规律）
├── build_map.py           # 主程序：插值 → 栅格 → 交互地图
├── requirements.txt
├── data/
│   ├── monitoring_points.csv      # 监测点基准数据
│   ├── monitoring_points.geojson  # 矢量点图层（EPSG:4326）
│   └── campus_boundary.geojson   # 校园边界面图层
└── output/
    ├── campus_heatmap.html        # 交互式地图（浏览器打开）
    └── raster/                    # GeoTIFF 栅格（63 个时间切片）
```

## GIS 核心概念

本项目完整演示了以下 GIS 工作流：

1. **矢量数据模型** — 监测点（Point）和校园边界（Polygon）以 GeoJSON 格式存储，带 CRS 信息
2. **矢量→栅格转换** — IDW 空间插值将离散点数据转换为连续栅格面
3. **掩膜裁剪（Mask）** — 用校园边界多边形裁剪插值结果，热力面精确限制在校园范围内
4. **GeoTIFF 输出** — 标准地理栅格格式，可在 QGIS/ArcGIS 中直接打开
5. **坐标参考系（CRS）** — 全程使用 EPSG:4326，与高德地图 GCJ-02 近似对齐

## 数据说明

### 监测点（10 个）

| 编号 | 地点 | 类型 | 特征 |
|------|------|------|------|
| 1 | 图书馆 | library | 晚上高峰，23:00 闭馆骤降 |
| 2 | 第一教学楼 | classroom | 上课时段嘈杂，周末几乎为零 |
| 3 | 第二教学楼 | classroom | 同上 |
| 4 | 一食堂 | canteen | 三餐脉冲高峰 |
| 5 | 二食堂 | canteen | 三餐脉冲高峰 |
| 6 | 学生宿舍A区 | dorm | 白天低谷，21:00 后高峰 |
| 7 | 学生宿舍B区 | dorm | 同上 |
| 8 | 体育场 | sports | 傍晚高峰，周末全天活跃 |
| 9 | 行政楼 | admin | 工作时间中等，其余安静 |
| 10 | 校门口 | gate | 上下课高峰 |

### 数据生成方法

```
实际值 = 基准值 × 时间系数(建筑类型, 小时) × 星期系数(建筑类型, 工作日/周末)
       + N(0, σ)   # 正态分布扰动，σ ≈ 基准值 × 10%
```

噪音范围：25–95 dB；人流等级：0–10

## 替换真实数据

1. 用手机分贝仪 App 实测各监测点基准噪音，更新 `data/monitoring_points.csv` 的 `base_noise_db` 列
2. 在高德地图上标注各建筑的精确 GCJ-02 坐标，更新 `lat`/`lng` 列
3. 用真实校园轮廓更新 `config.py` 中的 `CAMPUS_BOUNDARY`
4. 重新运行 `python generate_data.py && python build_map.py`

## License

MIT
