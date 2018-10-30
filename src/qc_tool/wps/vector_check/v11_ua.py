#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import re

from qc_tool.wps.helper import do_layers
from qc_tool.wps.helper import get_failed_items_message
from qc_tool.wps.registry import register_check_function
from qc_tool.wps.vector_check.v11 import count_table
from qc_tool.wps.vector_check.v11 import create_table
from qc_tool.wps.vector_check.v11 import drop_table
from qc_tool.wps.vector_check.v11 import subtract_table
from subprocess import run


def create_all_breaking_mmu(cursor, pg_fid_name, pg_layer_name, error_table_name, code_column_name):
    sql = ("CREATE TABLE {0:s} AS"
           "  SELECT {1:s} FROM {2:s}"
           "  WHERE ({3:s} LIKE '1%'  AND {3:s} NOT LIKE '122%' AND shape_area < 2500)"
           "        OR ({3:s} NOT LIKE '1%' AND {3:s} NOT LIKE '9%' AND shape_area < 10000);")
    sql = sql.format(error_table_name, pg_fid_name, pg_layer_name, code_column_name)
    cursor.execute(sql)
    return cursor.rowcount

def subtract_border_polygons(cursor, border_layer_name, pg_fid_name, pg_layer_name, error_table_name, except_table_name, code_column_name):
    """Subtracts polygons at boundary."""
    create_table(cursor, pg_fid_name, except_table_name, error_table_name)

    # Fill except table with polygons taken from error table and touching boundary.
    sql = ("WITH"
           "  boundary AS ("
           "    SELECT ST_Boundary(wkb_geometry) AS geom FROM {0:s}),"
           "  tr_boundary AS ("
           "    SELECT ST_Boundary(wkb_geometry) AS geom FROM {1:s} WHERE {2:s} LIKE '122%'),"
           "  ex_boundary AS ("
           "    SELECT DISTINCT lt.{3:s}, lt.wkb_geometry AS geom"
           "    FROM {1:s} lt INNER JOIN {4:s} et ON lt.{3:s} = et.{3:s}, boundary bt " 
           "    WHERE ST_Intersects(lt.wkb_geometry, bt.geom)),"
           "  ex_tr_boundary AS ("
           "    SELECT DISTINCT exb.{3:s}"
           "    FROM ex_boundary exb, tr_boundary trb"
           "    WHERE ST_Intersects(exb.geom, trb.geom))"
           " INSERT INTO {5:s}"
           "  SELECT {3:s} FROM ex_tr_boundary;")
    sql = sql.format(border_layer_name,
                     pg_layer_name,
                     code_column_name,
                     pg_fid_name,
                     error_table_name,
                     except_table_name)
    cursor.execute(sql)

    # Delete an item from error table if it is in except table already.
    subtract_table(cursor, pg_fid_name, error_table_name, except_table_name)

    error_count = count_table(cursor, error_table_name)
    except_count = count_table(cursor, except_table_name)
    return (error_count, except_count)


@register_check_function(__name__)
def run_check(params, status):
    cursor = params["connection_manager"].get_connection().cursor()
    for layer_def in do_layers(params):
        error_table_name = "{:s}_lessmmu_error".format(layer_def["pg_layer_name"])
        except_table_name = "{:s}_lessmmu_except".format(layer_def["pg_layer_name"])
        error_count = create_all_breaking_mmu(cursor,
                                              layer_def["pg_fid_name"],
                                              layer_def["pg_layer_name"],
                                              error_table_name,
                                              params["code_column_name"])
        (error_count, except_count) = subtract_border_polygons(cursor,
                                                               params["layer_defs"]["boundary"]["pg_layer_name"],
                                                               layer_def["pg_fid_name"],
                                                               layer_def["pg_layer_name"],
                                                               error_table_name,
                                                               except_table_name,
                                                               params["code_column_name"])

        # Clean the tables.
        if error_count == 0:
            drop_table(cursor, error_table_name)
        else:
            failed_items_message = get_failed_items_message(cursor, error_table_name, layer_def["pg_fid_name"])
            failed_message = "The layer {:s} has polygons with area less then MMU in rows: {:s}.".format(layer_def["pg_layer_name"], failed_items_message)
            status.add_message(failed_message)
            status.add_error_table(error_table_name, layer_def["pg_layer_name"], layer_def["pg_fid_name"])

        if except_count == 0:
            drop_table(cursor, except_table_name)
        else:
            failed_items_message = get_failed_items_message(cursor, except_table_name, layer_def["pg_fid_name"])
            failed_message = "The layer {:s} has exceptional polygons with area less then MMU in rows: {:s}.".format(layer_def["pg_layer_name"], failed_items_message)
            status.add_message(failed_message, failed=False)
            status.add_error_table(except_table_name, layer_def["pg_layer_name"], layer_def["pg_fid_name"])
