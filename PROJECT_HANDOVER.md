# PROJECT_HANDOVER — 基于 IDW 插值的 CUIT 校园噪音与人流时空热力图

> 本文档面向接手此项目的任何人（包括未来的自己），目标是让读者在不问任何人的情况下，完全理解并能独立运行、修改、扩展本项目。

---

## 1. 项目背景与目标

### 1.1 课程背景

本项目是 GIS（地理信息系统）课程作业，题目为“基于 IDW 插值的 CUIT 校园噪音与人流时空热力图”。核心考察点：

- 空间插值（Spatial Interpolation）的理解与应用
- GIS 数据模型（矢量/栅格）的实际操作
- 地图配色与可视化美观度
- 数据收集的巧思（加分项：时间轴切片动态展示）

### 1.2 选题逻辑

把空间分析应用到极其微观的日常生活——校园里的噪音和人流密度。这个选题的优势：

- 数据可自行采集（手机分贝仪 App），不依赖外部数据源
- 时间规律明显（食堂饭点、图书馆晚高峰、宿舍夜间），模拟数据符合直觉
- 可视化效果直观，答辩时容易讲清楚

### 1.3 最终产出

| 产出物 | 路径 | 说明 |
|--------|------|------|
| 交互式热力图 | `output/campus_heatmap.html` | 浏览器打开，含时间轴滑块 |
| GeoTIFF 栅格 | `output/raster/*.tif` | 63 个时间切片，可在 QGIS/ArcGIS 打开 |
| 矢量点图层 | `data/monitoring_points.geojson` | 10 个监测点，EPSG:4326 |
| 校园边界图层 | `data/campus_boundary.geojson` | 校园轮廓多边形 |
| 时序数据 | `data/weekly_data.csv` | 630 条记录（10点×7天×9时段） |

---

## 2. 环境配置

### 2.1 Python 版本

Python 3.10+（开发时使用 3.13.2）

### 2.2 依赖安装

```bash
pip install -r requirements.txt
```

依赖清单：

| 包 | 版本 | 用途 |
|----|------|------|
| folium | >=0.15 | 交互式 Web 地图 |
| numpy | 任意 | 数值计算、网格生成 |
| pandas | 任意 | 数据读写、时序处理 |
| shapely | 任意 | 几何运算（点在多边形内判断） |
| geopandas | 任意 | GeoDataFrame、GeoJSON 读写 |
| rasterio | 任意 | GeoTIFF 栅格读写、仿射变换 |
| scipy | 任意 | 预留（当前未直接使用，备用插值方法） |

### 2.3 可选工具

```bash
pip install ruff   # 代码格式化/lint（已配置 format-on-edit hook）
```

---

## 3. 文件结构详解

```
school-gis/
├── config.py                    ← 所有可调参数的唯一入口
├── idw.py                       ← 核心算法：IDW 插值 + GeoTIFF 导出
├── generate_data.py             ← 数据生成：GeoJSON 矢量图层 + CSV 时序数据
├── build_map.py                 ← 主程序：读数据 → 插值 → 输出地图
├── requirements.txt
├── CLAUDE.md                    ← Claude Code 项目指令
├── .gitignore
├── .claude/
│   ├── settings.json            ← format-on-edit hook（ruff）
│   └── skills/
│       ├── run/SKILL.md         ← /run 技能：一键运行流水线
│       └── verify/SKILL.md     ← /verify 技能：lint + 完整验证
├── data/
│   ├── monitoring_points.csv    ← 监测点基准数据（手动填写/实测）
│   ├── monitoring_points.geojson← 由 generate_data.py 生成
│   ├── campus_boundary.geojson  ← 由 generate_data.py 生成
│   └── weekly_data.csv          ← 由 generate_data.py 生成
└── output/
    ├── campus_heatmap.html      ← 最终交互式地图（不提交 git）
    └── raster/                  ← GeoTIFF 栅格文件（不提交 git）
```

---

## 4. 核心模块逐行解析

### 4.1 config.py — 全局配置

所有可调参数都在这里，修改其他文件前先看这里。

**关键参数：**

```python
CAMPUS_CENTER = [30.5795, 103.9945]   # 地图初始中心点（GCJ-02）
MAP_ZOOM = 17                          # 初始缩放级别（17 适合校园尺度）
GRID_RESOLUTION = 80                   # IDW 网格分辨率（80×80=6400个格点）
IDW_POWER = 2                          # IDW 幂次（2 是标准值，越大局部效果越强）
HOURS = list(range(7, 24, 2))          # [7,9,11,13,15,17,19,21,23]
```

**CAMPUS_BOUNDARY** — 校园边界多边形，13 个顶点，顺时针排列，首尾坐标相同（闭合）。这是掩膜裁剪的依据，**必须替换为真实坐标**。

**坐标系说明：** 高德地图使用 GCJ-02（国测局坐标），与 WGS84（EPSG:4326）有约 100-500 米偏移。本项目在校园尺度下近似处理为 EPSG:4326，误差可接受。如需精确，需要做 GCJ-02 → WGS84 转换。

### 4.2 idw.py — IDW 空间插值

**IDW 原理：**

反距离权重法（Inverse Distance Weighting）。对于目标点 P，其插值结果为：

```
Z(P) = Σ(w_i × Z_i) / Σ(w_i)
其中 w_i = 1 / d(P, P_i)^p
```

- `d(P, P_i)` 是目标点到第 i 个已知点的距离
- `p` 是幂次参数（`IDW_POWER = 2`）
- 距离越近权重越大，体现"近处影响大"的直觉

**`idw_interpolate()` 函数：**

```python
def idw_interpolate(points, values, grid_lats, grid_lngs, power=IDW_POWER):
```

- 输入：已知点坐标数组 `(n, 2)`、对应值数组 `(n,)`、网格坐标
- 内层双循环遍历每个网格点，先做边界掩膜判断（`_campus_poly.contains(Point(...))`），校园外的点跳过并设为 NaN
- 对校园内的点计算到所有已知点的欧氏距离，做加权平均
- 特殊处理：目标点与已知点重合时（距离 < 1e-10），直接取该点的值，避免除零
- 输出：插值结果二维数组 + 掩膜布尔数组

**`save_geotiff()` 函数：**

将插值结果保存为标准 GeoTIFF。关键细节：

```python
transform = from_bounds(lng_min, lat_min, lng_max, lat_max, width, height)
dst.write(data[::-1].astype("float32"), 1)  # 注意：行序翻转！
```

GeoTIFF 的行序是从北到南（纬度递减），而 numpy 数组的行序是从南到北（纬度递增），所以写入时需要 `[::-1]` 翻转。校园外的 NaN 替换为 nodata=-9999。

### 4.3 generate_data.py — 数据生成

**两层系数叠加：**

```python
实际值 = base_value × TIME_PROFILES[type][hour] × WEEKDAY_FACTORS[type][weekday/weekend]
       + numpy.random.normal(0, base_value × 0.08~0.10)
```

**TIME_PROFILES** — 每种建筑类型的 24h 时间系数曲线（只定义了 HOURS 中的 9 个时间点）：

| 类型 | 高峰时段 | 低谷时段 |
|------|---------|---------|
| library | 19:00-21:00（系数 1.2-1.3） | 7:00、23:00（系数 0.1-0.2） |
| classroom | 9:00、11:00、15:00、17:00 | 21:00、23:00 |
| canteen | 7:00（早餐）、11:00（午餐）、17:00（晚餐） | 9:00、15:00（系数 0.1） |
| dorm | 21:00-23:00 | 11:00-15:00 |
| sports | 17:00-19:00 | 13:00 |
| admin | 9:00-17:00 | 19:00 以后 |
| gate | 7:00、11:00、17:00 | 9:00、21:00 |

**WEEKDAY_FACTORS** — 工作日/周末系数：

- classroom 周末系数 0.15（几乎没人上课）
- sports 周末系数 1.4（周末运动更多）
- admin 周末系数 0.1（行政楼关门）

**输出的三个文件：**

1. `data/campus_boundary.geojson` — 从 `config.CAMPUS_BOUNDARY` 生成的 Polygon 要素
2. `data/monitoring_points.geojson` — 从 CSV 读取后转换为 GeoDataFrame，每行变成一个 Point 要素
3. `data/weekly_data.csv` — 630 条记录，字段：`id, name, type, lat, lng, day, day_idx, hour, noise_db, crowd_level`

### 4.4 build_map.py — 主程序

**`build_heatmap_data()` 函数：**

双层循环（7天 × 9时段 = 63次）：
1. 筛选当前时间切片的数据子集
2. 调用 `idw_interpolate()` 得到 80×80 插值网格
3. 调用 `save_geotiff()` 导出 GeoTIFF（命名如 `noise_db_周一_07.tif`）
4. 对插值结果归一化到 [0,1]（用于热力图权重）
5. 过滤掉权重 < 0.05 的点（减少 HTML 体积），转换为 `[lat, lng, weight]` 列表

**`create_map()` 函数：**

Folium 地图构建顺序（顺序影响图层叠加）：
1. 高德瓦片底图（`TileLayer`）
2. 校园边界（从 GeoJSON 加载，`folium.GeoJson`，虚线样式）
3. 噪音热力图（`HeatMapWithTime`，含时间轴控件）
4. 监测点标记（`folium.Marker`，按建筑类型用不同图标和颜色）
5. 图层控制（`LayerControl`）
6. 标题和图例（原始 HTML 注入）

**HeatMapWithTime 关键参数：**

```python
HeatMapWithTime(
    data=heat_data_noise,   # list of list，63个时间帧
    index=time_labels,      # ["周一 07:00", "周一 09:00", ...]
    radius=25,              # 热力点半径（像素）
    blur=20,                # 模糊程度
    gradient={0.2: "#00ff00", 0.5: "#ffff00", 0.8: "#ff8800", 1.0: "#ff0000"},
    auto_play=True,         # 自动播放
    speed_step=0.5,         # 播放速度
)
```

---

## 5. 完整运行流程

```bash
# Step 1: 安装依赖（首次）
pip install -r requirements.txt

# Step 2: 生成数据
python generate_data.py
# 输出：
#   data/campus_boundary.geojson
#   data/monitoring_points.geojson
#   data/weekly_data.csv（630条）

# Step 3: 生成地图
python build_map.py
# 输出：
#   output/raster/noise_db_周一_07.tif ... (63个)
#   output/campus_heatmap.html

# Step 4: 查看结果
# 浏览器打开 output/campus_heatmap.html
```

---

## 6. 替换真实数据的操作步骤

### 6.1 采集真实坐标

1. 打开高德地图网页版（amap.com）
2. 右键点击各建筑位置 → "在此处添加标注" → 记录经纬度
3. 注意：高德地图显示的是 GCJ-02 坐标，直接使用即可

### 6.2 更新监测点数据

编辑 `data/monitoring_points.csv`，替换 `lat`、`lng`、`base_noise_db`、`base_crowd` 列：

```csv
id,name,type,lat,lng,base_noise_db,base_crowd
1,图书馆,library,你测的纬度,你测的经度,实测分贝,目测人流
...
```

`base_noise_db`：用手机分贝仪 App 在该地点测量，取平日白天的平均值（非高峰时段）。
`base_crowd`：目测人流密度，1=几乎没人，10=非常拥挤。

### 6.3 更新校园边界

在高德地图上沿校园围墙描点，记录各顶点坐标，更新 `config.py` 中的 `CAMPUS_BOUNDARY`：

```python
CAMPUS_BOUNDARY = [
    [纬度1, 经度1],
    [纬度2, 经度2],
    ...
    [纬度1, 经度1],  # 必须与第一个点相同（闭合）
]
```

### 6.4 重新生成

```bash
python generate_data.py && python build_map.py
```

---

## 7. 常见问题

### Q: 热力图溢出到校园外面了

检查 `config.py` 中的 `CAMPUS_BOUNDARY` 坐标是否正确，确保是闭合多边形（首尾坐标相同）。

### Q: GeoTIFF 在 QGIS 中打开后颜色全是灰色

正常现象。QGIS 默认用灰度渲染单波段栅格。右键图层 → 属性 → 符号系统 → 渲染类型改为"单波段伪彩色"，选择色带即可。

### Q: 地图加载很慢或 HTML 文件很大

降低 `config.py` 中的 `GRID_RESOLUTION`（如从 80 改为 50），或提高 `build_map.py` 中的权重过滤阈值（如从 0.05 改为 0.1）。

### Q: 高德底图不显示

高德瓦片 URL 无需 API Key，但需要网络连接。离线环境下底图会显示为空白，热力图和标记仍然正常。

### Q: 想增加监测点

在 `data/monitoring_points.csv` 中添加新行，确保 `type` 字段是以下之一：`library / classroom / canteen / dorm / sports / admin / gate`。如果是新类型，需要在 `generate_data.py` 的 `TIME_PROFILES` 和 `WEEKDAY_FACTORS` 中添加对应配置。

---

## 8. 扩展方向

### 8.1 加入人流热力图图层切换

`build_map.py` 中 `build_heatmap_data()` 已经支持 `metric` 参数，`heat_data_crowd` 也已计算好，只需在 `create_map()` 中添加第二个 `HeatMapWithTime` 图层并加入 `LayerControl` 即可。

### 8.2 提高插值精度

当前 IDW 使用欧氏距离（经纬度差），在小范围内误差可接受。如需更精确，可改用投影坐标系（如 EPSG:32648 UTM Zone 48N）计算真实米制距离。

### 8.3 加入真实噪音数据

如果有多个时间点的实测数据，可以直接替换 `weekly_data.csv` 中对应行的 `noise_db` 值，模拟数据和真实数据可以混用。

### 8.4 导出为 Shapefile

在 `generate_data.py` 中，将 `gdf.to_file(path, driver="GeoJSON")` 改为 `gdf.to_file(path, driver="ESRI Shapefile")` 即可导出 Shapefile 格式（ArcGIS 原生格式）。

---

## 9. 答辩要点

答辩时重点讲以下几个点，能拿到大部分分数：

1. **为什么用 IDW？** 因为它符合"距离衰减"的物理直觉——离食堂越近噪音越大，越远影响越小。幂次 p=2 是标准选择，p 越大局部效果越强。

2. **掩膜裁剪的意义** — 没有掩膜，插值结果会铺满整个矩形区域，包括校外的马路和居民区，这在 GIS 上是不专业的。用校园边界 Polygon 做 Mask 是体现专业度的关键操作。

3. **矢量 vs 栅格** — 监测点是矢量数据（离散点），IDW 插值后变成栅格数据（连续面），这是 GIS 中"矢量→栅格转换"的典型应用场景。

4. **数据的真实性** — 基准值来自手机分贝仪实测，时间规律来自对校园生活的观察，正态分布扰动让数据符合统计学规律。

5. **时间轴动态展示** — 63 帧时间切片，从周一 7:00 到周日 23:00，直观展示校园噪音的时空动态转移过程。

---

*最后更新：2026-03-28*
