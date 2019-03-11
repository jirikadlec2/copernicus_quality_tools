# -*- coding: utf-8 -*-


from pathlib import Path

from django.db import models
from django.utils import timezone

from qc_tool.common import check_running_job
from qc_tool.common import compile_job_report
from qc_tool.common import JOB_RUNNING
from qc_tool.common import JOB_WAITING
from qc_tool.frontend.dashboard.helpers import find_product_description


def pull_job(job_uuid):
    """
    UPDATE deliveries SET last_job_uuid=%s WHERE last_job_uuid IS NULL LIMIT 1
    :return:
    """
    deliveries = Delivery.objects.exclude(product_ident__isnull=True).filter(last_job_uuid__isnull=True)

    if len(deliveries) > 0:
        d = deliveries.first()
        d.last_job_uuid = job_uuid
        d.last_job_status = JOB_RUNNING
        d.save()
        return d
    else:
        return None

class Delivery(models.Model):
    class Meta:
        app_label = "dashboard"

    def __str__(self):
        return "User: {:s} | File: {:s}".format(self.user.username, self.filename)

    def user_directory_path(instance, filename):
        # file will be uploaded to MEDIA_ROOT/<username>/<filename>
        return str(Path(instance.user.username, filename))

    def init_job(self, product_ident, skip_steps):
        self.last_job_uuid = None
        self.last_job_percent = 0
        self.last_job_status = JOB_WAITING
        self.product_ident = product_ident
        self.product_description = find_product_description(product_ident)
        self.skip_steps = skip_steps
        self.save()

    def update_job(self):
        # FIXME: temporarily does nothing
        pass

    def submit(self):
        self.date_submitted = timezone.now()
        self.save()

    def is_submitted(self):
        return self.date_submitted is not None

    user = models.ForeignKey("auth.User", null=True, on_delete=models.CASCADE)
    filename = models.CharField(max_length=500)
    filepath = models.CharField(max_length=500)
    size_bytes = models.IntegerField()
    date_uploaded = models.DateTimeField(default=timezone.now)
    date_submitted = models.DateTimeField(blank=True, null=True)
    product_ident = models.CharField(max_length=64, default=None, blank=True, null=True)
    product_description = models.CharField(max_length=500, default=None, blank=True, null=True)
    skip_steps = models.CharField(max_length=100, default=None, blank=True, null=True)
    last_job_uuid = models.CharField(max_length=32, default=None, blank=True, null=True)
    last_job_status = models.CharField(max_length=64, default=None, blank=True, null=True)
    last_job_percent = models.IntegerField(default=None, blank=True, null=True)
