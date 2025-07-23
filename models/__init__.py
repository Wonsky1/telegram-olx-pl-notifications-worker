class Item:
    def __init__(
        self,
        title,
        price,
        image_url,
        created_at,
        location,
        item_url,
        description,
        created_at_pretty,
    ):
        self.title = title
        self.price = price
        self.image_url = image_url
        self.created_at = created_at
        self.created_at_pretty = created_at_pretty
        self.location = location
        self.item_url = item_url
        self.description = description
