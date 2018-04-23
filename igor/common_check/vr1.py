#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
File format check.
"""

import json
import os

#import ogr
#import gdal

from registry import register_check_function

__author__ = "Jiri Tomicek"
__copyright__ = "Copyright 2018, GISAT s.r.o., CZ"
__email__ = "jiri.tomicek@gisat.cz"
__status__ = "testing"


@register_check_function(__name__, "Description of check function vr1.")
def run_check(filepath, params):
    """
    File format check.
    :param params: Parameters from config.json file
    :param ds: pathname to data source
    :param fj: pathname to gdal_ogr_drivers.json config file
    :return: status + message
    """
    print("run_check.filepath={:s}".format(repr(filepath)))
    print("run_check.params={:s}".format(repr(params)))

    return {"status": "ok",
            "message": "call ok."}

    # enable gdal/ogr to use exceptions
    gdal.UseExceptions()
    ogr.UseExceptions()

    # check for data source existence
    # if not os.path.exists(ds):
    #     return {"STATUS": "FAILED",
    #             "MESSAGE": "FILE DOES NOT EXIST IN FILESYSTEM"}

    # create dict of params
    p = dict()
    for d in params["parameters"]:
        p[d["name"]] = [d["value"], d["exceptions"]]

    if len(p) != 1:
        return {"STATUS": "WARNING",
                "MESSAGE": "V1/R1 CHECK TAKES EXACTLY 1 INPUT PARAMETER (%d GIVEN)" % len(p)}

    # check: data source name must end with specified extension and must be possible to open with specific driver
    allowed_extensions = p["format"][0]
    ds_extension = os.path.splitext(ds)[1]

    if ds_extension not in allowed_extensions:
        return {"STATUS": "FAILED",
                "MESSAGE": "FORBIDDEN FILE EXTENSION"}

    # in case of vector formats
    if ds_extension in drivers["ogr"]:
        try:
            ds_open = ogr.Open(ds)
        except:
            return {"STATUS": "FAILED",
                    "MESSAGE": "FILE CAN NOT BE OPENED"}

        if ds_open.GetDriver().GetName() == drivers["ogr"][ds_extension]:
            return {"STATUS": "OK",
                    "MESSAGE": "THE FILE FORMAT CHECK WAS SUCCESSFUL"}
        else:
            return {"STATUS": "FAILED",
                    "MESSAGE": "WRONG FILE FORMAT; FILE FORMAT IS: '%s'; DECLARED FILE FORMAT IS: '%s'" %
                               (ds_open.GetDriver().GetName(), drivers["ogr"][ds_extension])
                    }

    # in case of raster formats
    elif ds_extension in drivers["gdal"]:
        try:
            ds_open = gdal.Open(ds)
        except:
            return {"STATUS": "FAILED",
                    "MESSAGE": "FILE CAN NOT BE OPENED"}

        if ds_open.GetDriver().ShortName == drivers["gdal"][ds_extension]:
            return {"STATUS": "OK",
                    "MESSAGE": "THE FILE FORMAT CHECK WAS SUCCESSFUL"}
        else:
            return {"STATUS": "FAILED",
                    "MESSAGE": "WRONG FILE FORMAT;"
                               "FILE FORMAT IS: '%s'; DECLARED FILE FORMAT IS: '%s'" %
                               (ds_open.GetDriver().ShortName, drivers["gdal"][ds_extension])
                    }

    else:
        return {"STATUS": "FAILED",
                "MESSAGE": "UNKNOWN FILE EXTENSION: %s" % ds_extension}
