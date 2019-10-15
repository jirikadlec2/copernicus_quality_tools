#! /usr/bin/env python3
# -*- coding: utf-8 -*-


DESCRIPTION = "There is no gap in the AOI."
IS_SYSTEM = False


def run_check(params, status):
    import subprocess
    import numpy
    import osgeo.gdal as gdal
    import osgeo.osr as osr

    from qc_tool.raster.helper import do_raster_layers
    from qc_tool.raster.helper import find_tiles
    from qc_tool.raster.helper import read_tile
    from qc_tool.raster.helper import write_progress
    from qc_tool.raster.helper import write_percent


    aoi_code = params["aoi_code"]
    gap_value_ds = params["outside_area_code"]

    # Find the external boundary raster mask layer.
    raster_boundary_dir = params["boundary_dir"].joinpath("raster")
    mask_ident = "default"
    if "mask" in params:
        mask_ident = params["mask"]

    for layer_def in do_raster_layers(params):

        # set this to true for writing partial progress to a text file.
        report_progress = True
        progress_filename = "{:s}_{:s}_progress.txt".format(__name__.split(".")[-1], layer_def["src_filepath"].stem)
        progress_filepath = params["output_dir"].joinpath(progress_filename)
        percent_filename = "{:s}_{:s}_percent.txt".format(__name__.split(".")[-1], layer_def["src_filepath"].stem)
        percent_filepath = params["output_dir"].joinpath(percent_filename)

        # get raster corners and resolution
        ds = gdal.Open(str(layer_def["src_filepath"]))
        ds_gt = ds.GetGeoTransform()
        ds_ulx = ds_gt[0]
        ds_xres = ds_gt[1]
        ds_uly = ds_gt[3]
        ds_yres = ds_gt[5]
        ds_lrx = ds_ulx + (ds.RasterXSize * ds_xres)
        ds_lry = ds_uly + (ds.RasterYSize * ds_yres)

        # Check availability of mask.
        mask_file = raster_boundary_dir.joinpath("mask_{:s}_{:03d}m_{:s}.tif".format(mask_ident, int(ds_xres), aoi_code))
        if not mask_file.exists():
            status.info("Check cancelled due to boundary mask file {:s} not available.".format(mask_file.name))
            return
        mask_ds = gdal.Open(str(mask_file))
        if mask_ds is None:
            status.info("Check cancelled due to boundary mask file {:s} not available.".format(mask_file.name))
            return
        mask_band = mask_ds.GetRasterBand(1)
        nodata_value_mask = mask_band.GetNoDataValue()

        # get aoi mask corners and resolution
        mask_gt = mask_ds.GetGeoTransform()
        mask_ulx = mask_gt[0]
        mask_xres = mask_gt[1]
        mask_uly = mask_gt[3]
        mask_yres = mask_gt[5]
        mask_lrx = ds_ulx + (mask_ds.RasterXSize * mask_xres)
        mask_lry = ds_uly + (mask_ds.RasterYSize * mask_yres)

        # Check if the dataset extent intersects the mask extent.
        if (mask_ulx > ds_lrx or mask_uly < ds_lry or mask_lrx < ds_ulx or mask_lry > ds_uly):
            extent_message = "Layer {:s} does not intersect the aoi mask {:s}."
            extent_message = extent_message.format(layer_def["src_layer_name"], mask_ident)
            extent_message += "raster extent: [{:f} {:f}, {:f} {:f}]".format(ds_ulx, ds_uly, ds_lrx, ds_lry)
            extent_message += "aoi mask extent: [{:f} {:f}, {:f} {:f}]".format(mask_ulx, mask_uly, mask_lrx, mask_lry)
            status.info(extent_message)
            continue

        # Check if the raster and the AOI mask have the same resolution.
        if ds_xres != mask_xres or ds_yres != mask_yres:
            status.info("Resolution of the raster [{:f}, {:f}] does not match "
                        "the resolution [{:f}, {:f}] of the boundary mask {:s}.tif."
                        .format(ds_xres, ds_yres, mask_xres, mask_yres, mask_ident))
            continue

        # Check if origin of mask is aligned with origin of raster.
        if abs(ds_ulx - mask_ulx) % ds_xres > 0:
            status.info("X coordinates of the raster are not exactly aligned with x coordinates of boundary mask."
                        "Raster origin: {:f}, Mask origin: {:f}".format(ds_ulx, mask_ulx))
            continue

        if abs(ds_uly - mask_uly) % ds_yres > 0:
            status.info("Y coordinates of the raster are not exactly aligned with Y coordinates of boundary mask."
                        "Raster origin: {:f}, Mask origin: {:f}".format(ds_uly, mask_uly))
            continue

        # Calculate offset of checked raster dataset [ulx, uly] from boundary mask [ulx, uly].
        ds_add_cols = int(abs(mask_ulx - ds_ulx) / abs(ds_xres))
        ds_add_rows = int(abs(mask_uly - ds_uly) / abs(ds_yres))

        if report_progress:
            msg = "ds_ulx: {:f} mask_ulx: {:f} ds_add_cols: {:f}".format(ds_ulx, mask_ulx, ds_add_cols)
            msg += "\nds_uly: {:f} mask_uly: {:f} ds_add_rows: {:f}".format(ds_uly, mask_uly, ds_add_rows)
            msg += "\nRasterXSize: {:d} RasterYSize: {:d}".format(ds.RasterXSize, ds.RasterYSize)
            write_progress(progress_filepath, msg)

        # Find the tiles
        tiles = find_tiles(ds, mask_ds)
        if report_progress:
            write_progress(progress_filepath, "Number of tiles: {:d}".format(len(tiles)))

        # processing all the tiles:
        ds_band = ds.GetRasterBand(1)
        gap_count_total = 0
        num_tiles = len(tiles)
        gap_filepaths = []
        for tile_no, tile in enumerate(tiles):

            # reading the mask data into Numpy array
            mask_xoff = tile.x_offset
            mask_yoff = tile.y_offset
            blocksize_x = tile.ncols
            blocksize_y = tile.nrows
            arr_mask = mask_band.ReadAsArray(mask_xoff, mask_yoff, blocksize_x, blocksize_y)

            # If mask has all values unmapped then mask / raster comparison can be skipped.
            if numpy.max(arr_mask) == 0 or numpy.min(arr_mask) == nodata_value_mask:
                continue

            if tile.position == "outside":
                arr_gaps = (arr_mask == 1)
            elif tile.position == "inside":
                # current tile is completely inside the raster bounds (needs more testing..)
                arr_ds = ds_band.ReadAsArray(mask_xoff + ds_add_cols, mask_yoff + ds_add_rows, blocksize_x, blocksize_y)
                arr_gaps = ((arr_mask == 1) * (arr_ds == gap_value_ds))
            else:
                # current tile is partially inside the raster bounds
                arr_ds = read_tile(ds, tile, gap_value_ds)
                arr_gaps = ((arr_mask == 1) * (arr_ds == gap_value_ds))

            # find unmapped pixels inside mask
            gap_count = int(numpy.sum(arr_gaps))
            if gap_count > 0:

                # For each mask tile with gaps, create a new warning raster dataset.
                # These datasets can be merged or polygonized at the end of the run.
                src_stem = layer_def["src_filepath"].stem
                gap_ds_filename = "s{:02d}_{:s}_gap_warning_{:d}.tif".format(params["step_nr"], src_stem, tile_no)
                gap_ds_filepath = params["tmp_dir"].joinpath(gap_ds_filename)
                driver = gdal.GetDriverByName('GTiff')
                gap_ds = driver.Create(str(gap_ds_filepath), blocksize_x, blocksize_y, 1, gdal.GDT_Byte, ['COMPRESS=LZW'])
                gap_ds.SetGeoTransform([tile.xmin, mask_xres, 0, tile.ymax, 0, mask_yres])
                gap_sr = osr.SpatialReference()
                gap_sr.ImportFromWkt(ds.GetProjectionRef())
                gap_ds.SetProjection(gap_sr.ExportToWkt())
                gap_band = gap_ds.GetRasterBand(1)
                gap_band.SetNoDataValue(0)
                gap_band.WriteArray(arr_gaps.astype("byte"), 0, 0)
                gap_ds.FlushCache()
                gap_ds = None
                gap_filepaths.append(str(gap_ds_filepath))
                gap_count_total += gap_count

            if report_progress:
                msg = "tile: {:d}/{:d} ({:s}), gaps: {:d}".format(tile_no, num_tiles, tile.position, gap_count)
                write_progress(progress_filepath, msg)
                progress_percent = int(100 * (tile_no / num_tiles))
                write_percent(percent_filepath, progress_percent)


        # Free memory for checked raster and for mask.
        ds = None
        ds_mask = None

        # Generate attachments.
        if gap_count_total > 0:
            # Merge previously generated tile gap rasters into a .vrt
            src_stem = layer_def["src_filepath"].stem
            warning_vrt_filename = "s{:02d}_{:s}_gap_warning.vrt".format(params["step_nr"], src_stem)
            warning_vrt_filepath = params["tmp_dir"].joinpath(warning_vrt_filename)

            if len(gap_filepaths) > 0:
                cmd = ["gdalbuildvrt", str(warning_vrt_filepath)]
                cmd = cmd + gap_filepaths
                write_progress(progress_filepath, " ".join(cmd))
                subprocess.run(cmd)
                status.info("Layer {:s} has {:d} gap pixels in the mapped area."
                            .format(layer_def["src_layer_name"], gap_count_total))

            # Convert the .vrt to a GeoTiff
            if warning_vrt_filepath.is_file():
                warning_tif_filename = "s{:02d}_{:s}_gap_warning.tif".format(params["step_nr"], src_stem)
                warning_tif_filepath = params["output_dir"].joinpath(warning_tif_filename)
                cmd = ["gdal_translate",
                       "-of", "GTiff",
                       "-ot", "Byte",
                       "-co", "TILED=YES",
                       "-co", "COMPRESS=LZW",
                       str(warning_vrt_filepath),
                       str(warning_tif_filepath)]
                subprocess.run(cmd)
                status.add_attachment(warning_tif_filepath.name)
