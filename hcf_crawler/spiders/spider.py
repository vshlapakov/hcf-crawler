# -*- coding: utf-8 -*-
import scrapy
from ..items import HcfCrawlerItem


class HcfCrawlerSpider(scrapy.Spider):
    name = 'spider'

    def parse(self, response):
        self.logger.info('Handle response %s', response)
        yield HcfCrawlerItem(
            url=response.url,
            status=response.status,
            response_size=len(response.body),
        )
