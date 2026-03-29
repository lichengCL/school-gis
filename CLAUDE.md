# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

基于 IDW 插值的 CUIT（成都信息工程大学）校园噪音与人流时空热力图 — GIS 课程作业项目。

## 运行命令

```bash
# 生成模拟数据（GeoJSON 矢量图层 + CSV 时序数据）
python generate_data.py

# IDW 插值 + 生成 GeoTIFF 栅格 + Folium 交互式地图
python build_map.py

# 一键运行完整流水线
python generate_data.py && python build_map.py

# lint
ruff check .

# 格式化
ruff format .
```

## 关键注意事项

- 坐标系使用 GCJ-02（近似 EPSG:4326），所有经纬度数据必须保持一致
- `config.py` 中的 `CAMPUS_BOUNDARY` 和 `monitoring_points.csv` 的坐标需要用户替换为真实值
- IDW 插值结果必须用校园边界多边形做掩膜裁剪（Mask），不能溢出到校外
- GeoTIFF 输出时行序从北到南（纬度递减），需要翻转数组
- 高德瓦片 URL 无需 API Key，但 `config.py` 中预留了 Key 字段

## 输出文件

- `output/campus_heatmap.html` — 交互式 Folium 地图（浏览器打开）
- `output/raster/*.tif` — GeoTIFF 栅格（可在 QGIS/ArcGIS 中打开）
- `data/*.geojson` — 矢量图层（可在 QGIS/ArcGIS 中打开）

## Git 规范

- Commit message 用中文
