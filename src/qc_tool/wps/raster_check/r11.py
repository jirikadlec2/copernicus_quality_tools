#! /usr/bin/env python3
# -*- coding: utf-8 -*-


import subprocess

from osgeo import ogr
from qc_tool.wps.registry import register_check_function

@register_check_function(__name__)
def run_check(params, status):
    lessmmu_shp_path = params["output_dir"].joinpath("lessmmu_areas.shp")

    GRASS_VERSION = "grass72"

    # (1) create a new GRASS location named "location" in the job directory
    location_path = params["tmp_dir"].joinpath("location")
    p1 = subprocess.run([GRASS_VERSION,
             "-c",
             str(params["filepath"]),
             "-e",
             str(location_path)], check=True)
    if p1.returncode != 0:
        status.add_message("GRASS GIS error: cannot create location!")
        return

    # (2) import the data into a GRASS mapset named PERMANENT
    mapset_path = location_path.joinpath("PERMANENT")
    p2 = subprocess.run([GRASS_VERSION,
            str(mapset_path),
            "--exec",
            "r.external",
            "input={:s}".format(str(params["filepath"])),
            "output=srcfile"], check=True)
    if p2.returncode != 0:
        status.add_message("GRASS GIS error: cannot import raster from {:s}".format(params["filepath"].name))
        return

    # (2a) run r.reclass in case of groupcodes parameter.
    # this option is to reclassify codes belonging to a group (for example, decidous and conifer forest -> forest)
    reclass_raster = "srcfile"
    if "groupcodes" in params:
        # creating a reclass rule file.
        # each line of the file has entries like:
        # code_0 code_1 code_2 = new_code0
        # code_3 code_4 = new_code3
        rules_filepath = params["output_dir"].joinpath("rules.txt")
        with rules_filepath.open(mode='w') as f:
            for group in params["groupcodes"]:
                original_codes = [str(code) for code in group]
                new_code = original_codes[0]
                reclass_rule = " ".join(original_codes) + " = " + new_code
                f.write(reclass_rule)

        reclass_raster = "srcfile_reclass"
        p2a = subprocess.run([GRASS_VERSION,
                              str(mapset_path),
                              "--exec",
                              "r.reclass",
                              "--verbose",
                              "--overwrite",
                              "input=srcfile",
                              "output={:s}".format(reclass_raster),
                              "rules={:s}".format(str(rules_filepath)),
                              ])
        if p2a.returncode != 0:
            status.add_message("GRASS GIS error in r.reclass")
            return


    # (3) run r.reclass.area (area is already in hectares)
    # FIXME GRASS GIS reports patches with area exactly equal to params["area_m2"] as less than MMU.
    # therefore the area_m2 is reduced by half of raster pixel area before running the GRASS GIS commands.
    
    half_pixel_m2 = (20.0 * 20.0 * 0.1) # FIXME use half of actual raster pixel area.
    mmu_limit_ha = (params["area_m2"] - half_pixel_m2) / 10000

    p3 = subprocess.run([GRASS_VERSION,
              str(mapset_path),
              "--exec",
              "r.reclass.area",
              "--verbose",
              "input={:s}".format(reclass_raster),
              "output=lessmmu_raster",
              "value={:.4f}".format(mmu_limit_ha),
              "mode=lesser",
              "method=reclass"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    print(str(p3.stdout))
    if "No areas of size less than or equal to" in str(p3.stdout):
        return

    elif p3.returncode != 0:
        status.add_message("GRASS GIS error in r.reclass.area")
        return

    # (4) run r.to.vect: convert clumps with mmu < mmu_limit_ha to polygon areas
    p4 = subprocess.run([GRASS_VERSION,
              str(mapset_path),
              "--exec",
              "r.to.vect",
              "--overwrite",
              "--verbose",
              "-s",
              "-v",
              "type=area",
              "input=lessmmu_raster",
              "output=lessmmu_areas"],
             check=True)
    if p4.returncode != 0:
        status.add_message("GRASS GIS error in r.to.vect")
        return

    # (5) export lessmmu_areas to shapefile
    p5 = subprocess.run([GRASS_VERSION,
              str(mapset_path),
              "--exec",
              "v.out.ogr",
              "input=lessmmu_areas",
              "output={:s}".format(str(lessmmu_shp_path)),
              "format=ESRI_Shapefile"],
             check=True)
    if p5.returncode != 0:
        status.add_message("GRASS GIS error in executing v.out.ogr")
        return

    if not lessmmu_shp_path.exists():
        status.add_message("GRASS GIS error. exported lessmmu_areas shapefile {:s} does not exist.".format(str(lessmmu_shp_path)))
        return

    ogr.UseExceptions()
    try:
        ds_lessmmu = ogr.Open(str(lessmmu_shp_path))
        if ds_lessmmu is None:
            status.add_message("GRASS GIS error or OGR error. The file {:s} can not be opened.".format(str(lessmmu_shp_path)))
            return
    except BaseException as e:
        status.add_message("GRASS GIS error or OGR error."
                           " The shapefile {:s} cannot be opened."
                           " Exception: {:s}".format(str(lessmmu_shp_path), str(e)))
        return

    lyr = ds_lessmmu.GetLayer()
    lessmmu_count = lyr.GetFeatureCount()

    if lessmmu_count == 0:
        return
    else:
        status.add_message("The data source has {:d} objects under MMU limit of {:f} ha."
                           .format(lessmmu_count, params["area_m2"] / 10000))
        return
