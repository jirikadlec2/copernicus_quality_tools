#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Raster origin check.
"""

import gdal
from pathlib import Path

from qc_tool.wps.registry import register_check_function

@register_check_function(__name__, "Raster origin check.")
def run_check(filepath, params):
    """
    Raster origin check.
    :param filepath: pathname to data source
    :param params: configuration
    :return: status + message
    """

    # enable gdal to use exceptions
    gdal.UseExceptions()

    try:
        ds_open = gdal.Open(filepath)
        if ds_open is None:
            return {"status": "failed",
                    "message": "The file can not be opened."}
    except:
        return {"status": "failed",
                "message": "The file can not be opened."}

    # upper-left coordinate divided by pixel-size must leave no remainder
    gt = ds_open.GetGeoTransform()
    ulx = gt[0]
    uly = gt[3]
    pixelsizex = gt[1]
    pixelsizey = gt[5]

    if ulx % pixelsizex != 0 or uly % pixelsizey != 0:
        return {"status": "failed",
                "message": "The upper-left X, Y coordinates are not divisible by pixel-size with no remainder."}

    # Pan-European layers must fit to the LEAC 1 km grid
    filename = Path(filepath).name
    if "_eu_" in filename:
        if ulx % 1000 != 0 or uly % 1000 != 0:
            return {"status": "failed",
                    "message": "The raster origin does not fit to the LEAC 1 km grid."}

    return {"status": "ok"}