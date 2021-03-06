# -*- coding: utf-8 -*-


import logging
import sys
import shutil
import time
import traceback
from pathlib import Path
from zipfile import ZipFile

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import PermissionDenied
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.forms.models import model_to_dict
from django.http import FileResponse
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

import qc_tool.frontend.dashboard.models as models
from qc_tool.common import auth_worker
from qc_tool.common import check_running_job
from qc_tool.common import CONFIG
from qc_tool.common import JOB_RUNNING
from qc_tool.common import JOB_WAITING
from qc_tool.common import compose_attachment_filepath
from qc_tool.common import compile_job_form_data
from qc_tool.common import compile_job_report_data
from qc_tool.common import get_job_report_filepath
from qc_tool.common import get_product_descriptions
from qc_tool.common import locate_product_definition
from qc_tool.common import WORKER_PORT
from qc_tool.frontend.dashboard.helpers import find_product_description
from qc_tool.frontend.dashboard.helpers import get_announcement_message
from qc_tool.frontend.dashboard.helpers import guess_product_ident
from qc_tool.frontend.dashboard.helpers import submit_job


logger = logging.getLogger(__name__)

CHECK_RUNNING_JOB_DELAY = 10

UPLOADED_CHUNK_PROCESSING_DELAY = 1


@login_required
def deliveries(request):
    """
    Displays the main page with uploaded files and action buttons
    """
    return render(request, 'dashboard/deliveries.html', {"submission_enabled": settings.SUBMISSION_ENABLED,
                                                         "show_logo": settings.SHOW_LOGO,
                                                         "announcement": get_announcement_message()})


@login_required
def setup_job(request):
    """
    Displays a page for starting a new QA job
    :param delivery_id: The ID of the delivery ZIP file.
    """

    delivery_ids = request.GET.get("deliveries", "").split(",")

    if len(delivery_ids) == 0:
        raise Http404("No delivery IDs have been specified.")

    # input validation
    for delivery_id in delivery_ids:
        try:
            int(delivery_id)
        except ValueError:
            return HttpResponseBadRequest("Deliveries parameter must be comma-separated ID's.")

    product_infos = get_product_descriptions()
    product_list = [{"product_ident": product_ident, "product_description": product_name}
                    for product_ident, product_name in product_infos.items()]
    product_list = sorted(product_list, key=lambda x: x["product_description"])

    deliveries = []
    for delivery_id in delivery_ids:
        delivery = get_object_or_404(models.Delivery, pk=int(delivery_id))

        # Starting a job for a submitted delivery is not permitted.
        if delivery.date_submitted is not None:
            raise PermissionDenied("Starting a new QC job on submitted delivery is not permitted.")

        # Starting a job for another user's delivery is not permitted unless you are a superuser.
        if not request.user.is_superuser:
            if delivery.user != request.user:
                raise PermissionDenied("Delivery id={:d} belongs to another user.".format(int(delivery_id)))
        deliveries.append(delivery)

    # pass in product ident (only for the single delivery case)
    if len(deliveries) == 1:
        product_ident = deliveries[0].product_ident
    else:
        product_ident = None

    context = {"deliveries": deliveries,
               "product_ident": product_ident,
               "product_list": product_list,
               "show_logo": settings.SHOW_LOGO,
               "announcement": get_announcement_message()}
    return render(request, "dashboard/setup_job.html", context)


@login_required
def get_deliveries_json(request):
    """
    Returns a list of all deliveries for the current user.
    The deliveries are loaded from the dashboard_deliveries database table.
    The associated ZIP files are stored in <MEDIA_ROOT>/<username>/

    :param request:
    :return: list of deliveries with associated job information in JSON format
    """

    # Before refreshing the page, update status of all waiting or running jobs.
    running_jobs = models.Job.objects.filter(job_status=JOB_RUNNING)
    for job in running_jobs:
        job_status = check_running_job(str(job.job_uuid), job.worker_url)
        if job_status is not None:
            job.update_status(job_status)

    # Retrieve a table of deliveries.
    # If a delivery has one or more jobs, show information about the job with latest date_created.
    with connection.cursor() as cursor:
        sql = """
        SELECT d.id, d.filename, u.username, d.date_uploaded, d.size_bytes,
        d.product_ident, d.product_description, d.date_submitted, d.is_deleted,
        j.job_uuid AS last_job_uuid,
        j.date_created, j.date_started, j.job_status as last_job_status
        FROM dashboard_delivery d
        LEFT JOIN dashboard_job j
        ON j.job_uuid = (
          SELECT job_uuid FROM dashboard_job j
          WHERE j.delivery_id = d.id
          ORDER BY j.date_created DESC LIMIT 1)
        INNER JOIN auth_user u
        ON d.user_id = u.id
        """

        if request.user.is_superuser:
            # Superusers see deliveries of all other users.
            # Deleted delivery records are not shown , see #106579.
            sql += "WHERE d.is_deleted != 1 ORDER BY d.id DESC"
            cursor.execute(sql)
        else:
            # Regular users only see their own deliveries.
            sql += "WHERE d.is_deleted != 1 AND d.user_id = %s ORDER BY d.id DESC"
            cursor.execute(sql, (request.user.id,))
        header = [i[0] for i in cursor.description]
        rows = cursor.fetchall()
        data = []
        for row in rows:
            data.append(dict(zip(header, row)))

        return JsonResponse(data, safe=False)


@csrf_exempt
def resumable_upload_page(request):
    """
    Resumable file upload demo.
    """
    return render(request, 'dashboard/resumable_upload.html')


@csrf_exempt
@login_required
def announcement(request):
    """
    Saves or loads an announcement message.
    """
    if request.method == "GET":

        if CONFIG["announcement_path"].is_file():
            announcement_message = CONFIG["announcement_path"].read_text()
        else:
            announcement_message = ""

        return render(request, 'dashboard/announcement.html', {"announcement": announcement_message})
    else:
        try:
            CONFIG["announcement_path"].write_text(request.POST.get("announcement_text"))
            announcement_text = request.POST.get("announcement_text")
            if announcement_text:
                result_message = "Announcement has been successfully updated."
            else:
                result_message = "Announcement has been successfully removed."
            return render(request, 'dashboard/announcement.html',
                          {"announcement": request.POST.get("announcement_text"),
                           "result_message": result_message})
        except BaseException as e:
            return render(request, 'dashboard/announcement.html',
                          {"announcement": request.POST.get("announcement_text"),
                           "error_message": "Error updating announcement."})


@login_required
def boundaries(request):
    """
    Returns a list of all boundary aoi files in the active boundary package in html format.
    """
    return render(request, 'dashboard/boundaries.html', {})


@login_required
def get_boundaries_json(request, boundary_type):
    """
    Returns a list of all boundary aoi files in the active boundary package in json format.

    :param request:
    :return: list of boundary .tif or .shp file infos with name and size in JSON format
    """
    boundary_list = []

    if boundary_type == "raster":
        raster_dir = CONFIG["boundary_dir"].joinpath("raster")
        raster_filepaths = [path for path in raster_dir.glob("**/*") if
                            path.is_file() and path.suffix.lower() == ".tif"]
        for r in raster_filepaths:
            boundary_list.append({"filepath": str(r), "filename": r.name, "size_bytes": r.stat().st_size, "type": "raster"})

    else:
        vector_dir = CONFIG["boundary_dir"].joinpath("vector")
        vector_filepaths = [path for path in vector_dir.glob("**/*") if
                            path.is_file() and path.suffix.lower() == ".shp" or path.suffix.lower() == ".gpkg"]
        for v in vector_filepaths:
            boundary_list.append({"filepath": str(v), "filename": v.name, "size_bytes": v.stat().st_size, "type": "vector"})

    return JsonResponse(boundary_list, safe=False)


@login_required
def boundaries_upload(request):
    """
    Uploading boundary package via web console.
    default location for storing boundary package is CONFIG["boundary_dir"].
    """
    try:
        boundary_upload_path = Path(CONFIG["boundary_dir"])

        if request.method == 'POST' and request.FILES["file"]:

            # retrieve file info from uploaded zip file
            myfile = request.FILES["file"]
            logger.info("Processing uploaded boundary ZIP file: {:s}".format(myfile.name))

            # Check if there is an existing boundary package and boundary ZIP file. If found, delete.
            dst_filepath = boundary_upload_path.joinpath(myfile.name)
            if dst_filepath.exists():
                logger.debug("deleting abandoned zip file {:s}".format(str(dst_filepath)))
                dst_filepath.unlink()

            logger.debug("saving uploaded boundary zip file to {:s}".format(str(dst_filepath)))
            fs = FileSystemStorage(str(boundary_upload_path))
            fs.save(myfile.name, myfile)
            logger.debug("uploaded boundary zip file saved successfully to filesystem.")

            # Delete unzipped boundary files.
            raster_dir = boundary_upload_path.joinpath("raster")
            if raster_dir.exists():
                shutil.rmtree(str(raster_dir))

            vector_dir = boundary_upload_path.joinpath("vector")
            if vector_dir.exists():
                shutil.rmtree(str(vector_dir))

            # Unzip the uploaded boundary package.
            with ZipFile(str(dst_filepath)) as zip_file:
                zip_file.extractall(path=str(boundary_upload_path))

            data = {'is_valid': True,
                    'name': myfile.name,
                    'url': myfile.name}
            return JsonResponse(data)

    except BaseException as e:
        logger.debug("upload exception!")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        msg = traceback.format_exception(exc_type, exc_value, exc_traceback)
        logger.debug(msg)
        data = {'is_valid': False,
                'name': None,
                'url': None,
                'message': msg}

        return JsonResponse(data)

    return render(request, 'dashboard/boundaries_upload.html')



@csrf_exempt
def delivery_delete(request):
    """
    Deletes a delivery from the database and deleted the associated ZIP file from the filesystem.
    """
    if request.method == "POST":
        delivery_ids = request.POST.get("ids").split(",")
        logger.debug("delivery_delete ids={:s}".format(repr(delivery_ids)))

        # Validate deliveries.
        for delivery_id in delivery_ids:

            # Validate delivery id.
            try:
                int(delivery_id)
            except ValueError:
                error_message = "Delivery id {:s} must be an integer.".format(repr(delivery_id))
                response = JsonResponse({"status": "error", "message": error_message})
                response.status_code = 400
                return response

            # Get delivery entity.
            delivery = get_object_or_404(models.Delivery, pk=int(delivery_id))

            # Authorize the user.
            if not request.user.is_superuser:
                if request.user.id != delivery.user.id:
                    error_message = "User {:s} is not authorized to delete delivery {:s}.".format(request.user.username, delivery.filename)
                    response = JsonResponse({"status": "error", "message": error_message})
                    response.status_code = 403
                    return response

            # Abort, if the job is in JOB_WAITING or JOB_RUNNING status.
            waiting_count = models.Job.objects.filter(delivery__id=delivery.id).filter(job_status=JOB_WAITING).count()
            if waiting_count > 0:
                error_message = "Delivery {:s} cannot be deleted. QC job is currently waiting.".format(delivery.filename)
                response = JsonResponse({"status": "error", "message": error_message})
                response.status_code = 400
                return response
            running_count = models.Job.objects.filter(delivery__id=delivery.id).filter(job_status=JOB_RUNNING).count()
            if running_count > 0:
                error_message = "Delivery {:s} cannot be deleted. QC job is currently running.".format(delivery.filename)
                response = JsonResponse({"status": "error", "message": error_message})
                response.status_code = 400
                return response

        # Delete deliveries.
        for delivery_id in delivery_ids:
            # Get delivery entity.
            delivery = get_object_or_404(models.Delivery, pk=int(delivery_id))

            # Delete delivery .zip file on the file system.
            filepath = Path(settings.MEDIA_ROOT).joinpath(request.user.username).joinpath(delivery.filename)
            if filepath.exists():
                filepath.unlink()

            # The delivery and its jobs are not actually deleted from the database.
            # Only delivery.is_deleted attribute is set to True.
            # This is done in order to preserve the job history.
            delivery.is_deleted = True
            delivery.save()
        return JsonResponse({"status":"ok", "message": "{:d} deliveries have been deleted.".format(len(delivery_ids))})


@csrf_exempt
def job_delete(request):
    """
    Deletes the job from the database and associated files from the filesystem.
    """
    if request.method == "POST":
        uuids = request.POST.get("uuids")

        logger.debug("job_delete uuids={:s}".format(uuids))

        job_uuids = uuids.split(",")
        num_deleted = 0

        # Job status validation.
        for job_uuid in job_uuids:

            # Existence validation.
            job = get_object_or_404(models.Job, pk=str(job_uuid))

            # User validation.
            if not request.user.is_superuser:
                if request.user.id != job.delivery.user.id:
                    return PermissionDenied("User {:s} is not authorized to delete job {:s}"
                                            .format(request.user.username, job_uuid))

            # Job status validation.
            running_jobs = models.Job.objects.filter(job_uuid=str(job_uuid)).filter(job_status=JOB_RUNNING)
            if len(running_jobs) > 0:
                return JsonResponse({"status": "error",
                                     "message": "Job {:s} cannot be deleted. QC job is currently running."
                                                .format(job_uuid)})
        deleted_jobs = []
        for job_uuid in job_uuids:
            models.Job.objects.filter(job_uuid=str(job_uuid)).delete()
            deleted_jobs.append(job_uuid)
        return JsonResponse({"status":"ok", "message": "{:d} jobs deleted successfully."
                            .format(len(deleted_jobs))})


@csrf_exempt
def submit_delivery_to_eea(request):
    if request.method == "POST":
        delivery_id = request.POST.get("id")
        filename = request.POST.get("filename")

        # Check if delivery with given ID exists.
        try:
            d = models.Delivery.objects.get(id=delivery_id)
        except ObjectDoesNotExist:
            response = JsonResponse({"status": "error",
                                     "message": "Delivery id={0} cannot be found in the database.".format(delivery_id)})
            response.status_code = 404
            return response

        try:
            logger.debug("delivery_submit_eea id=" + str(delivery_id))

            zip_filepath = Path(settings.MEDIA_ROOT).joinpath(request.user.username).joinpath(d.filename)

            job = d.get_submittable_job()
            if job is None:
                message = "Delivery {:s} cannot be submitted to EEA. Status is not OK.)".format(d.filename)
                response = JsonResponse({"status": "error", "message": message})
                response.status_code = 400
                return response
            submission_date = timezone.now()
            submit_job(job.job_uuid, zip_filepath, CONFIG["submission_dir"], submission_date)
            d.submit()
            d.submission_date = submission_date
            d.save()
        except BaseException as e:
            d.date_submitted = None
            d.save()
            error_message = "ERROR submitting delivery to EEA. file {:s}. exception {:s}".format(filename, str(e))
            logger.error(error_message)
            response = JsonResponse({"status": "error", "message": error_message})
            response.status_code = 500
            return response

        return JsonResponse({"status":"ok",
                             "message": "Delivery {0} successfully submitted to EEA.".format(filename)})

@login_required
def get_product_list(request):
    """
    returns a list of all product types that are available for checking.
    :param request:
    :return: list of the product types with items {name, description} in JSON format
    """
    product_infos = get_product_descriptions()
    product_list = [{'name': product_ident, 'description': product_description}
                    for product_ident, product_description in product_infos.items()]
    product_list = sorted(product_list, key=lambda x: x['description'])
    return JsonResponse({'product_list': product_list})

def get_product_definition(request, product_ident):
    """
    Shows the json product definition.
    """
    filepath = locate_product_definition(product_ident)
    try:
        return FileResponse(open(str(filepath), "rb"), content_type="application/json")
    except FileNotFoundError:
        raise Http404()

@login_required
def get_job_info(request, product_ident):
    """
    returns a table of details about the product
    :param request:
    :param product_ident: the name of the product type for example clc
    :return: product details with a list of job steps and their type (system, required, optional)
    """
    job_report = compile_job_form_data(product_ident)
    return JsonResponse({'job_result': job_report})

def get_job_report(request, job_uuid):
    job = models.Job.objects.get(job_uuid=job_uuid)
    job_result = compile_job_report_data(job_uuid, job.product_ident)
    return JsonResponse(job_result, safe=False)

def get_job_history_json(request, delivery_id):
    """
    Shows the history of all jobs for a specific delivery in .json format.
    """
    delivery = get_object_or_404(models.Delivery, pk=int(delivery_id))

    if not request.user.is_superuser:
        if delivery.user != request.user:
            raise PermissionDenied("Delivery id={:d} belongs to another user.".format(int(delivery_id)))

    # find all jobs with same filename
    if request.user.is_superuser:
        # superuser can see all jobs.
        jobs = models.Job.objects.filter(delivery__filename=delivery.filename) \
            .order_by("-date_created")
    else:
        # regular user can only see their own jobs.
        jobs = models.Job.objects.filter(delivery__filename=delivery.filename)\
            .filter(delivery__user=request.user)\
            .order_by("-date_created")
    for job in jobs:
        if job.job_status == JOB_RUNNING:
            job_status = check_running_job(str(job.job_uuid), job.worker_url)
            if job_status is not None:
                job.update_status(job_status)
    return JsonResponse(list(jobs.values()), safe=False)

def job_history_page(request, delivery_id):
    """
    Shows the history of all jobs for a specific delivery in .json format.
    """
    delivery = get_object_or_404(models.Delivery, pk=int(delivery_id))
    if not request.user.is_superuser:
        if delivery.user != request.user:
            raise PermissionDenied("Delivery id={:d} belongs to another user.".format(int(delivery_id)))
    return render(request, 'dashboard/job_history.html', {"delivery": delivery,
                                                          "show_logo": settings.SHOW_LOGO})
@login_required
def get_result(request, job_uuid):
    """
    Shows the result page with detailed results of the selected job.
    """
    job = models.Job.objects.get(job_uuid=job_uuid)
    delivery = job.delivery
    job_report = compile_job_report_data(job_uuid, job.product_ident)

    for step in job_report["steps"]:
        # Strip initial qc_tool. from check idents.
        if step["check_ident"].startswith("qc_tool."):
            step["check_ident"] = ".".join(step["check_ident"].split(".")[1:])
        # Inform the result page about presence of a check with 'aborted' status.
        if step["status"] == "aborted":
            job_report["aborted_check"] = step["check_ident"]
    return render(request, "dashboard/result.html", {"job_report":job_report,
                                                     "delivery": delivery,
                                                     "show_logo": settings.SHOW_LOGO,
                                                     "announcement": get_announcement_message()})

def get_pdf_report(request, job_uuid):
    try:
        filepath = get_job_report_filepath(job_uuid)
    except FileNotFoundError:
        # There is no result.
        raise Http404()
    try:
        response = FileResponse(open(str(filepath), "rb"), content_type="application/pdf", as_attachment=True)
    except FileNotFoundError:
        # There is no report.
        raise Http404()
    return response

@login_required
def download_delivery_file(request, delivery_id):
    delivery = get_object_or_404(models.Delivery, pk=int(delivery_id))

    # Authorization check.q
    if not request.user.is_superuser:
        if delivery.user != request.user:
            raise PermissionDenied("You are not authorized to view uploaded file for delivery id={:d}."
                                   .format(int(delivery_id)))
    # File existence check.
    if delivery.is_deleted:
        raise Http404("Uploaded file for delivery id={:d} has been deleted by the user.".format(int(delivery_id)))

    # Downloading the delivery Zip file.
    try:
        delivery_filepath = Path(settings.MEDIA_ROOT).joinpath(delivery.user.username, delivery.filename)
        return FileResponse(open(str(delivery_filepath), "rb"), content_type="application/zip", as_attachment=True)
    except FileNotFoundError:
        raise Http404()

@login_required
def get_attachment(request, job_uuid, attachment_filename):
    attachment_filepath = compose_attachment_filepath(job_uuid, attachment_filename)
    return FileResponse(open(str(attachment_filepath), "rb"), as_attachment=True)

@login_required
def update_job(request, job_uuid):
    job = models.Job.objects.get(job_uuid=job_uuid)

    if job.job_status == JOB_RUNNING:
        time_running = (timezone.now() - job.date_started).total_seconds()
        if time_running > CHECK_RUNNING_JOB_DELAY:
            job_status = check_running_job(str(job.job_uuid), job.worker_url)
            if job_status is not None:
                job.update_status(job_status)

    return JsonResponse({"id": job.delivery.id, "last_job_uuid": job.job_uuid, "last_job_status": job.job_status})

@csrf_exempt
def create_job(request):
    delivery_ids = request.POST.get("delivery_ids").split(",")
    product_ident = request.POST.get("product_ident")
    skip_steps = request.POST.get("skip_steps")
    if skip_steps == "":
        skip_steps = None

    num_created = 0

    for delivery_id in delivery_ids:
        # Input validation.
        try:
            int(delivery_id)
        except ValueError:
            return HttpResponseBadRequest("delivery id " + delivery_id + " must be a valid integer id.")

        # Update delivery status in the frontend database.
        d = models.Delivery.objects.get(id=int(delivery_id))
        d.create_job(product_ident, skip_steps)
        num_created += 1
        logger.debug("Delivery {:d}: job has been submitted.".format(d.id))

    if num_created == 1:
        msg = "QC Job has been set up for execution (product: {:s}).".format(product_ident)
    else:
        msg = "{:d} QC Jobs have been set up for execution (product: {:s}).".format(num_created, product_ident)

    result = {"num_created": num_created, "status": "OK", "message": msg}
    return JsonResponse(result)

def pull_job(request):
    try:
        token = request.GET.get("token")
        if not auth_worker(token):
            return HttpResponse(status=401)
    except:
        return HttpResponse(status=400)
    worker_url = "http://{:s}:{:d}/".format(request.META["REMOTE_ADDR"], WORKER_PORT)
    job = models.pull_job(worker_url)
    if job is None:
        response = None
    else:
        response = {"job_uuid": job.job_uuid,
                    "product_ident": job.product_ident,
                    "username": job.delivery.user.username,
                    "filename": job.delivery.filename,
                    "skip_steps": job.skip_steps}
    return JsonResponse(response, safe=False)


def get_chunk_name(uploaded_filename, chunk_number):
    return uploaded_filename + "_part_{:03d}".format(chunk_number)

def merge_uploaded_chunks(chunk_paths, target_filepath):
    with open(str(target_filepath), "ab+") as target_file:
        for stored_chunk_filepath in chunk_paths:
            stored_chunk_file = open(str(stored_chunk_filepath), "rb")
            target_file.write(stored_chunk_file.read())
            stored_chunk_file.close()
            stored_chunk_filepath.unlink()
    target_file.close()
    logger.debug("Uploaded file saved to: " + str(target_filepath))


def remove_old_chunks(chunks_dir):
    old_chunks = [chunk for chunk in chunks_dir.iterdir() if chunk.is_file()]
    for old_chunk in old_chunks:
        try:
            old_chunk.unlink()
        except:
            pass


def uploaded_delivery_file_exists(filename, user_id):
    """
    Helper function used by resumable_upload.
    :param filename: the uploaded .zip file name.
    :param username: the user id.
    :return: Returns: an error message if delivery with same filename and username already exists in the DB.
    """
    existing_deliveries = models.Delivery.objects.filter(
        filename=filename, user_id=user_id).exclude(is_deleted=True)
    if existing_deliveries.count() > 0:
        logger.info("Upload rejected: file {} already exists for user_id={}".format(filename, user_id))

        file_exists_message = "A file named {} already exists. \
                            If you want to replace the file, please delete if first.".format(filename)
        return file_exists_message


@csrf_exempt
def resumable_upload(request):
    if request.method == "GET":
        resumableIdentifier = str(request.GET.get("resumableIdentifier"))
        resumableFilename = str(request.GET.get("resumableFilename"))
        resumableChunkNumber = int(request.GET.get("resumableChunkNumber"))

        if not resumableIdentifier or not resumableFilename or not resumableChunkNumber:
            # Parameters are missing or invalid
            return JsonResponse({"status":"error", "message": "Missing or invalid parameters."}, status=500)

        # path where data should be uploaded to
        user_upload_path = Path(settings.MEDIA_ROOT).joinpath(request.user.username, "uploads")
        if not user_upload_path.exists():
           logger.info("Creating a directory for user uploads: {:s}.".format(str(user_upload_path)))
           user_upload_path.mkdir(parents=True)

        # chunk folder path based on the parameters
        chunks_dir = user_upload_path.joinpath(resumableIdentifier)

        # chunk path based on the parameters
        chunk_file = chunks_dir.joinpath(get_chunk_name(resumableFilename, resumableChunkNumber))
        logger.debug('Getting chunk: %s', chunk_file)

        if chunk_file.is_file():
            # Let resumable.js know this chunk already exists
            return HttpResponse(status=200)
        else:
            # Let resumable.js know this chunk does not exists and needs to be uploaded
            return HttpResponse(status=404)

    if request.method == "POST":
        resumableTotalChunks = int(request.POST.get('resumableTotalChunks'))
        resumableChunkNumber = int(request.POST.get('resumableChunkNumber'))
        resumableFilename = str(request.POST.get('resumableFilename'))
        resumableIdentifier = str(request.POST.get('resumableIdentifier'))


        # Get the chunk data.
        chunk_data = request.FILES.get("file")

        # Make a temp directory for the uploads if needed.
        # The upload directory will be located at INCOMING_DIR/<user>/uploads.
        user_upload_path = Path(settings.MEDIA_ROOT).joinpath(request.user.username, "uploads")
        if not user_upload_path.exists():
            logger.info("Creating a directory for user uploads: {:s}.".format(str(user_upload_path)))
            user_upload_path.mkdir(parents=True, exist_ok=True)

        # Chunk folder path is based on the resumableIdentifier parameter.
        chunks_dir = user_upload_path.joinpath(resumableIdentifier)
        if not chunks_dir.is_dir():
            chunks_dir.mkdir(parents=True, exist_ok=True)

        # If delivery already exists in the DB, return 409 conflict status.
        if resumableChunkNumber == 1:
            conflict_message = uploaded_delivery_file_exists(resumableFilename, request.user.id)
            if conflict_message:
                remove_old_chunks(chunks_dir)
                return HttpResponse(conflict_message, status=409)

        # Simulate delay in chunk processing.
        time.sleep(UPLOADED_CHUNK_PROCESSING_DELAY)

        # Save the chunk data.
        chunk_name = get_chunk_name(resumableFilename, resumableChunkNumber)
        chunk_filepath = chunks_dir.joinpath(chunk_name)

        fs = FileSystemStorage(str(chunk_filepath.parent))
        fs.save(chunk_filepath.name, chunk_data)
        logger.info("Saved chunk: " + chunk_filepath.name)

        # Check if the upload is complete.
        chunk_paths = [chunks_dir.joinpath(get_chunk_name(resumableFilename, x)) for x in
                       range(1, resumableTotalChunks + 1)]
        upload_complete = all([p.is_file() for p in chunk_paths])

        # Combine all the chunks to create the final file.
        if upload_complete:

            # If delivery already exists in the DB, return 409 conflict status.
            conflict_message = uploaded_delivery_file_exists(resumableFilename, request.user.id)
            if conflict_message:
                remove_old_chunks(chunks_dir)
                return HttpResponse(conflict_message, status=409)

            # Uploaded file will be copied to INCOMING_DIR/{USERNAME}/{FILENAME}.
            user_incoming_path = Path(settings.MEDIA_ROOT).joinpath(request.user.username)
            if not user_incoming_path.exists():
                logger.info("Creating a directory for user-incoming files: {:s}.".format(str(user_incoming_path)))
                user_incoming_path.mkdir(parents=True, exist_ok=True)
            target_filepath = user_incoming_path.joinpath(resumableFilename)
            merge_uploaded_chunks(chunk_paths, target_filepath)

            # Assign product description based on product ident.
            # Typically, the product ident is used as the zip filename prefix.
            product_ident = guess_product_ident(target_filepath)
            logger.debug(product_ident)
            product_description = find_product_description(product_ident)

            # Register the uploaded file as a new delivery in the database.
            d = models.Delivery()
            d.filename = target_filepath.name
            d.filepath = user_incoming_path
            d.size_bytes = target_filepath.stat().st_size
            d.product_ident = product_ident
            d.product_description = product_description
            d.date_uploaded = timezone.now()
            d.user = request.user
            d.is_deleted = False
            d.save()
            logger.debug("Delivery object saved successfully to database.")

        return JsonResponse({"status":"ok", "message": "Chunk uploaded successfully."}, status=200)

    else:
        return JsonResponse({"status":"error", "message": "request method must be 'GET' or 'POST'."}, status=500)
