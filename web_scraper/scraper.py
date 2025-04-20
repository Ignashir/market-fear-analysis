import os
import time
import argparse
import json
import httpx
import asyncio
import pandas as pd
from datetime import date, datetime
from collections import defaultdict
from dotenv import load_dotenv

from typing import List, Optional
from urllib.robotparser import RobotFileParser

from lxml import html
from playwright.async_api import async_playwright
from tqdm.asyncio import tqdm

from length_enum import Length, parse_enum

load_dotenv()

NASDAQ_REQUEST_DELAY = int(os.getenv("NASDAQ_REQUEST_DELAY"))
NUMBER_OF_COMPANIES = int(os.getenv("NUMBER_OF_COMPANIES"))
NASDAQ_REQUEST_PATH = os.getenv("NASDAQ_REQUEST_PATH")
DATASET_DIRECTORY = os.getenv("DATASET_DIRECTORY")
NASDAQ_DOWLNOAD = os.path.join(DATASET_DIRECTORY, "nasdaq")

NASDAQ_REQUEST_LENGTH = Length.ONE_MONTH



# Create necessary directories
def prepare_structure() -> None:
    # Prepare directory for data from nasdaq
    os.makedirs(os.path.join(os.getcwd(), NASDAQ_DOWLNOAD), exist_ok=True)


# Read robots.txt of a website, to check if it allows fetching
async def check_if_allowed(main_webpage: str, target: str, browser) -> bool:
    page = await browser.new_page()
    await page.goto(main_webpage + "/robots.txt")
    rp = RobotFileParser()
    rp.parse((await page.text_content("body")).splitlines())
    result = rp.can_fetch("*", f"/{target}")
    await page.close()
    return result


# Fetch top LIMIT companies on NASDAQ
async def scrap_top_companies_symbols(webpage: str, limit: int, browser) -> List[str]:
    page = await browser.new_page()
    await page.goto(webpage)
    tree = html.fromstring(await page.content())
    links = tree.xpath("//table[1]//tr//td[3]//a//text()")
    result = links if limit > len(links) else links[:limit]
    await page.close()
    return result


async def scrap_history_of_companies(company_symbol: List[str], download_range: Optional[Length], browser = None) -> None:
    """Fetch historical data for certain companies from NASDAQ

    Args:
        company_symbol (List[str]): List of symbols of companies
        download_range (Optional[Length], optional): Defines range of the download ( min=Length.ONE_MONTH, max=Length.MAX ). Defaults to Length.ONE_MONTH.
        browser (_type_, optional): Playwright Browser instance. Defaults to None.

    Returns:
        Pulled data is saved to the ./data directory
    """
    try:
        context = await browser.new_context(accept_downloads=True, user_agent="Non-profit student")
        for company in tqdm(company_symbol, desc="Progress"):
            try:
                page = await context.new_page()
                webpage = NASDAQ_REQUEST_PATH.replace("COMPANY_SYMBOL", company.lower()).replace("DOWNLOAD_RANGE", download_range)
                await page.goto(webpage)
                try:
                    await page.locator("#onetrust-accept-btn-handler").click(timeout=3000)
                except:
                    pass
                try:
                    await page.locator("button[aria-label='Close']").first.click(timeout=2000)
                except:
                    pass
                # Wait for the download button to be visible
                await page.wait_for_selector("button.historical-download", timeout=15000)
                await page.wait_for_timeout(1000)
                async with page.expect_download() as download_info:
                    await page.get_by_text("Download historical data").click()
                download = await download_info.value
                download_path = os.path.join(NASDAQ_REQUEST_PATH, f"{company}.csv")
                await download.save_as(download_path)
                print(f"Succesfully downloaded {company} historical data to {download_path}.\nAwaiting {NASDAQ_REQUEST_DELAY} seconds for next request (not forced, but asked by owners)")
            finally:
                await page.close()
                await asyncio.sleep(NASDAQ_REQUEST_DELAY)
    finally:
        await context.close()
    print("Finished downloading historical data")


def save_to_json(content: dict[str, List[str]]) -> None:
    with open(os.path.join(DATASET_DIRECTORY, "sectors.json"), 'w') as file:
        json.dump(content, file, indent=4)


async def match_company_to_sector(company_symbols: List[str], browser) -> None:
    print("Begin Matching sectors to companies")
    page = await browser.new_page()
    sectors = defaultdict(list)
    for company in company_symbols:
        webpage = "https://stockanalysis.com/stocks/COMPANY_SYMBOL/company/"
        webpage = webpage.replace("COMPANY_SYMBOL", company.lower())
        await page.goto(webpage)
        tree = html.fromstring(await page.content())
        # Fetch only the sector of the company
        sector = tree.xpath("//table[1]//tr[5]//td[2]//a//text()")[0]
        sectors[sector].append(company)
    await page.close()
    save_to_json(sectors)
    print("Finished Matching sectors to companies")



async def fetch_fear_and_greed_index():
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    header = {
        "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    }
    print("Begin Fetching fear & greeed index")
    async with httpx.AsyncClient(headers=header) as client:
        data = (await client.get(url, headers=header)).json()["fear_and_greed_historical"]
    fear = pd.DataFrame(data["data"])
    fear["x"] = fear["x"].apply(lambda ordinal: date.fromtimestamp(int(ordinal) // 1000))
    fear.rename({"x": "date", "y": "fear_greed_factor"}, axis=1, inplace=True)
    fear.to_csv(os.path.join(DATASET_DIRECTORY, "fear_greed.csv"))
    print("Finished Fetching fear & greeed index")


async def main(limit: int, range: Length):
    prepare_structure()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        # Scrape TOP limit companies from https://www.slickcharts.com/nasdaq100
        if (await check_if_allowed("https://www.slickcharts.com", "nasdaq100", browser)):
            print("Pulling top nasdaq companies")
            result = await scrap_top_companies_symbols("https://www.slickcharts.com/nasdaq100", limit=limit, browser=browser)
            print("Finished fetching top nasdaq companies")

        # Download history for each company from previous step
        hist = asyncio.create_task(scrap_history_of_companies(result, range, browser))
        
        # Fetch Sectors for each company
        matching = asyncio.create_task(match_company_to_sector(result, browser))
        
        # Fetch Fear&Greed Factor
        fear_greed = asyncio.create_task(fetch_fear_and_greed_index())
        await asyncio.gather(hist, matching, fear_greed)
        await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="scrapper", description="CLI for scrapping data from NASDAQ's top X companies")
    parser.add_argument("--limit", type=int, default=NUMBER_OF_COMPANIES, help="Amount of top companies to pull historical data on")
    parser.add_argument("--range", type=parse_enum(Length), default=NASDAQ_REQUEST_LENGTH, help="Time interval of historical data to pull.\nPossible options are : ONE_MONTH, SIX_MONTH, YTD, YEAR, YEAR_FIVE, MAX")
    args = parser.parse_args()
    asyncio.run(main(args.limit, args.range))