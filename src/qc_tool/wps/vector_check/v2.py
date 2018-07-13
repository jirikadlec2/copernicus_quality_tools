#! /usr/bin/env python3
# -*- coding: utf-8 -*-


from osgeo import ogr

from qc_tool.wps.registry import register_check_function


@register_check_function(__name__)
def run_check(params, status):
    # enable ogr to use exceptions
    ogr.UseExceptions()

    filepaths = [layer_filepath for (layer_name, layer_filepath) in params["layer_sources"]]
    filepaths = set(filepaths)
    for filepath in filepaths:
        ds_extension = filepath.suffix
        if (ds_extension not in params["formats"]
            or ds_extension not in params["drivers"]):
            status.aborted()
            status.add_message("The source file has forbidden extension: {:s}".format(ds_extension))
        else:
            ds_open = None
            try:
                ds_open = ogr.Open(str(filepath))
            except:
                pass
            if ds_open is None:
                status.aborted()
                status.add_message("The source file can not be opened.")
            else:
                drivername = ds_open.GetDriver().GetName()
                if drivername != params["drivers"][ds_extension]:
                    status.aborted()
                    status.add_message("The file format is invalid.")
