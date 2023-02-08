import scrapy
import re


class MuseumSpider(scrapy.Spider):
    name = 'museum_spider'
    start_urls = ['http://pstrial-2019-12-16.toscrape.com/browse/']

    def parse(self, response):
        """Gets all categories from the main tree, if the category is in the categories_to_scrap list, proceeds to request the category.

        Args:
            response (response): Receive a response object

        Yields:
            response: Send the category link to the subcategory method if the category exists in categories_to_scrap}
        """
        category_to_scrap = ["In Sunsh", "Summertime"]

        categories = response.xpath(
            '//div[@id="subcats"]/div/a')

        for category in categories:
            name = category.xpath(".//h3/text()").get()
            link = category.xpath(".//@href").get()
            current_category = []

            if name in category_to_scrap:
                current_category.append(name)
                yield response.follow(url=link, callback=self.sub_category, cb_kwargs={"visited_category": current_category, "main_categories": category_to_scrap})

    def sub_category(self, response, visited_category, main_categories):
        """Extracts the subcategories of a category from the subcat div, returning a link and adding the name to the list of visited_categories.

        Args:
            response (response): Receive a response object
            visited_category (list): Receive a list of strings containing the visted categories
            main_categories (list) : Receive a list of strings containing the main categories to scrap

        Yields:
            response : Makes a recursive call if there are other subcategories, otherwise it makes a call to the single page function.
        """
        sub_categories = response.xpath('//div[@id="subcats"]/div/a')
        link = response.request.url
        cat_title = response.xpath('//div[@id="body"]/h1/text()').get()[9:]

        if cat_title in main_categories:
            yield response.follow(url=link, callback=self.page_arts_iterator, cb_kwargs={'category_url': link+"?page={}", 'visited_categories': visited_category}, dont_filter=True)

        if sub_categories:
            for sub_category in sub_categories:
                visited_categories = visited_category.copy()
                link = sub_category.xpath(".//@href").get()
                name = sub_category.xpath(".//h3/text()").get()
                visited_categories.append(name)
                yield response.follow(url=link, callback=self.sub_category, cb_kwargs={"visited_category": visited_categories, "main_categories": main_categories})
                yield response.follow(url=link, callback=self.page_arts_iterator, cb_kwargs={'category_url': "http://pstrial-2019-12-16.toscrape.com"+link+"?page={}", "visited_categories": visited_categories}, dont_filter=True)
        elif not sub_categories and cat_title not in main_categories:
            yield response.follow(url=link, callback=self.page_arts_iterator, cb_kwargs={'category_url': link+"?page={}", 'visited_categories': visited_category}, dont_filter=True)

    def page_arts_iterator(self, response, category_url, visited_categories):
        """Iterate all the pages within a category or subcategory.

        Args:
            response (response):Get the response object from the call
            category_url (str): Gets a url in string format
            visited_categories (list): Receive a list of strings containing the visted categories

        Yields:
            Response : Call the page art function to send the page number of a single category or subcategory
        """
        item = response.xpath('//label[@class="item-count"]/text()').get()

        total_items_in_category = int(item[:-5])

        for i in range((total_items_in_category//10)+1):
            yield scrapy.Request(url=category_url.format(i), callback=self.page_art, cb_kwargs={'visited_categories': visited_categories})

    def page_art(self, response, visited_categories):
        """Gets all the arts listed on a page and sends them to the single page method.
        Args:
            response (response): Get the response object from the call
            visited_categories (list): Receive a list of strings containing the visted categories

        Yields:
            response : calls the single page function to scrap a single art in the page
        """
        arts = response.xpath(
            '//div[@id="body"]/div/a[starts-with(@href, "/item")]')

        for art in arts:
            link = art.xpath(".//@href").get()

            yield response.follow(url=link, callback=self.single_page, cb_kwargs={'visited_categories': visited_categories})

    def single_page(self, response, visited_categories):
        """Returns the data of an individual page in dictionary format, if any data is not found, the value is omitted.

        Args:
            response (response): Get the response object from the start_url
            visited_categories (list): Obtain a list of the visited categories to reach the current art page.

        Yields:
            data_to_return (dict) : Dictionary containing the existing data extracted from the page
        """

        current_url = response.request.url

        title = response.xpath(
            '//div[@id="content"]/h1/text()').get()

        image = response.xpath('//div[@id="body"]/img/@src').get()

        artist = response.xpath(
            '//h2[@class="artist"]/text()').get()

        dimensions = response.xpath(
            '//td[contains(text(), "cm)")]/text()').get()

        description = response.xpath(
            '//div[@class="description"]/p/text()').get()

        data_to_return = {
            'art_url': current_url,
            'title': title,
            'image': "http://pstrial-2019-12-16.toscrape.com"+image,
            'artist': artist,
            'description': description,
            'categories': visited_categories,
        }
        if description is None:
            data_to_return.pop('description')

        if not artist:
            data_to_return.pop('artist')

        if dimensions:
            # Compile a pattern to capture float values
            p = re.compile(r'\d+\.\d+')
            # Convert strings to float
            floats = [float(i) for i in p.findall(dimensions)]
            if len(floats) % 3 == 0:
                data_to_return["height"] = floats[0::3]
                data_to_return["width"] = floats[1::3]
                data_to_return["depth"] = floats[2::3]

            elif len(floats) % 2 == 0:
                data_to_return["height"] = floats[0::2]
                data_to_return["width"] = floats[1::2]

        yield data_to_return
