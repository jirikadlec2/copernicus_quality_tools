#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from zipfile import ZipFile

from qc_tool.wps.registry import register_check_function


@register_check_function(__name__)
def run_check(params):
    zip_filepath = params["filepath"]
    extract_dir = params["tmp_dir"].joinpath("r_unzip")
    extract_dir.mkdir()
    
    # Unzip the source zip file.
    try:
        with ZipFile(str(zip_filepath)) as zip_file:
            zip_file.extractall(path=str(extract_dir))
    except Exception as ex:
        return {"status": "aborted",
                "message": "Error unzipping file {:s}.".format(zip_filepath.filename)}

    # Find tif file.
    tif_filepaths = [path for path in list(extract_dir.glob("**/*")) if path.name.lower().endswith(".tif")]
    if len(tif_filepaths) != 1 or not tif_filepaths[0].is_file():
        return {"status": "aborted",
                "message": "There must be exactly one .tif file in the zip file. "
                           "Found {:d} .tif files.".format(len(tif_filepaths))}

    return {"status": "ok",
            "params": {"filepath": tif_filepaths[0]}}
