import scrapy
import json
import re
from urllib.parse import quote


class ZillowspiderSpider(scrapy.Spider):
    name = 'zillowspider'
    allowed_domains = ['zillow.com']
    zillow_search_url_template = 'https://zillow.com/search/GetSearchPageState.htm?searchQueryState={0}&wants=' + quote('{"cat1":["listResults"]}')
    start_urls = []

    def __init__(self, max_pages = 10, city_names = None, *args, **kwargs):
        super(ZillowspiderSpider, self).__init__(*args, **kwargs)
        self.max_pages = max_pages
        if city_names != None:
            self.start_urls = ['https://zillow.com/{}/sold/'.format(self.__parse_city_name(name)) for name in city_names.split('|')]
        self.log(', '.join(self.start_urls))
    
    def parse(self, response):
        encodedQuerySearchTerms = response.xpath('//script[@data-zrr-shared-data-key="mobileSearchPageStore"]//text()').re_first(r'^<!--(.*)-->$')
        if encodedQuerySearchTerms != None:
            querySearchTerms = json.loads(encodedQuerySearchTerms)
            queryState = querySearchTerms.get('queryState', {})

            results_url = self.zillow_search_url_template.format(quote(json.dumps(queryState)))

            return response.follow(results_url, callback=self.parse_page_state, cb_kwargs={'query_state': queryState})
    
    def parse_page_state(self, response, page=1, query_state=None):
        self.log('Parsing page ' + str(page))
        data = json.loads(response.text)
        next_page = (page + 1) if (page + 1) <= data.get('cat1', {}).get('searchList', {}).get('totalPages', 0) else None
        for listing in data.get('cat1', {}).get('searchResults', {}).get('listResults', []):
            yield listing.get('hdpData', {}).get('homeInfo')
        
        if next_page != None and next_page <= self.max_pages:
            nextQueryState = query_state.copy()
            nextQueryState.update({"pagination": {"currentPage": next_page}})

            next_page_url = self.zillow_search_url_template.format(quote(json.dumps(nextQueryState)))

            yield scrapy.Request(next_page_url, callback=self.parse_page_state, cb_kwargs={'page': next_page, 'query_state': nextQueryState})

    @staticmethod
    def __parse_city_name(city_name):
        stripped_city_names = re.split('\s+', city_name.strip().lower().replace(',',''))
        return '-'.join(stripped_city_names)

