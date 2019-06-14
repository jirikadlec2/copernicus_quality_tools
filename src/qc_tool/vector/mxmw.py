#!/usr/bin/env python3
# -*- coding: utf-8 -*-


DESCRIPTION = "Maximum mapping width."
IS_SYSTEM = False


def run_check(params, status):
    from qc_tool.vector.helper import do_layers
    from qc_tool.vector.helper import get_failed_items_message

    cursor = params["connection_manager"].get_connection().cursor()

    for layer_def in do_layers(params):
        # Prepare parameters used in sql clauses.
        sql_params = {"fid_name": layer_def["pg_fid_name"],
                      "layer_name": layer_def["pg_layer_name"],
                      "code_column_name": params["code_column_name"],
                      "warning_table": "s{:02d}_{:s}_warning".format(params["step_nr"], layer_def["pg_layer_name"])}
        sql_execute_params = {"buffer": -params["mxmw"] / 2,
                              "linear_code": params["linear_code"]}

        # Create table of warning items.
        sql = ("CREATE TABLE {warning_table} AS"
               " SELECT {fid_name}"
               " FROM {layer_name}"
               " WHERE"
               "  {code_column_name} = %(linear_code)s"
               "  AND NOT ST_IsEmpty(ST_Buffer(geom, %(buffer)s));")
        sql = sql.format(**sql_params)
        cursor.execute(sql, sql_execute_params)

        # Report warning features.
        items_message = get_failed_items_message(cursor, sql_params["warning_table"], layer_def["pg_fid_name"])
        if items_message is not None:
            status.info("Layer {:s} has warning features with {:s}: {:s}."
                        .format(layer_def["pg_layer_name"], layer_def["fid_display_name"], items_message))
            status.add_error_table(sql_params["warning_table"], layer_def["pg_layer_name"], layer_def["pg_fid_name"])
