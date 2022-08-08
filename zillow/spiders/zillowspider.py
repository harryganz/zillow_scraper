import scrapy
import json
from urllib.parse import quote


class ZillowspiderSpider(scrapy.Spider):
    name = 'zillowspider'
    allowed_domains = ['zillow.com']
    start_urls = ['https://zillow.com/sandy-springs-ga/sold/']
    zillow_search_url_template = 'https://zillow.com/search/GetSearchPageState.htm?searchQueryState={0}&wants=' + quote('{"cat1":["listResults"]}')

    def __init__(self, max_pages = 10, *args, **kwargs):
        super(ZillowspiderSpider, self).__init__(*args, **kwargs)
        self.max_pages = max_pages
        self.queryState = None
    
    def parse(self, response):
        encodedQuerySearchTerms = response.xpath('//script[@data-zrr-shared-data-key="mobileSearchPageStore"]//text()').re_first(r'^<!--(.*)-->$')
        if encodedQuerySearchTerms != None:
            querySearchTerms = json.loads(encodedQuerySearchTerms)
            if self.queryState == None:
                self.queryState = querySearchTerms.get('queryState', {})

            results_url = self.zillow_search_url_template.format(quote(json.dumps(self.queryState)))

            return response.follow(results_url, callback=self.parse_page_state)
    
    def parse_page_state(self, response, page=1):
        self.log('Parsing page ' + str(page))
        data = json.loads(response.text)
        next_page = (page + 1) if (page + 1) <= data.get('cat1', {}).get('searchList', {}).get('totalPages', 0) else None
        for listing in data.get('cat1', {}).get('searchResults', {}).get('listResults', []):
            yield listing.get('hdpData', {}).get('homeInfo')
        
        if next_page != None and next_page <= self.max_pages:
            queryState = self.queryState.copy()
            queryState.update({"pagination": {"currentPage": next_page}})

            next_page_url = self.zillow_search_url_template.format(quote(json.dumps(queryState)))

            yield scrapy.Request(next_page_url, callback=self.parse_page_state, cb_kwargs={'page': next_page})



    


        
