# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/spider-middleware.html

import os
import logging

from scrapy import signals, Request
from scrapy.exceptions import DontCloseSpider, NotConfigured
from scrapinghub import ScrapinghubClient

# minimum amount of requests to consumer from HCF per iteration
DEFAULT_BATCH_SIZE = 100


class HcfMiddleware:

    @classmethod
    def from_crawler(cls, crawler):
        mware = cls(crawler)
        crawler.signals.connect(mware.spider_idle, signal=signals.spider_idle)
        return mware

    def __init__(self, crawler):
        self.crawler = crawler
        settings = crawler.settings
        current_project_id = os.environ.get('SCRAPY_PROJECT_ID')
        project_id = settings.get('HCF_PROJECT_ID', current_project_id)
        frontier_name = settings.get('HCF_FRONTIER')
        frontier_slot = settings.get('HCF_FRONTIER_SLOT')
        if not project_id or not frontier_name or not frontier_slot:
            raise NotConfigured('Please set HCF settings for the middleware.')
        self.batch_size = settings.getint('HCF_BATCH_SIZE', DEFAULT_BATCH_SIZE)

        self.logger = logging.getLogger(__name__)
        # if auth is not set explicitly, fallback to SH job-level token
        self.client = ScrapinghubClient(settings.get('HCF_AUTH'))
        self.project = self.client.get_project(project_id)
        self.frontier = self.project.frontiers.get(frontier_name)
        self.frontier_slot = self.frontier.get(frontier_slot)

    def process_start_requests(self, start_requests, spider):
        # process initial start requests if any
        for request in start_requests:
            yield request
        # otherwise start consuming from HCF
        if not start_requests:
            for request in self._get_next_requests(spider):
                yield request

    # Signal handlers.

    def spider_idle(self, spider):
        # when spider is idel, the handler is called each 5 secs
        self.logger.debug('Spider is idle, getting new requests..')
        self._schedule_next_requests(spider)
        # prevent the spider from closing regardless of the scheduled reqs
        raise DontCloseSpider

    # Getting next requests from HCF.

    def _schedule_next_requests(self, spider):
        for request in self._get_next_requests(spider):
            self.crawler.engine.crawl(request, spider)

    def _get_next_requests(self, spider):
        """Get a new batch of links from the HCF (ported from scrapy-hcf)."""
        # define handler to convert HCF data entry to Scrapy request
        request_factory = getattr(
            spider, 'create_request_from_hcf_data',
            self.create_request_from_hcf_data
        )
        scheduled_links = 0
        scheduled_batches = []
        for batch in self.frontier_slot.q.iter():
            for url, data in batch['requests']:
                scheduled_links += 1
                yield request_factory(url, data)
            self.logger.debug('Received %d new request(s) from HCF', len(batch))
            scheduled_batches.append(batch['id'])
            # we should finish consuming a batch before stopping
            if scheduled_links >= self.batch_size:
                break
        # the processed batches should be dropped to exclude it from the next
        # iteration. another approach would be to track batches in-progress,
        # ignore it while iterating and delete when all related requests are
        # processed
        if scheduled_batches:
            self._delete_processed_batches(scheduled_batches)
            self.logger.info(
                'Scheduled %d request(s) from %d batch(es).',
                scheduled_links, len(scheduled_batches)
            )

    def _delete_processed_batches(self, batches):
        self.frontier_slot.q.delete(batches)

    def create_request_from_hcf_data(self, url, data):
        """
        The simplest way to convert HCF entry to Scrapy request.
        The approach might be extended if needed by formatting a final url
        depending on the data or pass some data via meta parameter.
        """
        return Request(url=url)
