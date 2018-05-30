#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Naming convention check.
"""
import re

from pathlib import PurePath

from qc_tool.wps.registry import register_check_function
from qc_tool.wps.helper import check_name
from qc_tool.wps.vector_check.dump_gdbtable import get_fc_path

@register_check_function(__name__, "File names match file naming conventions.")
def run_check(filepath, params):
    """
    Check if string matches pattern.
    :param filepath: pathname to data source
    :param params: configuration
    :return: status + message
    """


    # check file name
    filename = PurePath(filepath).name
    filename = filename.lower()
    file_name_regex = params["file_name_regex"].replace("countrycode", params["country_codes"]).lower()
    conf = check_name(filename, file_name_regex)
    if not conf:
        return {"status": "aborted",
                "message": "File name does not conform to the naming convention."}

    # get particular country code
    cc_regex = params["file_name_regex"].replace("countrycode", "(.+?)")
    countrycode = re.search(cc_regex, filename).group(1)

    # get list of feature classes
    lyrs = get_fc_path(filepath)

    # get list of feature classes matching to the prefix and regex
    layer_prefix = params["layer_prefix"].replace("countrycode", countrycode)
    layer_regex = params["layer_regex"].replace("countrycode", countrycode).lower()
    layers_prefix = [lyr.lower() for lyr in lyrs if check_name(lyr.lower(), layer_prefix)]
    layers_regex = [layer for layer in layers_prefix if check_name(layer, layer_regex)]

    if not list(set(layers_prefix) - set(layers_regex)):
        if len(layers_regex) != int(params["layer_count"]):
            return {"status": "aborted",
                    "message": "Number of matching layers ({:d}) does not correspond with declared number of layers({:d})".format(
                        len(layers_regex), int(params["layer_count"]))}
        else:
            return {"status": "ok"}
    else:
        return {"status": "aborted",
                "message": "Number of layers matching prefix '{:s}' and number of layers matching regex '{:s}' are not equal.".format(
                    layer_prefix, layer_regex)}
