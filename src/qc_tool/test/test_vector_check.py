#!/usr/bin/env python3


from contextlib import closing

from qc_tool.common import TEST_DATA_DIR
from qc_tool.test.helper import VectorCheckTestCase


class TestImport2pg(VectorCheckTestCase):
    valid_geodatabase = "clc2012_mt.gdb"
    def setUp(self):
        super().setUp()
        self.filepath = str(TEST_DATA_DIR.joinpath(self.valid_geodatabase))
        self.params["layer_names"] = ["clc12_mt"]

    def test_import2pg_pass(self):
        from qc_tool.wps.vector_check.import2pg import run_check
        result = run_check(self.filepath, self.params)
        self.assertEqual("ok", result["status"])


    def test_import2pg_table_created(self):
        from qc_tool.wps.vector_check.import2pg import run_check
        run_check(self.filepath, self.params)

        cur = self.params["connection_manager"].get_connection().cursor()
        cur.execute("""SELECT id FROM {:s};""".format(self.params["layer_names"][0]))
        self.assertLess(0, cur.rowcount, "imported table should have at least one row.")

    def test_import2pg_functions_created(self):
        from qc_tool.wps.vector_check.import2pg import run_check
        run_check(self.filepath, self.params)

        job_schema = self.params["connection_manager"].get_dsn_schema()[1]
        expected_function_names = ["__v11_mmu_status",
                                   "__v11_mmu_polyline_border",
                                   "__v5_uniqueid",
                                   "__v6_validcodes",
                                   "__v8_multipartpolyg",
                                   "__v11_mmu_change_clc"]
        conn = self.params["connection_manager"].get_connection()
        cur = conn.cursor()
        cur.execute("""SELECT routine_name FROM information_schema.routines \
                       WHERE routine_type='FUNCTION' AND routine_schema='{:s}'""".format(job_schema))

        actual_function_names = [row[0] for row in cur.fetchall()]

        for expected_name in expected_function_names:
            self.assertIn(expected_name, actual_function_names,
                          "a function {:s} should be created in schema {:s}".format(expected_name, job_schema))


class TestV8(VectorCheckTestCase):
    def setUp(self):
        super().setUp()
        from qc_tool.wps.vector_check.import2pg import run_check as import_check
        self.filepath = str(TEST_DATA_DIR.joinpath("clc2012_mt.gdb"))
        self.params["layer_names"] =  ["clc12_mt"]
        import_check(self.filepath, self.params)

    def test_v8_Malta(self):
        from qc_tool.wps.vector_check.v8 import run_check
        result = run_check(self.filepath, self.params)
        self.assertEqual("ok", result["status"], "Check result should be ok for Malta.")


class TestV11(VectorCheckTestCase):
    def setUp(self):
        super().setUp()
        from qc_tool.wps.vector_check.import2pg import run_check as import_check
        self.filepath = str(TEST_DATA_DIR.joinpath("clc2012_mt.gdb"))
        self.params.update({"layer_names": ["clc12_mt"],
                            "area_ha": 25,
                            "border_exception": True})
        import_check(self.filepath, self.params)

    def test_v11_small_mmu_should_pass(self):
        from qc_tool.wps.vector_check.v11 import run_check
        result = run_check(self.filepath, self.params)
        self.assertEqual("ok", result["status"], "Check result should be ok for MMU=25ha.")

    def test_v11_big_mmu_should_fail(self):
        from qc_tool.wps.vector_check.v11 import run_check
        self.params["area_ha"] = 250
        result = run_check(self.filepath, self.params)
        self.assertEqual("failed", result["status"], "Check result should be 'failed' for MMU=250ha.")

    def test_v11_border_table(self):
        """
        a _polyline_border table should be created in the job's schema
        :return:
        """
        from qc_tool.wps.vector_check.v11 import run_check
        run_check(self.filepath, self.params)

        table_name = "{:s}_polyline_border".format(self.params["layer_names"][0])
        dsn, job_schema_name =  self.params["connection_manager"].get_dsn_schema()
        cur = self.params["connection_manager"].get_connection().cursor()
        cur.execute("SELECT table_schema FROM information_schema.tables WHERE table_name=%s;", (table_name,))
        row = cur.fetchone()
        self.assertIsNotNone(row, "There should be polyline_border table created.")
        table_schema = row[0]
        self.assertNotEqual("public", table_schema, "polyline_border table should not be in public schema.")
        self.assertEqual(job_schema_name, table_schema, "polyline_border table is in {:s} schema instead of {:s} schema.".format(table_schema, job_schema_name))


class TestV11_DataNotImported(VectorCheckTestCase):
    def test_missing_table_should_cause_fail(self):
        from qc_tool.wps.vector_check.v11 import run_check
        filepath = TEST_DATA_DIR.joinpath("clc2012_mt.gdb")
        self.params.update({"area_ha": 25,
                            "border_exception": True})
        result = run_check(filepath, self.params)
        self.assertEqual("failed", result["status"], "check result should be FAILED when table is not imported.")
