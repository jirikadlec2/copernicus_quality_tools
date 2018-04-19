import json
import os
import ogr
from import_file import import_file

# import check scripts
dir_this = os.path.dirname(os.path.realpath(__file__))  # parent directory of this file


def run(config_file, filename, checks):

    dir_this = os.path.dirname(os.path.realpath(__file__))

    # directory with config files
    general_config_dir = os.path.join(dir_this, 'helpers/config_files/general')

    # import helper
    helper = import_file(os.path.join(dir_this, 'helpers/helper.py'))

    # import check modules
    v1 = import_file(os.path.join(dir_this, 'common_checks/VR1.py'))
    # v2 = ...
    # v3 = ...
    v4 = import_file(os.path.join(dir_this, 'common_checks/VR4.py'))

    # -------------------------------
    # basic check of input parameters
    # -------------------------------

    # enable ogr to use exceptions
    ogr.UseExceptions()

    # check of input data source existence
    if not os.path.exists(filename):
        return {"fatal_error": {"status": "FAILED",
                                "message": "INPUT DATA SOURCE DOES NOT EXIST IN THE FILESYSTEM"}}

    # check of input data source
    try:
        fgdbopen = ogr.Open(filename)
        if fgdbopen is None:
            return {"fatal_error": {"status": "FAILED",
                                    "message": "INVALID DATA SOURCE"}}
    except:
        return {"fatal_error": {"status": "FAILED",
                                "message": "INVALID DATA SOURCE"}}

    # check for appropriate config file existence
    if not os.path.exists(config_file):
        return {"fatal_error": {"status": "FAILED",
                                "message": "APPROPRIATED CONFIG FILE DOES NOT EXIST"}}

    # load data from check config file
    with open(config_file) as cf:
        config_data = json.load(cf)

    # checking the existence of the layer in the data source
    ln_template = config_data["layer"]
    fcs_in_fgdb = list()
    for lyr in fgdbopen:
        fcs_in_fgdb.append(lyr.GetName())
    layers = [layer for layer in fcs_in_fgdb if ln_template in layer]
    if len(layers) != 1:
        return {"fata_error": {"status": "FAILED",
                               "message": "THERE IS NOT ONLY ONE MATCHING LAYER IN THE DATA SOURCE"}}
    else:
        layer = layers[0]
    lyr = None
    fgdbopen = None

    # get dict of checks and their requirement
    list_of_checks = {check_id["check_id"]: check_id["required"] for check_id in config_data["checks"][:]}

    # list of required checks for appropriate product
    list_of_required_checks = [ch for ch in list_of_checks if list_of_checks[ch] is True]

    # verify that custom checks are available for appropriate product
    custom_checks = list()
    checks = [i.lower() for i in checks]
    for ch in checks:
        if ch not in list_of_checks:
            return {"fatal_error": {"status": "FAILED",
                                    "message": "REQUIRED CHECK WITH ID: '%s' IS NOT ON THE CHECK LIST FOR THE PRODUCT: '%s'."
                                               % (ch, config_data["description"])}}
        else:
            custom_checks.append(ch)

    # list of checks to be run (custom chosen + required ones from config. file)
    list_of_checks = list(set(custom_checks + list_of_required_checks))

    # =============================================
    # ****************** CHECKS *******************
    # =============================================

    # dict with results for particular checks
    res = dict()

    # --------------------
    # request for 1. check
    # --------------------

    if "v1" in list_of_checks:

        # get config parameters for V1 check
        v1_config = [d for d in config_data["checks"] if d["check_id"] == "v1"][0]

        # load FileExtension: driver pairs from config file
        config_drivers = os.path.join(general_config_dir, 'gdal_ogr_drivers.json')
        with open(config_drivers) as drivers_data:
            drivers_load = json.load(drivers_data)

        res["v1"] = dict()
        (res["v1"]["status"], res["v1"]["message"]) = v1.run_check(v1_config, filename, drivers_load).values()

    # --------------------
    # request for 2. check
    # --------------------

    if "v2" in list_of_checks:

        # get config parameters for V2 check
        v2_config = [d for d in config_data["checks"] if d["check_id"] == "v2"][0]

        # TODO: finish file naming convention check


        # Potemkin's second check - DELETE!!!
        res["v2"] = dict()
        res["v2"]["status"] = "FAILED"
        res["v2"]["message"] = "NO CHECK WITH ID: V2 WAS FOUND"
        # Potemkin's second check - DELETE!!!

    # --------------------
    # request for 3. check
    # --------------------

    if "v3" in list_of_checks:

        # get config parameters for V3 check
        v3_config = [d for d in config_data["checks"] if d["check_id"] == "v3"][0]

        # TODO: finish file naming convention check

        # Potemkin's third check - DELETE!!!
        res["v3"] = dict()
        res["v3"]["status"] = "FAILED"
        res["v3"]["message"] = "NO CHECK WITH ID: V2 WAS FOUND"
        # Potemkin's third check - DELETE!!!

    # --------------------
    # request for 4. check
    # --------------------

    if "v4" in list_of_checks:

        # get config paramers for V4 check
        v4_config = [d for d in config_data["checks"] if d["check_id"] == "v4"][0]
        res["v4"] = dict()
        (res["v4"]["status"], res["v4"]["message"]) = v4.run_check(v4_config, filename, "v", layer).values()

    # ---------------------
    # request for 11. check
    # ---------------------

    # TODO: add MMU check

    return res


print run("/home/jtomicek/GISAT/GitHub/copernicus_quality_tools/check_scripts/helpers/config_files/vector/clc_chaYY.json",
          "/home/jtomicek/GISAT/GitHub/copernicus_quality_tools/testing_data/clc2012_mt.gdb",
          ["v1", "v2", "v4"])
