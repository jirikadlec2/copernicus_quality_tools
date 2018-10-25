#!/usr/bin/env python3


import json
from pathlib import Path
from unittest import TestCase
from uuid import uuid4

from qc_tool.common import TEST_DATA_DIR
from qc_tool.common import compose_attachment_filepath
from qc_tool.test.helper import ProductTestCase
from qc_tool.wps.dispatch import dispatch
from qc_tool.wps.registry import load_all_check_functions


class Test_clc(TestCase):
    def setUp(self):
        super().setUp()
        load_all_check_functions()
        from qc_tool.common import CONFIG
        CONFIG["boundary_dir"] = TEST_DATA_DIR.joinpath("boundary")

    def test(self):
        filepath = TEST_DATA_DIR.joinpath("vector", "clc", "clc2012_mt.gdb.zip")
        job_status = dispatch(str(uuid4()),
                              "user_name",
                              filepath,
                              "clc",
                              ["v5",
                               "status.v6",
                               "change.v6",
                               "v8",
                               "status.v11",
                               "change.v11",
                               "v13",
                               "status.v14",
                               "change.v14"])

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
        # FIXME:
        # Narva test zip should be removed while it fails in some checks.
        # The new test zip should pass all checks with ok status.
        self.filepath = TEST_DATA_DIR.joinpath("vector", "ua_shp", "EE003L0_NARVA.shp.zip")

    def test(self):
        expected_check_statuses = {"v_unzip": "ok",
                                   "v1_ua": "ok",
                                   "v2": "ok",
                                   "reference.v3": "ok",
                                   "boundary.v3": "ok",
                                   "v4": "ok",
                                   "v_import2pg": "ok",
                                   "v5": "ok",
                                   "v6": "ok",
                                   "v8": "ok",
                                   "v11_ua": "failed",
                                   "v13": "ok",
                                   "v14": "ok"}
        job_status = dispatch(str(uuid4()),
                              "user_name",
                              self.filepath,
                              "ua",
                              ["v5", "v6", "v8", "v11_ua", "v13", "v14"])
        check_statuses = dict((check_status["check_ident"], check_status["status"])
                              for check_status in job_status["checks"])
        self.assertDictEqual(expected_check_statuses, check_statuses)


class Test_ua_gdb(ProductTestCase):
    def setUp(self):
        super().setUp()
        load_all_check_functions()

    def test_klagenfurt(self):
        # FIXME:
        # Klagenfurt test zip should be removed while it fails in some checks.
        # The new test zip should pass all checks with ok status.
        filepath = TEST_DATA_DIR.joinpath("vector", "ua_gdb", "AT006L1_KLAGENFURT.zip")
        expected_check_statuses = {"v_unzip": "ok",
                                   "v1_ua": "ok",
                                   "v2": "ok",
                                   "reference.v3": "ok",
                                   "boundary.v3": "ok",
                                   "v4": "ok",
                                   "v_import2pg": "ok",
                                   "v5": "ok",
                                   "v6": "ok",
                                   "v8": "ok",
                                   "v11_ua": "failed",
                                   "v13": "failed",
                                   "v14": "ok"}
        job_status = dispatch(str(uuid4()),
                              "user_name",
                              filepath,
                              "ua",
                              ["v5", "v6", "v8", "v11_ua", "v13", "v14"])
        check_statuses = dict((check_status["check_ident"], check_status["status"])
                              for check_status in job_status["checks"])
        self.assertDictEqual(expected_check_statuses, check_statuses)

    def test_kobenhavn(self):
        self.maxDiff = None
        filepath = TEST_DATA_DIR.joinpath("vector", "ua_gdb", "DK001L2_KOBENHAVN_clip.zip")
        expected_check_statuses = {"v_unzip": "ok",
                                   "v1_ua": "ok",
                                   "v2": "ok",
                                   "reference.v3": "ok",
                                   "boundary.v3": "ok",
                                   "combined.v3": "ok",
                                   "revised.v3": "ok",
                                   "change.v3": "ok",
                                   "v4": "ok",
                                   "v_import2pg": "ok",
                                   "v5": "ok",
                                   "reference.v6": "ok",
                                   "combined.v6": "ok",
                                   "revised.v6": "ok",
                                   "change.v6": "ok",
                                   "v8": "ok",
                                   "reference.v11_ua": "ok",
                                   "combined.v11_ua": "ok",
                                   "revised.v11_ua": "ok",
                                   "change.v11_ua": "ok",
                                   "v13": "ok",
                                   "reference.v14": "ok",
                                   "combined.v14": "ok",
                                   "revised.v14": "ok",
                                   "change.v14": "ok"}
        job_status = dispatch(str(uuid4()),
                              "user_name",
                              filepath,
                              "ua_with_change",
                              ["v5",
                               "reference.v6",
                               "combined.v6",
                               "revised.v6",
                               "change.v6",
                               "v8",
                               "reference.v11_ua",
                               "combined.v11_ua",
                               "revised.v11_ua",
                               "change.v11_ua",
                               "v13",
                               "reference.v14",
                               "combined.v14",
                               "revised.v14",
                               "change.v14"])
        check_statuses = dict((check_status["check_ident"], check_status["status"])
                              for check_status in job_status["checks"])
        self.assertDictEqual(expected_check_statuses, check_statuses)


class Test_dump_error_table(ProductTestCase):
    def setUp(self):
        super().setUp()
        load_all_check_functions()

    def test(self):
        filepath = TEST_DATA_DIR.joinpath("vector", "ua_gdb", "AT006L1_KLAGENFURT.zip")
        expected_check_statuses = {"v_unzip": "ok",
                                   "v1_ua": "ok",
                                   "v2": "ok",
                                   "boundary.v3": "ok",
                                   "reference.v3": "ok",
                                   "v4": "ok",
                                   "v_import2pg": "ok",
                                   "v5": "skipped",
                                   "v6": "skipped",
                                   "v8": "skipped",
                                   "v11_ua": "skipped",
                                   "v13": "failed",
                                   "v14": "skipped"}
        job_status = dispatch(str(uuid4()),
                              "user_name",
                              filepath,
                              "ua",
                              ["v13"])
        check_statuses = dict((check_status["check_ident"], check_status["status"]) for check_status in job_status["checks"])
        self.assertDictEqual(expected_check_statuses, check_statuses)
        zip_filepath = compose_attachment_filepath(job_status["job_uuid"], "v13_at006l1_klagenfurt_ua2012_error.zip")
        self.assertTrue(zip_filepath.is_file())
