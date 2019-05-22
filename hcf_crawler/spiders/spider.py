# -*- coding: utf-8 -*-
import scrapy


class HcfCrawlerSpider(scrapy.Spider):
    name = 'spider'

    def parse(self, response):
        # XXX put your custom parse logic here
        self.logger.info('Handle response %s', response)
