# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# pylint: disable=missing-manifest-dependency,invalid-commit
# disable warning on 'vcr' missing in manifest: this is only a dependency for
# dev/tests

import os
from vcr import VCR
from os.path import join
import logging
from odoo.addons.component.tests.common import SavepointComponentCase
from odoo.addons.queue_job.job import Job
from openerp import api

logging.getLogger("vcr").setLevel(logging.WARNING)


JSON_WEBHOOK_PATH = '/payment-gateway-json-webhook'
HTTP_WEBHOOK_PATH = '/payment-gateway-http-webhook'


class RecordedScenario(object):

    def _before_record(self, request):
        if JSON_WEBHOOK_PATH in request.path\
                or HTTP_WEBHOOK_PATH in request.path:
            return
        return request

    def _decorate_test(self, test_path):
        recorder = VCR(
            before_record_request=self._before_record,
            record_mode=os.environ.get('VCR_MODE', 'none'),
            cassette_library_dir=join(test_path, 'fixtures/cassettes'),
            path_transformer=VCR.ensure_suffix('.yaml'),
            filter_headers=['Authorization'],
        )
        for test_func in dir(self):
            if test_func.startswith('test'):
                setattr(self, test_func,
                        recorder.use_cassette(getattr(self, test_func)))


# This class should be used if you want to call the odoo webhook during the
# test. Indeed you will stay in the same cursor for all the process
# Do not forget to commit before calling a odoo controller
class HttpSavepointComponentCase(SavepointComponentCase):

    def setUp(self, *args, **kwargs):
        super(HttpSavepointComponentCase, self).setUp(*args, **kwargs)
        self.registry.enter_test_mode()
        self.env = api.Environment(self.registry.test_cr, 1, {})

    def tearDown(self):
        self.registry.leave_test_mode()
        super(HttpSavepointComponentCase, self).tearDown()

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
