#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File format check.
"""


from osgeo import gdal

from qc_tool.wps.registry import register_check_function


@register_check_function(__name__)
def run_check(params):
    """
    File format check.
    :param params: configuration
    :return: status + message
    """

    # enable gdal to use exceptions
    gdal.UseExceptions()

    # file extension check
    ds_extension = params["filepath"].suffix
    if ds_extension not in params["formats"]:
        return {"status": "aborted",
                "message": "The source file has forbidden extension: {:s}.".format(ds_extension)}

    # try to open file with ogr drivers
    if ds_extension in params["drivers"]:
        try:
            ds_open = gdal.Open(str(params["filepath"]))
            if ds_open is None:
                return {"status": "aborted",
                        "message": "The source file can not be opened."}
        except:
            return {"status": "aborted",
                    "message": "The source file can not be opened."}

        # check file format
        drivername = ds_open.GetDriver().ShortName
        if drivername == params["drivers"][ds_extension]:
            return {"status": "ok"}
        else:
            return {"status": "aborted",
                    "message": "The file format is invalid."}
    else:
        return {"status": "aborted",
                "message": "The source file has forbidden extension: {:s}".format(ds_extension)}
