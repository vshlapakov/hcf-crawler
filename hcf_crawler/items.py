# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class HcfCrawlerItem(scrapy.Item):
    url = scrapy.Field()
    status = scrapy.Field()
    response_size = scrapy.Field()
