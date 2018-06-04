#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Raster resolution check.
"""

import gdal

# from qc_tool.wps.registry import register_check_function
#
# @register_check_function(__name__, "Pixel size must be equal to given value.")
def run_check(filepath, params):
    """
    Raster resolution check.
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

    band_count = ds_open.RasterCount
    if band_count != 1:
        return {"status": "failed",
                "message": "The input raster data contains {:s} bands (1 band is allowed).".format(str(band_count))}

    # get raster pixel size
    gt = ds_open.GetGeoTransform()
    x_size = abs(gt[1])
    y_size = abs(gt[5])

    # verify the square shape of the pixel
    if x_size != y_size:
        return {"status": "failed",
                "message": "The pixel is not square-shaped."}

    # 
    if x_size == params["pixelsize"]:
        return {"status": "ok"}
    else:
        return {"status": "failed",
                "message": "The raster pixel size is {:s} m, {:s} m is allowed.".format(str(x_size), str(params["pixelsize"]))}


f = "/home/jiri/Plocha/COP_QC_rasterdata/WAW_2015_100m_eu_03035_d02_full/WAW_2015_100m_eu_03035_d02_full.tif"
par = {"pixelsize": 20}
print(run_check(f, par))

