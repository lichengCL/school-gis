# -*- coding: utf-8 -*-
"""
基于正态分布 + 时间规律模板生成一周模拟数据。

GIS 核心概念：
- 矢量数据模型（点要素 + 属性表）
- GeoJSON / Shapefile 标准地理数据格式
- 坐标参考系（CRS）

运行: python generate_data.py
输出:
  - data/monitoring_points.geojson  （监测点矢量图层）
  - data/campus_boundary.geojson    （校园边界矢量图层）
  - data/weekly_data.csv            （时序属性数据）
"""

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon

from config import HOURS, DAYS, CAMPUS_BOUNDARY, CRS

np.random.seed(42)

# ========== 各建筑类型的时间系数曲线 ==========
TIME_PROFILES = {
    "library": {
        7: 0.2, 9: 0.5, 11: 0.7, 13: 0.6, 15: 0.8, 17: 0.9, 19: 1.2, 21: 1.3, 23: 0.1
    },
    "classroom": {
        7: 0.3, 9: 1.2, 11: 1.1, 13: 0.4, 15: 1.1, 17: 0.9, 19: 0.3, 21: 0.1, 23: 0.05
    },
    "canteen": {
        7: 0.8, 9: 0.1, 11: 1.4, 13: 0.3, 15: 0.1, 17: 1.3, 19: 0.5, 21: 0.1, 23: 0.05
    },
    "dorm": {
        7: 0.6, 9: 0.3, 11: 0.2, 13: 0.5, 15: 0.2, 17: 0.4, 19: 0.8, 21: 1.2, 23: 1.3
    },
    "sports": {
        7: 0.3, 9: 0.4, 11: 0.3, 13: 0.2, 15: 0.5, 17: 1.3, 19: 1.1, 21: 0.5, 23: 0.1
    },
    "admin": {
        7: 0.1, 9: 0.8, 11: 0.9, 13: 0.6, 15: 0.9, 17: 0.7, 19: 0.1, 21: 0.05, 23: 0.05
    },
    "gate": {
        7: 1.0, 9: 0.6, 11: 0.9, 13: 0.5, 15: 0.6, 17: 1.1, 19: 0.7, 21: 0.3, 23: 0.1
    },
}

# ========== 星期系数 ==========
WEEKDAY_FACTORS = {
    "library":   {"weekday": 1.0, "weekend": 0.6},
    "classroom": {"weekday": 1.0, "weekend": 0.15},
    "canteen":   {"weekday": 1.0, "weekend": 0.8},
    "dorm":      {"weekday": 1.0, "weekend": 1.3},
    "sports":    {"weekday": 1.0, "weekend": 1.4},
    "admin":     {"weekday": 1.0, "weekend": 0.1},
    "gate":      {"weekday": 1.0, "weekend": 0.5},
}


def generate_boundary_geojson():
    """生成校园边界 GeoJSON（面要素图层）。"""
    coords = [(lng, lat) for lat, lng in CAMPUS_BOUNDARY]
    polygon = Polygon(coords)
    gdf = gpd.GeoDataFrame(
        [{"name": "CUIT航空港校区", "type": "campus_boundary"}],
        geometry=[polygon],
        crs=CRS,
    )
    path = "data/campus_boundary.geojson"
    gdf.to_file(path, driver="GeoJSON")
    print(f"校园边界 → {path}")
    return gdf


def generate_points_geojson():
    """
    读取 CSV 监测点，转换为 GeoDataFrame 并输出 GeoJSON。
    体现 GIS 中"属性数据 → 矢量要素"的转换过程。
    """
    df = pd.read_csv("data/monitoring_points.csv")
    geometry = [Point(row.lng, row.lat) for _, row in df.iterrows()]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=CRS)

    path = "data/monitoring_points.geojson"
    gdf.to_file(path, driver="GeoJSON")
    print(f"监测点图层（{len(gdf)} 个要素） → {path}")
    return gdf


def generate_weekly_data(points_gdf):
    """基于正态分布 + 时间规律模板生成一周时序数据。"""
    records = []

    for _, row in points_gdf.iterrows():
        btype = row["type"]
        time_profile = TIME_PROFILES[btype]
        wf = WEEKDAY_FACTORS[btype]

        for day_idx, day_name in enumerate(DAYS):
            is_weekend = day_idx >= 5
            wd_factor = wf["weekend"] if is_weekend else wf["weekday"]

            for hour in HOURS:
                tf = time_profile[hour]

                noise = row["base_noise_db"] * tf * wd_factor
                noise += np.random.normal(0, row["base_noise_db"] * 0.08)
                noise = np.clip(noise, 25, 95)

                crowd = row["base_crowd"] * tf * wd_factor
                crowd += np.random.normal(0, row["base_crowd"] * 0.10)
                crowd = np.clip(crowd, 0, 10)

                records.append({
                    "id": row["id"],
                    "name": row["name"],
                    "type": btype,
                    "lat": row["lat"],
                    "lng": row["lng"],
                    "day": day_name,
                    "day_idx": day_idx,
                    "hour": hour,
                    "noise_db": round(noise, 1),
                    "crowd_level": round(crowd, 1),
                })

    df = pd.DataFrame(records)
    path = "data/weekly_data.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"时序数据（{len(df)} 条） → {path}")
    return df


def main():
    print("=" * 50)
    print("生成 GIS 矢量数据图层 + 模拟时序数据")
    print("=" * 50)

    generate_boundary_geojson()
    gdf = generate_points_geojson()
    generate_weekly_data(gdf)

    print("\n所有数据生成完毕！")
    print("GeoJSON 文件可直接在 QGIS/ArcGIS 中打开查看。")


if __name__ == "__main__":
    main()
