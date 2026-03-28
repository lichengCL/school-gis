---
name: run
description: 一键运行完整 GIS 流水线（生成数据 → IDW 插值 → 输出地图）。当需要重新生成数据或地图时使用。
---

运行完整的 GIS 分析流水线：

1. 执行 `python generate_data.py` 生成模拟数据（GeoJSON + CSV）
2. 执行 `python build_map.py` 进行 IDW 插值并生成交互式热力图和 GeoTIFF 栅格

两步必须按顺序执行。运行完成后告知用户输出文件路径。
