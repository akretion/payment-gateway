# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# pylint: disable=missing-manifest-dependency,invalid-commit
# disable warning on 'vcr' missing in manifest: this is only a dependency for
# dev/tests

import inspect
import os
from vcr import VCR
from os.path import join
import logging
from odoo.addons.component.tests.common import ComponentMixin
from odoo.addons.queue_job.job import Job
from odoo.tests.common import HttpCase
from odoo import api

logging.getLogger("vcr").setLevel(logging.WARNING)


JSON_WEBHOOK_PATH = '/payment-gateway-json-webhook'
HTTP_WEBHOOK_PATH = '/payment-gateway-http-webhook'


def _before_record(request):
    if JSON_WEBHOOK_PATH in request.path \
            or HTTP_WEBHOOK_PATH in request.path:
        return
    return request


class PaymentScenarioType(type):

    def __new__(cls, name, bases, members):
        test_path = members['_test_path']

        # decorate test method with the cassette
        klass = type.__new__(cls, name, bases, members)
        for name, val in inspect.getmembers(klass, inspect.ismethod):
            if name.startswith('test'):
                recorder = VCR(
                    before_record_request=_before_record,
                    record_mode=os.environ.get('VCR_MODE', 'none'),
                    cassette_library_dir=join(test_path, 'fixtures/cassettes'),
                    path_transformer=VCR.ensure_suffix('.yaml'),
                    filter_headers=['Authorization'],
                )
                val = recorder.use_cassette(val)
                setattr(klass, name, val)
        return klass


class HttpComponentCase(HttpCase, ComponentMixin):

    @classmethod
    def setUpClass(cls):
        super(HttpComponentCase, cls).setUpClass()
        cls.setUpComponent()

    # pylint: disable=W8106
    def setUp(self):
        # resolve an inheritance issue (common.TransactionCase does not call
        # super)
        HttpCase.setUp(self)
        self.env = api.Environment(self.registry.test_cr, 1, {})
        ComponentMixin.setUp(self)

    def _init_job_counter(self):
        self.existing_job = self.env['queue.job'].search([])

    @property
    def created_jobs(self):
        return self.env['queue.job'].search([]) - self.existing_job

    def _check_nbr_job_created(self, nbr):
        self.assertEqual(len(self.created_jobs), nbr)

    def _perform_created_job(self):
        for job in self.created_jobs:
            Job.load(self.env, job.uuid).perform()
