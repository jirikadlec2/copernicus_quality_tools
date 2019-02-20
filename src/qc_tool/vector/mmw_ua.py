#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import re

from qc_tool.vector.helper import do_layers
from qc_tool.vector.helper import get_failed_items_message


DESCRIPTION = "Minimum mapping width, Urban Atlas."
IS_SYSTEM = False


def run_check(params, status):
    cursor = params["connection_manager"].get_connection().cursor()

    for layer_def in do_layers(params):
        # Prepare parameters used in sql clauses.
        sql_params = {"fid_name": layer_def["pg_fid_name"],
                      "layer_name": layer_def["pg_layer_name"],
                      "code_column_name": params["code_column_name"],
                      "general_table": "v12_{:s}_general".format(layer_def["pg_layer_name"]),
                      "exception_table": "v12_{:s}_exception".format(layer_def["pg_layer_name"]),
                      "warning_table": "v12_{:s}_warning".format(layer_def["pg_layer_name"])}

        # Create table of general items.
        sql = ("CREATE TABLE {general_table} AS"
               " SELECT {fid_name}"
               " FROM {layer_name}"
               " WHERE"
               "  ST_NumGeometries(ST_Buffer(wkb_geometry, %s)) = 1;")
        sql = sql.format(**sql_params)
        cursor.execute(sql, [-params["mmw"]])

        # Create table of exception items.
        sql = ("CREATE TABLE {exception_table} AS"
               " WITH"
               "  layer AS ("
               "   SELECT *"
               "   FROM {layer_name}"
               "   WHERE"
               "    {fid_name} NOT IN (SELECT {fid_name} FROM {general_table}))"
               " SELECT {fid_name}"
               " FROM layer"
               " WHERE"
               "  {code_column_name} LIKE '122%';")
        sql = sql.format(**sql_params)
        cursor.execute(sql)

        # Report exception features.
        items_message = get_failed_items_message(cursor, sql_params["exception_table"], layer_def["pg_fid_name"])
        if items_message is not None:
            status.info("Layer {:s} has exception features with {:s}: {:s}."
                        .format(layer_def["pg_layer_name"], layer_def["fid_display_name"], items_message))
            status.add_error_table(sql_params["exception_table"], layer_def["pg_layer_name"], layer_def["pg_fid_name"])

        # Create table of warning items.
        sql = ("CREATE TABLE {warning_table} AS"
               " SELECT {fid_name}"
               " FROM {layer_name}"
               " WHERE"
               "  {fid_name} NOT IN (SELECT {fid_name} FROM {general_table})"
               "  AND {fid_name} NOT IN (SELECT {fid_name} FROM {exception_table});")
        sql = sql.format(**sql_params)
        cursor.execute(sql)

        # Report warning features.
        items_message = get_failed_items_message(cursor, sql_params["warning_table"], layer_def["pg_fid_name"])
        if items_message is not None:
            status.info("Layer {:s} has warning features with {:s}: {:s}."
                        .format(layer_def["pg_layer_name"], layer_def["fid_display_name"], items_message))
            status.add_error_table(sql_params["warning_table"], layer_def["pg_layer_name"], layer_def["pg_fid_name"])