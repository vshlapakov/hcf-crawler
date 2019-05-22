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
        project_id = settings.get(
            'HCF_PROJECT_ID', os.environ.get('SCRAPY_PROJECT_ID')
        )
        frontier_name = settings.get('HCF_FRONTIER')
        frontier_slot = settings.get('HCF_FRONTIER_SLOT')
        if not project_id or not frontier_name or not frontier_slot:
            raise NotConfigured('Please set HCF settings for the middleware')

        self.batch_size = settings.getint('HCF_BATCH_SIZE', DEFAULT_BATCH_SIZE)
        self.logger = logging.getLogger(__name__)

        self.client = ScrapinghubClient()
        self.project = self.client.get_project(project_id)
        self.frontier = self.project.frontiers.get(frontier_name)
        self.frontier_slot = self.frontier.get(frontier_slot)

    def process_start_requests(self, start_requests, spider):
        for request in start_requests:
            yield request
        if not start_requests:
            for request in self._get_next_requests():
                yield request

    # Signal handlers.

    def spider_idle(self, spider):
        self.logger.debug('Spider is idle, getting new requests..')
        self._schedule_next_requests(spider)
        raise DontCloseSpider

    # Getting next requests from HCF.

    def _schedule_next_requests(self, spider):
        for request in self._get_next_requests():
            self.crawler.engine.crawl(request, spider)

    def _get_next_requests(self):
        """Get a new batch of links from the HCF (ported from scrapy-hcf)."""
        scheduled_links = 0
        scheduled_batches = []
        for batch in self.frontier_slot.q.iter():
            for url, data in batch['requests']:
                scheduled_links += 1
                yield Request(url=url, meta={'hcf_params': {'qdata': data}})
            self.logger.info('Received %d new request(s) from HCF', len(batch))
            scheduled_batches.append(batch['id'])
            if scheduled_links >= self.batch_size:
                break
        if scheduled_batches:
            self.frontier_slot.q.delete(scheduled_batches)
            self.logger.info(
                'Scheduled %d request(s) from %d batch(es).',
                scheduled_links, len(scheduled_batches)
            )
