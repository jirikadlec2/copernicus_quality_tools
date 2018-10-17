#!/usr/bin/env python3

from unittest import TestCase
from uuid import uuid4

from qc_tool.common import TEST_DATA_DIR
from qc_tool.wps.dispatch import dispatch
from qc_tool.wps.registry import load_all_check_functions

class Test_Raster(TestCase):

    """
    Helper function to display messages of aborted, failed or skipped checks in
    case of test failure.
    """
    def show_messages(self, job_status):
        checks_not_ok = [check for check in job_status["checks"] if check["status"] != "ok"]
        msg = ""
        for check in checks_not_ok:
            check_ident = check["check_ident"]
            check_status = check["status"]
            check_messages = " ".join(check["messages"])
            msg += "[{:s} {:s}]: {:s}\n".format(check_ident, check_status, check_messages)
        return msg

    def setUp(self):
        super().setUp()
        load_all_check_functions()

        self.maxDiff = None
        self.raster_data_dir = TEST_DATA_DIR.joinpath("raster")
        self.username = "test_username"

        # these optional checks are present in all tested raster product definitions.
        self.check_idents = ["r2", "r3", "r4", "r5", "r6", "r7", "r8", "r9", "r10", "r14", "r15"]

    # High resolution forest type (FTY) - 20m
    def test_fty_020m(self):
        product_ident = "fty_020m"
        filepath = self.raster_data_dir.joinpath(product_ident, "fty_2015_020m_mt_03035_d04_clip.zip")
        self.check_idents.append("r11")
        job_status = dispatch(str(uuid4()), self.username, filepath, product_ident, self.check_idents)
        self.assertTrue(all([check["status"] == "ok" for check in job_status["checks"]]),
                        self.show_messages(job_status))

    # High resolution forest type (FTY) - 100m
    def test_fty_100m(self):
        product_ident = "fty_100m"
        filepath = self.raster_data_dir.joinpath(product_ident, "fty_2015_100m_mt_03035_d02_clip.zip")
        job_status = dispatch(str(uuid4()), self.username, filepath, product_ident, self.check_idents)
        self.assertTrue(all([check["status"] == "ok" for check in job_status["checks"]]),
                        self.show_messages(job_status))

    # High resolution grassland (GRA) - 20m
    def test_gra_020m(self):
        product_ident = "gra_020m"
        filepath = self.raster_data_dir.joinpath(product_ident, "GRA_2015_020m_mt_03035_V1_clip.zip")
        self.check_idents.append("r11")
        job_status = dispatch(str(uuid4()), self.username, filepath, product_ident, self.check_idents)
        self.assertTrue(all([check["status"] == "ok" for check in job_status["checks"]]),
                        self.show_messages(job_status))

    # High resolution grassland (GRA) - 100m
    def test_gra_100m(self):
        product_ident = "gra_100m"
        filepath = self.raster_data_dir.joinpath(product_ident, "GRA_2015_100m_mt_03035_V1_clip.zip")
        job_status = dispatch(str(uuid4()), self.username, filepath, product_ident, self.check_idents)
        self.assertTrue(all([check["status"] == "ok" for check in job_status["checks"]]),
                        self.show_messages(job_status))

    # High resolution imperviousness change (IMC) - 20m
    def test_imc_020m(self):
        product_ident = "imc_020m"
        filepath = self.raster_data_dir.joinpath(product_ident, "IMC_1215_020m_mt_03035_d02_clip.zip")
        job_status = dispatch(str(uuid4()), self.username, filepath, product_ident, self.check_idents)
        self.assertTrue(all([check["status"] == "ok" for check in job_status["checks"]]),
                        self.show_messages(job_status))

    # High resolution imperviousness change (IMC) - 100m
    def test_imc_100m(self):
        product_ident = "imc_100m"
        filepath = self.raster_data_dir.joinpath(product_ident, "IMC_1215_100m_mt_03035_d02_clip.zip")
        job_status = dispatch(str(uuid4()), self.username, filepath, product_ident, self.check_idents)
        self.assertTrue(all([check["status"] == "ok" for check in job_status["checks"]]),
                        self.show_messages(job_status))

    # High resolution imperviousness density (IMD) - 20m
    def test_imd_020m(self):
        product_ident = "imd_020m"
        filepath = self.raster_data_dir.joinpath(product_ident, "IMD_2015_020m_mt_03035_d04_clip.zip")
        job_status = dispatch(str(uuid4()), self.username, filepath, product_ident, self.check_idents)
        self.assertTrue(all([check["status"] == "ok" for check in job_status["checks"]]),
                        self.show_messages(job_status))

    # High resolution imperviousness density (IMD) - 100m
    def test_imd_100m(self):
        product_ident = "imd_100m"
        filepath = self.raster_data_dir.joinpath(product_ident, "IMD_2015_100m_mt_03035_d02_clip.zip")
        job_status = dispatch(str(uuid4()), self.username, filepath, product_ident, self.check_idents)
        self.assertTrue(all([check["status"] == "ok" for check in job_status["checks"]]),
                        self.show_messages(job_status))

    # High resolution tree cover density (TCD) - 20m
    def test_tcd_020m(self):
        product_ident = "tcd_020m"
        filepath = self.raster_data_dir.joinpath(product_ident, "TCD_2015_020m_mt_03035_d04_clip.zip")
        job_status = dispatch(str(uuid4()), self.username, filepath, product_ident, self.check_idents)
        self.assertTrue(all([check["status"] == "ok" for check in job_status["checks"]]),
                        self.show_messages(job_status))

    # High resolution tree cover density (TCD) - 100m
    def test_tcd_100m(self):
        product_ident = "tcd_100m"
        filepath = self.raster_data_dir.joinpath(product_ident, "TCD_2015_100m_mt_03035_d03_clip.zip")
        job_status = dispatch(str(uuid4()), self.username, filepath, product_ident, self.check_idents)
        self.assertTrue(all([check["status"] == "ok" for check in job_status["checks"]]),
                        self.show_messages(job_status))

    # High resolution water and wetness (WAW) - 20m
    def test_waw_020m(self):
        product_ident = "waw_020m"
        filepath = self.raster_data_dir.joinpath(product_ident, "WAW_2015_020m_mt_03035_d06_clip.zip")
        job_status = dispatch(str(uuid4()), self.username, filepath, product_ident, self.check_idents)
        self.assertTrue(all([check["status"] == "ok" for check in job_status["checks"]]),
                        self.show_messages(job_status))

    # High resolution water and wetness (WAW) - 100m
    def test_waw_100m(self):
        product_ident = "waw_100m"
        filepath = self.raster_data_dir.joinpath(product_ident, "WAW_2015_100m_mt_03035_d02_clip.zip")
        job_status = dispatch(str(uuid4()), self.username, filepath, product_ident, self.check_idents)
        self.assertTrue(all([check["status"] == "ok" for check in job_status["checks"]]),
                        self.show_messages(job_status))