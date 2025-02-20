import msgspec


class FixpricePriceData(msgspec.Struct):
    current: float | None
    original: float | None
    sale_tag: str | None

class FixpriceStock(msgspec.Struct):
    in_stock: bool
    count: int

class FixpriceAssets(msgspec.Struct):
    main_image: str
    set_images: list[str]
    view360: list[str]
    video: list[str]

class FixpriceItem(msgspec.Struct):
    timestamp: int
    RPC: str
    url: str
    title: str
    marketing_tags: list[str]
    brand: str
    section: list[str]
    price_data: FixpricePriceData
    stock: FixpriceStock
    assets: FixpriceAssets
    metadata: dict[str, str]
    variants: int | None
