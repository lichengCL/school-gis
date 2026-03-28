# -*- coding: utf-8 -*-
"""
IDW（反距离权重）空间插值 + GeoTIFF 栅格输出。

GIS 核心概念：
- 矢量 → 栅格转换（点插值生成连续栅格面）
- 空间插值（IDW）
- 栅格掩膜（Mask）裁剪
"""

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from shapely.geometry import Point, Polygon

from config import CAMPUS_BOUNDS, CAMPUS_BOUNDARY, GRID_RESOLUTION, IDW_POWER, CRS

# 校园边界多边形
_campus_poly = Polygon([(lng, lat) for lat, lng in CAMPUS_BOUNDARY])


def idw_interpolate(points, values, grid_lats, grid_lngs, power=IDW_POWER):
    """
    IDW 空间插值。

    Parameters:
        points:    已知点坐标 array, shape (n, 2) -> [lat, lng]
        values:    已知点的值 array, shape (n,)
        grid_lats: 网格纬度 1D array
        grid_lngs: 网格经度 1D array
        power:     距离幂次

    Returns:
        grid_values: 插值结果 2D array, shape (len(grid_lats), len(grid_lngs))
        mask:        校园边界掩膜 2D bool array, True=校园内
    """
    grid_lat_mesh, grid_lng_mesh = np.meshgrid(grid_lats, grid_lngs, indexing="ij")
    grid_values = np.zeros_like(grid_lat_mesh)
    mask = np.zeros_like(grid_lat_mesh, dtype=bool)

    for i in range(grid_lat_mesh.shape[0]):
        for j in range(grid_lat_mesh.shape[1]):
            lat_i, lng_j = grid_lat_mesh[i, j], grid_lng_mesh[i, j]

            # 掩膜：只对校园边界内的点做插值
            if not _campus_poly.contains(Point(lng_j, lat_i)):
                continue

            mask[i, j] = True
            target = np.array([lat_i, lng_j])
            distances = np.sqrt(np.sum((points - target) ** 2, axis=1))

            zero_mask = distances < 1e-10
            if np.any(zero_mask):
                grid_values[i, j] = values[zero_mask][0]
            else:
                weights = 1.0 / (distances ** power)
                grid_values[i, j] = np.sum(weights * values) / np.sum(weights)

    # 校园外设为 NaN
    grid_values[~mask] = np.nan
    return grid_values, mask


def make_grid():
    """生成覆盖校园范围的规则网格坐标。"""
    bounds = CAMPUS_BOUNDS
    grid_lats = np.linspace(bounds["lat_min"], bounds["lat_max"], GRID_RESOLUTION)
    grid_lngs = np.linspace(bounds["lng_min"], bounds["lng_max"], GRID_RESOLUTION)
    return grid_lats, grid_lngs


def save_geotiff(grid_values, output_path, description="IDW interpolation"):
    """
    将插值结果保存为 GeoTIFF 栅格文件。

    GIS 意义：标准栅格数据格式，可在 ArcGIS/QGIS 中直接打开。
    """
    bounds = CAMPUS_BOUNDS
    height, width = grid_values.shape

    # 仿射变换：像素坐标 → 地理坐标
    transform = from_bounds(
        bounds["lng_min"], bounds["lat_min"],
        bounds["lng_max"], bounds["lat_max"],
        width, height,
    )

    # 将 NaN 替换为 nodata 值
    nodata = -9999.0
    data = grid_values.copy()
    data[np.isnan(data)] = nodata

    with rasterio.open(
        output_path, "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float32",
        crs=CRS,
        transform=transform,
        nodata=nodata,
    ) as dst:
        # 注意：GeoTIFF 行序是从北到南（纬度递减），需要翻转
        dst.write(data[::-1].astype("float32"), 1)
        dst.update_tags(DESCRIPTION=description)

    return output_path
