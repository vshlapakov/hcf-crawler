# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
import os
import hashlib
import logging

from scrapy.exceptions import DontCloseSpider, NotConfigured
from scrapinghub import ScrapinghubClient
from scrapy.utils.request import request_fingerprint
from w3lib.url import canonicalize_url


class HcfCrawlerPipeline(object):

    def __init__(self, crawler):
        settings = crawler.settings
        coll_name = settings.get('TARGET_COLLECTION_NAME')
        coll_type = settings.get('TARGET_COLLECTION_TYPE', 's')
        if not coll_name or not coll_type:
            raise NotConfigured('Please set target collection settings.')
        current_project_id = os.environ.get('SCRAPY_PROJECT_ID')
        project_id = settings.get('HCF_PROJECT_ID', current_project_id)
        self.logger = logging.getLogger(__name__)
        # if auth is not set explicitly, fallback to SH job-level token
        self.client = ScrapinghubClient(settings.get('HCF_AUTH'))
        self.project = self.client.get_project(project_id)
        self.collection = self.project.collections.get(coll_type, coll_name)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def process_item(self, item, spider):
        item_to_export = dict(item)
        if not '_key' in item_to_export:
            fp = hashlib.sha1()
            fp.update(canonicalize_url(item['url']).encode('utf8'))
            item_to_export['_key'] = fp.hexdigest()
        self.collection.set(item_to_export)
        return item
