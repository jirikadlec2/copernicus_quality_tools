# from django.conf.urls import url
from django.urls import path
from django.urls import re_path
from dashboard import views

urlpatterns = [
    path("", views.files, name="files"),
    path("jobs/", views.jobs, name="jobs"),

    re_path("data/jobs", views.get_jobs, name="jobs_json"),
    re_path("data/files", views.get_files_json, name="files_json"),
    path("data/product/<product_ident>/", views.get_product_info, name="product_info_json"),
    path("data/product_list/", views.get_product_list, name="product_list_json"),


    path('files/upload', views.file_upload, name='file_upload'),

    path("run_wps_execute", views.run_wps_execute, name="run_wps_execute"),
    path("start_job/<filename>/<product>/", views.start_job, name="start_job"),
    path("result/<job_uuid>/", views.get_result, name="show_result"),
]

from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()