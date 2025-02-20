import msgspec

import scrapy
from scrapy.http import Request, Response
from scrapy.selector.unified import SelectorList

from .items import FixpriceItem, FixpricePriceData, FixpriceStock, FixpriceAssets
from datetime import datetime


class FixpriceSpider(scrapy.Spider):
    name = "Fixprice"
    allowed_domains = [ "fix-price.com" ]
    start_urls = [ 
        "https://fix-price.com/catalog/kosmetika-i-gigiena/ukhod-za-polostyu-rta",
        "https://fix-price.com/catalog/kantstovary/tetradi-i-bloknoty",
        "https://fix-price.com/catalog/seychas-pokupayut"
    ]
    custom_settings = {
        "FEED_EXPORT_ENCODING": "utf-8"
    }
    

    def start_requests(self):
        cookies = {
            'i18n_redirected': 'ru',
            'skip-city': 'true',
            'locality': u'%7B%22city%22%3A%22%D0%95%D0%BA%D0%B0%D1%82%D0%B5%D1%80%D0%B8%D0%BD%D0%B1%D1%83%D1%80%D0%B3%22%2C%22cityId%22%3A55%2C%22longitude%22%3A60.597474%2C%22latitude%22%3A56.838011%2C%22prefix%22%3A%22%D0%B3%22%7D',
        }
        for url in self.start_urls:
            yield Request(url, dont_filter = True, cookies = cookies)

    def detail_product(self, response: Response):
        ProductBlock: SelectorList = response.css(".product")
        InfoBlock: SelectorList = ProductBlock.css('div[itemscope="itemscope"]')
        Images: list[str] =  response.css("div.swiper-slide > img::attr(src)").getall()

        CurrentPrice: float = None
        OriginalPrice: float = None
        DisCount: int = None
        Stock: bool = True
        Count: int = 0

        PriceBlock: SelectorList = InfoBlock.css("* > .price-in-cart")
        if PriceBlock.get():
            OriginalPrice = float(PriceBlock.css(".regular-price::text").get().replace("₽", "").strip())
            if SalePrice := PriceBlock.css(".special-price::text").get():
                CurrentPrice = float(SalePrice.replace("₽", "").strip())
                DisCount = CurrentPrice / OriginalPrice * 100
        else:
            Stock = False

        Metadata = response.css('p.property').css('span::text').getall()
        if len(Metadata) % 2 == 1:
            Metadata = Metadata[1:]

        Metadata = { Metadata[i].strip(): Metadata[i + 1].strip() for i in range(0, len(Metadata), 2) }
 
        Metadata["__description"] = InfoBlock.css(".description::text").get()
        Metadata["Бренд"] = response.css('p.property').css('a.link::text').get()

        Item: FixpriceItem = FixpriceItem(
            int(round(datetime.now().timestamp())),
            Metadata["Код товара"],
            response.url,
            response.css('h1.title::text').get(),
            response.css('p.special-auth::text').get(),
            Metadata["Бренд"],
            response.url.split('/')[-2],
            FixpricePriceData(
                CurrentPrice if DisCount else OriginalPrice,
                OriginalPrice,
                f"Скидка {DisCount}%" if DisCount else None
            ),
            FixpriceStock(Stock, Count),
            FixpriceAssets(
                response.css('img.zoom::attr(src)').get(),
                Images,
                [], []
            ),
            Metadata,
            None
        )

        return msgspec.to_builtins(Item)
 

    def current_page_parse(self, response: Response):
        entities = response.css('div.product__wrapper')

        if len(entities) == 0:
            self.logger.info('Товаров для парсинга закончились!')
            raise scrapy.exceptions.CloseSpider()

        for i in entities:
            url_part = (
                i.css('div.product__wrapper')[0].css('a::attr(href)').get()
            )
            next_page = response.urljoin(url_part)
            yield Request(next_page, callback=self.detail_product)

    def parse(self, response: Response):
        self.logger.info(f'Город {response.css(".city > div > .geo::text").get()}')
    
        current_page = response.meta.get('page', 1)
        pagination = f'?page={current_page + 1}'

        next_page_url = response.urljoin(pagination)

        yield Request(
            next_page_url, callback=self.parse, meta={'page': current_page + 1}
        )

        yield from self.current_page_parse(response)
