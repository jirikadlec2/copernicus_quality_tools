#!/usr/bin/env python3


import json
from pathlib import Path
from unittest import TestCase
from uuid import uuid4

from qc_tool.common import TEST_DATA_DIR
from qc_tool.test.helper import ProductTestCase
from qc_tool.wps.dispatch import dispatch
from qc_tool.wps.registry import load_all_check_functions


class Test_fty_YYYY_020m(TestCase):
    def setUp(self):
        super().setUp()
        load_all_check_functions()

    def test_run(self):
        filepath = TEST_DATA_DIR.joinpath("raster", "fty", "fty_2015_020m_si_03035_d04_test.tif.zip")
        job_status = dispatch(str(uuid4()), "user_name", filepath, "fty_YYYY_020m", ["r2", "r3", "r4", "r5"])
        self.assertEqual("r1", job_status["checks"][1]["check_ident"])
        self.assertEqual("ok", job_status["checks"][1]["status"],
                         "Slovenia test file should pass check for the product fty_YYYY_020m.")

    def test_bad_extension(self):
        filepath = TEST_DATA_DIR.joinpath("vector", "clc", "clc2012_mt.gdb.zip")
        job_status = dispatch(str(uuid4()), "user_name", filepath, "fty_YYYY_020m", [])
        self.assertEqual("r_unzip", job_status["checks"][0]["check_ident"])
        self.assertEqual("aborted", job_status["checks"][0]["status"])


class Test_clc(TestCase):
    def setUp(self):
        super().setUp()
        load_all_check_functions()

    def test_malta(self):
        filepath = TEST_DATA_DIR.joinpath("vector", "clc", "clc2012_mt.gdb.zip")
        job_status = dispatch(str(uuid4()), "user_name", filepath, "clc", [])
        self.assertEqual("change.v2", job_status["checks"][2]["check_ident"])
        self.assertEqual("ok", job_status["checks"][2]["status"],
                         "Malta should pass the checks for the product clc.status.")

    def test_malta_all_ok(self):
        filepath = TEST_DATA_DIR.joinpath("vector", "clc", "clc2012_mt.gdb.zip")
        job_status = dispatch(str(uuid4()),
                              "user_name",
                              filepath,
                              "clc",
                              ["status.v5", "status.v6", "status.v8", "status.v11", "status.v13", "status.v14",
                               "change.v5", "change.v6", "change.v8", "change.v11", "change.v13", "change.v14"])

        statuses_ok = [check for check in job_status["checks"] if check["status"] == "ok"]
        checks_not_ok = [check["check_ident"] for check in job_status["checks"] if check["status"] != "ok"]

        self.assertEqual(len(statuses_ok), len(job_status["checks"]),
                         "Checks {:s} do not have status ok.".format(",".join(checks_not_ok)))


class Test_clc_status(TestCase):
    def setUp(self):
        super().setUp()
        load_all_check_functions()

    def test_status_json(self):
        filepath = TEST_DATA_DIR.joinpath("vector", "clc", "clc2012_mt.gdb.zip")
        job_uuid = uuid4().hex
        status_filepath = Path("/mnt/qc_tool_volume/work/").joinpath("job_{:s}".format(job_uuid), "status.json")
        job_status = dispatch(job_uuid, "user_name", filepath, "clc", [])
        self.assertTrue(status_filepath.exists())
        job_status_from_file = status_filepath.read_text()
        job_status_from_file = json.loads(job_status_from_file)
        self.assertEqual(job_status, job_status_from_file,
                         "Job status returned by dispatch() must be the same as stored in status.json file.")


class Test_ua_shp(ProductTestCase):
    def setUp(self):
        super().setUp()
        load_all_check_functions()
        self.filepath = TEST_DATA_DIR.joinpath("vector", "ua_shp", "EE003L0_NARVA.shp.zip")

    def test_run(self):

        job_status = dispatch(str(uuid4()),
                              "user_name",
                              self.filepath,
                              "ua",
                              ["status.v5", "status.v6", "status.v8", "status.v11_ua", "status.v13", "status.v14"])
        statuses_ok = [check for check in job_status["checks"] if check["status"] == "ok"]
        checks_not_ok = [check for check in job_status["checks"] if check["status"] != "ok"]
        check_idents_not_ok = [check["check_ident"] for check in checks_not_ok]

        for check in checks_not_ok:
            print(check["check_ident"])
            print(check["messages"])

        self.assertEqual(len(statuses_ok), len(job_status["checks"]),
                         "Checks {:s} do not have status ok.".format(",".join(check_idents_not_ok)))


class Test_ua_gdb(ProductTestCase):
    def setUp(self):
        super().setUp()
        load_all_check_functions()
        # FIXME:
        # Klagenfurt test zip should be removed while it fails in some checks.
        # The new test zip should pass all checks with ok status.
        self.filepath = TEST_DATA_DIR.joinpath("vector", "ua_gdb", "AT006L1_KLAGENFURT.zip")

    def test_run_ok(self):
        expected_check_statuses = {"v_unzip": "ok",
                                   "boundary.v1_ua": "ok",
                                   "boundary.v2": "ok",
                                   "boundary.v3": "ok",
                                   "boundary.v4": "ok",
                                   "boundary.v_import2pg": "ok",
                                   "status.v1_ua": "ok",
                                   "status.v2": "ok",
                                   "status.v3": "ok",
                                   "status.v4": "ok",
                                   "status.v_import2pg": "ok",
                                   "status.v5": "ok",
                                   "status.v6": "ok",
                                   "status.v8": "ok",
                                   "status.v11_ua": "failed",
                                   "status.v13": "failed",
                                   "status.v14": "failed"}
        job_status = dispatch(str(uuid4()),
                              "user_name",
                              self.filepath,
                              "ua",
                              ["status.v5", "status.v6", "status.v8", "status.v11_ua", "status.v13", "status.v14"])
        check_statuses = dict((check_status["check_ident"], check_status["status"])
                              for check_status in job_status["checks"])
        self.assertDictEqual(expected_check_statuses, check_statuses)


class Test_update_status(ProductTestCase):
    def setUp(self):
        super().setUp()
        load_all_check_functions()

    def test_run(self):
        def my_update(check_ident, percent_done):
            pass
        filepath = TEST_DATA_DIR.joinpath("vector", "clc", "clc2012_mt.gdb.zip")
        dispatch(str(uuid4()),
                 "user_name",
                 filepath,
                 "clc",
                 ["status.v5", "status.v6", "status.v8", "status.v11", "status.v13", "status.v14",
                  "change.v5", "change.v6", "change.v8", "change.v11", "change.v13", "change.v14"],
                 update_status_func=my_update)
