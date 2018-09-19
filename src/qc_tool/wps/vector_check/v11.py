#!/bin/env python3
# -*- coding: utf-8 -*-


import re

from qc_tool.wps.helper import get_failed_ids_message
from qc_tool.wps.registry import register_check_function


def count_table(cursor, table_name):
    sql = "SELECT count(*) FROM {:s};".format(table_name)
    cursor.execute(sql)
    count = cursor.fetchone()[0]
    return count

def create_table(cursor, ident_colname, new_table_name, orig_table_name):
    sql = "CREATE TABLE {0:s} AS SELECT {1:s} FROM {2:s} WHERE FALSE;"
    sql = sql.format(new_table_name, ident_colname, orig_table_name)
    cursor.execute(sql)

def drop_table(cursor, table_name):
    sql = "DROP TABLE IF EXISTS {:s};".format(table_name)
    cursor.execute(sql)

def subtract_table(cursor, ident_colname, first_table, second_table):
    sql = "DELETE FROM {0:s} USING {1:s} WHERE {0:s}.{2:s} = {1:s}.{2:s};"
    sql = sql.format(first_table, second_table, ident_colname)
    cursor.execute(sql)
    return cursor.rowcount

def create_all_breaking_mmu(cursor, ident_colname, layer_name, error_table_name, area_ha):
    area_m = area_ha * 10000
    sql = ("CREATE TABLE {:s} AS"
           " SELECT {:s} FROM {:s}"
           " WHERE shape_area < %s;")
    sql = sql.format(error_table_name, ident_colname, layer_name)
    cursor.execute(sql, [area_m])
    return cursor.rowcount

def subtract_border_polygons(cursor, border_layer_name, ident_colname, layer_name, error_table_name, except_table_name):
    """Subtracts polygons at boundary."""
    create_table(cursor, ident_colname, except_table_name, error_table_name)

    # Fill except table with polygons taken from error table and touching boundary.
    sql = ("WITH boundary AS ("
           "  SELECT ST_Boundary(ST_Union(wkb_geometry)) AS wkb_geometry FROM {0:s})"
           " INSERT INTO {1:s}"
           "  SELECT DISTINCT lt.{2:s}"
           "  FROM {3:s} lt INNER JOIN {4:s} et ON lt.{2:s} = et.{2:s}, boundary"
           "  WHERE ST_Intersects(lt.wkb_geometry, boundary.wkb_geometry);")
    sql = sql.format(border_layer_name,
                     except_table_name,
                     ident_colname,
                     layer_name,
                     error_table_name)
    cursor.execute(sql)

    # Delete an item from error table if it is in except table already.
    subtract_table(cursor, ident_colname, error_table_name, except_table_name)

    error_count = count_table(cursor, error_table_name)
    except_count = count_table(cursor, except_table_name)
    return (error_count, except_count)

def subtract_inner_polygons(cursor, ident_colname, layer_name, error_table_name, except_table_name, code_colname, area_ha):
    """Subtracts polygons smaller than MMU which are part of dissolved polygons greater than MMU."""
    area_m = area_ha * 10000
    sql = ("WITH"
           "  all_dissolved AS ("
           "    SELECT (ST_Dump(ST_Union(wkb_geometry))).geom geom FROM {0:s} GROUP BY {1:s}),"
           "  big_dissolved AS ("
           "    SELECT geom FROM all_dissolved WHERE ST_Area(geom) > %s)"
           " INSERT INTO {2:s}"
           "  SELECT lt.{3:s}"
           "  FROM {0:s} lt INNER JOIN {4:s} et ON lt.{3:s} = et.{3:s}, big_dissolved "
           "  WHERE ST_Within(lt.wkb_geometry, big_dissolved.geom);")
    sql = sql.format(layer_name,
                     code_colname,
                     except_table_name,
                     ident_colname,
                     error_table_name,
                     layer_name,)
    cursor.execute(sql, [area_m])

    # Delete an item from error table if it is in except table already.
    subtract_table(cursor, ident_colname, error_table_name, except_table_name)

    error_count = count_table(cursor, error_table_name)
    except_count = count_table(cursor, except_table_name)
    return (error_count, except_count)


@register_check_function(__name__)
def run_check(params, status):
    cursor = params["connection_manager"].get_connection().cursor()

    for layer_name in params["db_layer_names"]:
        if "code_regex" in params:
            mobj = re.search(params["code_regex"], layer_name)
            code = mobj.group(1)
            code_colnames = params["code_to_column_names"][code]
            border_exception = True
        else:
            code_colnames = []
            border_exception = params["border_exception"]

        error_table_name = "{:s}_lessmmu_error".format(layer_name)
        if not border_exception:
            # Status without border.
            error_count = create_all_breaking_mmu(cursor,
                                                  params["ident_colname"],
                                                  layer_name,
                                                  error_table_name,
                                                  params["area_ha"])
            except_count = 0
        else:
            except_table_name = "{:s}_lessmmu_except".format(layer_name)
            border_source_layer = params["border_source_layer"]
            create_all_breaking_mmu(cursor,
                                    params["ident_colname"],
                                    layer_name,
                                    error_table_name,
                                    params["area_ha"])
            (error_count, except_count) = subtract_border_polygons(cursor,
                                                                   border_source_layer,
                                                                   params["ident_colname"],
                                                                   layer_name,
                                                                   error_table_name,
                                                                   except_table_name)
            for code_colname in code_colnames:
                (error_count, except_count) = subtract_inner_polygons(cursor,
                                                                      params["ident_colname"],
                                                                      layer_name,
                                                                      error_table_name,
                                                                      except_table_name,
                                                                      code_colname,
                                                                      params["area_ha"])

        # Clean the tables.
        if error_count == 0:
            drop_table(cursor, error_table_name)
        else:
            failed_ids_message = get_failed_ids_message(cursor, error_table_name, params["ident_colname"])
            failed_message = "The layer {:s} has polygons with area less then MMU in rows: {:s}.".format(layer_name, failed_ids_message)
            status.add_message(failed_message)
            status.add_error_table(error_table_name)
        if except_count == 0:
            drop_table(cursor, except_table_name)
        else:
            failed_ids_message = get_failed_ids_message(cursor, except_table_name, params["ident_colname"])
            failed_message = "The layer {:s} has exceptional polygons with area less then MMU in rows: {:s}.".format(layer_nar_name, failed_ids_message)
            status.add_message(failed_message, failed=False)
            status.add_error_table(except_table_name)
