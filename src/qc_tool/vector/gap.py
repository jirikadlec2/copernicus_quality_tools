#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import re

from qc_tool.vector.helper import do_layers
from qc_tool.vector.helper import get_failed_items_message


DESCRIPTION = "There is no gap in the AOI."
IS_SYSTEM = False


def run_check(params, status):
    cursor = params["connection_manager"].get_connection().cursor()

    if "boundary" not in params["layer_defs"]:
        status.cancelled("Check cancelled due to boundary not being available.")
        return

    for layer_def in do_layers(params):
        # Prepare parameters used in sql clauses.
        sql_params = {"layer_name": layer_def["pg_layer_name"],
                      "boundary_name": params["layer_defs"]["boundary"]["pg_layer_name"],
                      "error_table": "v10_{:s}_error".format(layer_def["pg_layer_name"])}

        # Create table of error items.
        sql = ("CREATE TABLE {error_table} AS"
               " WITH"
               "  layer_union AS (SELECT ST_Union(wkb_geometry) AS geom FROM {layer_name}),"
               "  boundary_union AS (SELECT ST_Union(wkb_geometry) AS geom FROM {boundary_name})"
               " SELECT (ST_Dump(ST_Difference(boundary_union.geom, layer_union.geom))).geom AS geom"
               " FROM layer_union, boundary_union;")
        sql = sql.format(**sql_params)
        cursor.execute(sql)

        # Report error items.
        if cursor.rowcount > 0:
            status.failed("Layer {:s} has {:d} gaps.".format(layer_def["pg_layer_name"], cursor.rowcount))
            status.add_full_table(sql_params["error_table"])