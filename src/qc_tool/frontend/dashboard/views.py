# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import json
import requests
import time

from pathlib import Path
from xml.etree import ElementTree

from django.conf import settings
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .helpers import parse_status_document

from django.shortcuts import render


def index(request):

    return render(request, 'dashboard/homepage.html', {'show_button': True})


def new_check(request):

    return render(request, 'dashboard/new_check.html')


def get_files(request):
    """
    returns a list of all files that are available for checking.
    The files are loaded from the directory specified in settings.CHECKED_FILES_DIR
    :param request:
    :return: list of the files in JSON format
    """
    base_dir = '/mnt/wps/data/'
    out_list = []
    for root, dirs, files in os.walk(settings.CHECKED_FILES_DIR):
        for filepath in files:
            if filepath.endswith('.tif') or filepath.endswith('.zip'):
                out_list.append(base_dir + filepath)
        for dirpath in dirs:
            if dirpath.endswith('.gdb'):
                out_list.append(base_dir + dirpath)

    return JsonResponse({'files': out_list})


def get_product_types(request):
    """
    returns a list of all product types that are available for checking.
    The files are loaded from the directory specified in settings.PRODUCT_TYPES_DIR
    :param request:
    :return: list of the product types in JSON format
    """
    out_dict = {}
    for root, dirs, files in os.walk(settings.PRODUCT_TYPES_DIR):
        for filepath in files:
            if filepath.endswith('.json') and not os.path.basename(filepath).startswith('_'):
                product_type_name = os.path.splitext(filepath)[0]
                filepath_abs = os.path.join(root, filepath)

                prod_path = Path(filepath_abs)
                prod_info = json.loads(prod_path.read_text())
                prod_desc = prod_info['description']
                out_dict[product_type_name] = prod_desc
    return JsonResponse({'product_types': out_dict})


def get_product_type_details(request, product_type):
    """
    returns a table of details about the product type
    The files are loaded from the directory specified in settings.PRODUCT_TYPES_DIR
    :param request:
    :return: list of the product types in JSON format
    """
    prod_file = os.path.join(settings.PRODUCT_TYPES_DIR, product_type + ".json")
    prod_path = Path(prod_file)
    prod_info = json.loads(prod_path.read_text())
    return JsonResponse({'product_type': prod_info})


def get_product_type_table(request, product_type):
    """
    returns the product type info in suitable format for bootstrap-table
    :param request:
    :param product_type:
    :return:
    """
    prod_file = os.path.join(settings.PRODUCT_TYPES_DIR, product_type + ".json")
    prod_path = Path(prod_file)
    prod_info = json.loads(prod_path.read_text())
    checks = prod_info['checks']
    check_list = []
    for check in checks:
        if 'parameters' in check:
            check_params = repr(check['parameters'])
        else:
            check_params = 'no parameters'
        check_list.append({'check_ident': check['check_ident'],
                         'required': check['required'],
                         'parameters': check_params})
    return JsonResponse({"total": len(checks), "rows": check_list})


def get_checking_sessions(request):
    """
    Returns the list of all checking sessions in JSON format
    :param request:
    :return:
    """

    # first, retrieve the URL's
    status_docs_api = settings.WPS_SERVER + "/status_document_urls"
    resp = requests.get(url=status_docs_api)
    status_doc_urls = resp.json()

    # for each status document, retrieve the info:
    docs = []
    for doc_url in status_doc_urls:
        doc = parse_status_document(doc_url)

        if not doc is None:
            docs.append(doc)

    # sort by start_time in descending order
    docs_sorted = sorted(docs, key=lambda d: d['start_time'], reverse=True)

    out_dict = {"total": len(docs_sorted), "rows": docs_sorted}
    return JsonResponse(out_dict)


@csrf_exempt
def run_wps_execute(request):
    """
    Called from the web app - Run the process
    """
    try:

        product_type_name = request.POST.get("product_type_name")
        filepath = request.POST.get("filepath")
        optional_check_idents = request.POST.get("optional_check_idents")

        if not product_type_name:
            product_type_name = request.GET.get("product_type_name")
        if not filepath:
            filepath = request.GET.get("filepath")
        if not optional_check_idents:
            optional_check_idents = request.GET.get("optional_check_idents")

        # calling cop_sleep (-> change it to run_checks)
        wps_server = settings.WPS_SERVER # "http://192.168.2.72:5000"
        wps_base = wps_server + "/wps?service=WPS&version=1.0.0&request=Execute&identifier=run_checks&lineage=true&DataInputs="
        data_inputs = "filepath={0};product_type_name={1};optional_check_idents={2}".format(filepath, product_type_name, optional_check_idents)

        wps_url = wps_base + data_inputs
        print('Sending WPS Execute request to: ' + wps_url)

        # call the wps and receive response
        r = requests.get(wps_url)
        tree = ElementTree.fromstring(r.text)

        # wait for the response
        time.sleep(2)
        if 'statusLocation' in tree.attrib:

            # process is started
            result = {"status": "OK",
                      "message": "Checking task has started and it is running in the background. " +
                                 "To view status of the task, go to 'Checking Tasks' menu..."}
            js = json.dumps(result)
            return HttpResponse(js, content_type='application/json')
        else:

            # process failed to start
            error_response = {"status": "ERR", "message": "There was an error starting the process. Exception: %s" % r.text}
            js = json.dumps(error_response)
            return HttpResponse(js, content_type='application/json')

    except BaseException as e:
        # general exception handling
        error_response = {"status": "ERR", "message": "WPS server probably does not respond. Error details: %s" % (e)}
        js = json.dumps(error_response)
        return HttpResponse(js, content_type='application/json')