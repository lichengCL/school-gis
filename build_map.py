# -*- coding: utf-8 -*-
"""
主程序：读取 GIS 矢量数据 → IDW 空间插值 → 输出 GeoTIFF 栅格 + Folium 交互式热力图。

GIS 工作流：
1. 读取矢量点图层（GeoJSON）和属性数据（CSV）
2. 对每个时间切片做 IDW 空间插值（矢量→栅格转换）
3. 用校园边界多边形做掩膜裁剪（Mask Extract）
4. 输出 GeoTIFF 栅格（可在 ArcGIS/QGIS 中打开）
5. 生成 Folium 交互式 Web 地图

运行: python build_map.py
输出:
  - output/raster/noise_周一_07.tif  （各时间切片的 GeoTIFF 栅格）
  - output/campus_heatmap.html       （交互式热力图）
"""

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import HeatMapWithTime

from config import (
    AMAP_TILE_URL, AMAP_TILE_ATTR, CAMPUS_CENTER, MAP_ZOOM,
    CAMPUS_BOUNDS, CAMPUS_BOUNDARY, GRID_RESOLUTION, HOURS, DAYS, CRS,
)
from idw import idw_interpolate, make_grid, save_geotiff


def build_heatmap_data(df, metric="noise_db", export_tiff=True):
    """
    对每个时间切片做 IDW 插值。

    Returns:
        heat_data:   HeatMapWithTime 所需的数据
        time_labels: 时间标签列表
    """
    grid_lats, grid_lngs = make_grid()

    os.makedirs("output/raster", exist_ok=True)

    heat_data = []
    time_labels = []

    for day_idx in range(7):
        for hour in HOURS:
            subset = df[(df["day_idx"] == day_idx) & (df["hour"] == hour)]
            if subset.empty:
                continue

            points = subset[["lat", "lng"]].values
            values = subset[metric].values

            # IDW 插值（含边界掩膜）
            grid_values, mask = idw_interpolate(points, values, grid_lats, grid_lngs)

            label = f"{DAYS[day_idx]} {hour:02d}:00"

            # 导出 GeoTIFF 栅格
            if export_tiff:
                tiff_name = f"output/raster/{metric}_{DAYS[day_idx]}_{hour:02d}.tif"
                save_geotiff(grid_values, tiff_name, description=f"{metric} - {label}")

            # 归一化用于热力图
            valid = grid_values[mask]
            if len(valid) == 0:
                heat_data.append([])
                time_labels.append(label)
                continue

            v_min, v_max = valid.min(), valid.max()
            if v_max > v_min:
                grid_norm = (grid_values - v_min) / (v_max - v_min)
            else:
                grid_norm = np.zeros_like(grid_values)

            frame = []
            for i in range(len(grid_lats)):
                for j in range(len(grid_lngs)):
                    if mask[i, j]:
                        w = float(grid_norm[i, j])
                        if w > 0.05:
                            frame.append([float(grid_lats[i]), float(grid_lngs[j]), w])

            heat_data.append(frame)
            time_labels.append(label)

    return heat_data, time_labels


def create_map(heat_data_noise, time_labels, points_gdf, df):
    """创建 Folium 地图。"""
    m = folium.Map(location=CAMPUS_CENTER, zoom_start=MAP_ZOOM, tiles=None)

    # 高德底图
    folium.TileLayer(
        tiles=AMAP_TILE_URL, attr=AMAP_TILE_ATTR, name="高德地图",
    ).add_to(m)

    # --- 校园边界（从 GeoJSON 加载） ---
    boundary_gdf = gpd.read_file("data/campus_boundary.geojson")
    boundary_layer = folium.FeatureGroup(name="🏫 校园边界", show=True)
    folium.GeoJson(
        boundary_gdf.to_json(),
        style_function=lambda x: {
            "color": "#2c3e50", "weight": 2.5,
            "fillOpacity": 0, "dashArray": "8, 4",
        },
        name="校园边界",
    ).add_to(boundary_layer)
    boundary_layer.add_to(m)

    # --- 噪音热力图（时间轴） ---
    noise_layer = folium.FeatureGroup(name="🔊 噪音分贝热力图", show=True)
    HeatMapWithTime(
        data=heat_data_noise,
        index=time_labels,
        radius=25,
        blur=20,
        min_opacity=0.3,
        max_opacity=0.8,
        gradient={0.2: "#00ff00", 0.5: "#ffff00", 0.8: "#ff8800", 1.0: "#ff0000"},
        auto_play=True,
        speed_step=0.5,
        position="bottomleft",
    ).add_to(noise_layer)
    noise_layer.add_to(m)

    # --- 监测点标记（从 GeoJSON 加载） ---
    marker_layer = folium.FeatureGroup(name="📍 监测点", show=True)
    point_stats = df.groupby("id").agg({
        "name": "first", "type": "first", "lat": "first", "lng": "first",
        "noise_db": "mean", "crowd_level": "mean",
    }).reset_index()

    type_icons = {
        "library": ("book", "blue"),
        "classroom": ("graduation-cap", "darkblue"),
        "canteen": ("cutlery", "orange"),
        "dorm": ("home", "purple"),
        "sports": ("futbol-o", "green"),
        "admin": ("building", "gray"),
        "gate": ("road", "red"),
    }

    for _, row in point_stats.iterrows():
        icon_name, icon_color = type_icons.get(row["type"], ("info-sign", "blue"))
        popup_html = (
            f"<b>{row['name']}</b><br>"
            f"类型: {row['type']}<br>"
            f"平均噪音: {row['noise_db']:.1f} dB<br>"
            f"平均人流: {row['crowd_level']:.1f}/10"
        )
        folium.Marker(
            location=[row["lat"], row["lng"]],
            popup=folium.Popup(popup_html, max_width=200),
            icon=folium.Icon(color=icon_color, icon=icon_name, prefix="fa"),
        ).add_to(marker_layer)
    marker_layer.add_to(m)

    # 图层控制
    folium.LayerControl(collapsed=False).add_to(m)

    # 标题
    title_html = """
    <div style="position:fixed; top:10px; left:50%; transform:translateX(-50%);
                z-index:9999; background:rgba(255,255,255,0.9); padding:10px 24px;
                border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.2);
                font-family:'Microsoft YaHei',sans-serif;">
        <h3 style="margin:0; color:#333;">🎓 CUIT 校园"噪音与卷度"时空分布热力图</h3>
        <p style="margin:4px 0 0; font-size:12px; color:#666;">
            基于 IDW 空间插值 | 拖动时间轴查看动态变化 | 绿色=安静 → 红色=嘈杂
        </p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    # 图例
    legend_html = """
    <div style="position:fixed; bottom:50px; right:20px; z-index:9999;
                background:rgba(255,255,255,0.9); padding:12px 16px;
                border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.2);
                font-family:'Microsoft YaHei',sans-serif; font-size:13px;">
        <b>噪音等级</b><br>
        <span style="color:#00ff00;">■</span> &lt;35 dB 安静<br>
        <span style="color:#ffff00;">■</span> 35-55 dB 一般<br>
        <span style="color:#ff8800;">■</span> 55-70 dB 较吵<br>
        <span style="color:#ff0000;">■</span> &gt;70 dB 嘈杂
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m


def main():
    print("=" * 50)
    print("GIS 空间分析流水线")
    print("=" * 50)

    # 1. 读取矢量数据
    print("\n[1/4] 读取 GIS 矢量图层...")
    points_gdf = gpd.read_file("data/monitoring_points.geojson")
    print(f"  监测点图层: {len(points_gdf)} 个要素, CRS={points_gdf.crs}")

    boundary_gdf = gpd.read_file("data/campus_boundary.geojson")
    print(f"  校园边界图层: {len(boundary_gdf)} 个要素, CRS={boundary_gdf.crs}")

    # 2. 读取时序数据
    print("\n[2/4] 读取时序属性数据...")
    df = pd.read_csv("data/weekly_data.csv")
    print(f"  共 {len(df)} 条记录")

    # 3. IDW 插值 + GeoTIFF 输出
    print(f"\n[3/4] IDW 空间插值（{GRID_RESOLUTION}×{GRID_RESOLUTION} 网格, p={2}）...")
    print("  同时导出 GeoTIFF 栅格到 output/raster/")
    heat_data_noise, time_labels = build_heatmap_data(df, metric="noise_db", export_tiff=True)
    print(f"  生成 {len(time_labels)} 个时间切片栅格")

    # 4. 生成交互式地图
    print("\n[4/4] 生成 Folium 交互式地图...")
    m = create_map(heat_data_noise, time_labels, points_gdf, df)

    output_path = "output/campus_heatmap.html"
    m.save(output_path)
    print(f"\n{'=' * 50}")
    print(f"交互式地图 → {output_path}")
    print(f"GeoTIFF 栅格 → output/raster/ （可在 QGIS/ArcGIS 中打开）")
    print(f"矢量图层 → data/*.geojson （可在 QGIS/ArcGIS 中打开）")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
