#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRS check.
"""


from osgeo import ogr
from osgeo import osr

from qc_tool.wps.registry import register_check_function


@register_check_function(__name__)
def run_check(params, status):
    """
    CRS check.
    :param params: configuration
    :return: status + message
    """
    # check CRS of all matching layers
    dsopen = ogr.Open(str(params["filepath"]))
    for layer_name in params["layer_names"]:
        layer = dsopen.GetLayerByName(layer_name)
        srs = osr.SpatialReference(layer.GetSpatialRef().ExportToWkt())
        if not srs.IsProjected:
            status.add_message("Layer {:s} has source data not projected.".format(layer_name))
        else:
            epsg = srs.GetAttrValue("AUTHORITY", 1)
            if epsg is None:
                status.add_message("Layer {:s} has missing EPSG authority.".format(layer_name))
            else:
                # CRS check via EPSG comparison
                if epsg not in map(str, params["epsg"]):
                    status.add_message("Layer {:s} has illegal EPSG code {:s}.".format(layer_name, str(epsg)))
