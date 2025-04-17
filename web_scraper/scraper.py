import pandas as pd
import numpy as np
import requests
from lxml import html
import os
from typing import List
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright



def scrap_companies_symbols(webpage: str, browser) -> List[str]:
    page = browser.new_page()
    page.goto(webpage)
    tree = html.fromstring(page.content())
    links = tree.xpath("//table[1]//tr//td[3]//a//text()")
    return links


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        result = scrap_companies_symbols("https://www.slickcharts.com/nasdaq100", browser)
        browser.close()


if __name__ == "__main__":
    main()