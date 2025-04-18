import os
import time
import argparse
from dotenv import load_dotenv

from typing import List, Optional
from urllib.robotparser import RobotFileParser

from lxml import html
from playwright.sync_api import sync_playwright
from tqdm import tqdm

from length_enum import Length, parse_enum

load_dotenv()

NASDAQ_REQUEST_DELAY = int(os.getenv("NASDAQ_REQUEST_DELAY"))
NUMBER_OF_COMPANIES = int(os.getenv("NUMBER_OF_COMPANIES"))
NASDAQ_REQUEST_PATH = os.getenv("NASDAQ_REQUEST_PATH")
DATASET_DIRECTORY = os.getenv("DATASET_DIRECTORY")
NASDAQ_REQUEST_LENGTH = Length.ONE_MONTH



# Create necessary directories
def prepare_structure() -> None:
    # Prepare directory for data
    os.makedirs(os.path.join(os.getcwd(), "data"), exist_ok=True)


# Read robots.txt of a website, to check if it allows fetching
def check_if_allowed(main_webpage: str, target: str, browser) -> bool:
    page = browser.new_page()
    page.goto(main_webpage + "/robots.txt")
    rp = RobotFileParser()
    rp.parse(page.text_content("body").splitlines())
    result = rp.can_fetch("*", f"/{target}")
    page.close()
    return result


# Fetch top LIMIT companies on NASDAQ
def scrap_top_companies_symbols(webpage: str, limit: int, browser) -> List[str]:
    page = browser.new_page()
    page.goto(webpage)
    tree = html.fromstring(page.content())
    links = tree.xpath("//table[1]//tr//td[3]//a//text()")
    result = links if limit > len(links) else links[:limit]
    page.close()
    return result


def scrap_history_of_companies(company_symbol: List[str], download_range: Optional[Length] = NASDAQ_REQUEST_LENGTH, browser = None) -> None:
    """Fetch historical data for certain companies from NASDAQ

    Args:
        company_symbol (List[str]): List of symbols of companies
        download_range (Optional[Length], optional): Defines range of the download ( min=Length.ONE_MONTH, max=Length.MAX ). Defaults to Length.ONE_MONTH.
        browser (_type_, optional): Playwright Browser instance. Defaults to None.

    Returns:
        Pulled data is saved to the ./data directory
    """
    context = browser.new_context(accept_downloads=True, user_agent="Non-profit student")
    for company in tqdm(company_symbol, desc="Progress"):
        page = context.new_page()
        webpage = NASDAQ_REQUEST_PATH.replace("COMPANY_SYMBOL", company.lower()).replace("DOWNLOAD_RANGE", download_range)
        page.goto(webpage)
        try:
            page.locator("#onetrust-accept-btn-handler").click(timeout=3000)
        except:
            pass
        try:
            page.locator("button[aria-label='Close']").first.click(timeout=2000)
        except:
            pass
        # # Wait for the download button to be visible
        page.wait_for_selector("button.historical-download", timeout=15000)
        page.wait_for_timeout(1000)
        # page.click("button.historical-download")
        with page.expect_download() as download_info:
            page.get_by_text("Download historical data").click()
        download = download_info.value
        download_path = os.path.join(DATASET_DIRECTORY, f"{company}.csv")
        download.save_as(download_path)
        print(f"Succesfully downloaded {company} historical data to {download_path}.\nAwaiting {NASDAQ_REQUEST_DELAY} seconds for next request (not forced, but asked by owners)")
        page.close()
        time.sleep(NASDAQ_REQUEST_DELAY)
    context.close()
    print("Finished downloading historical data")


def main(limit: int, range: Length):
    prepare_structure()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        if (check_if_allowed("https://www.slickcharts.com", "nasdaq100", browser)):
            print("Pulling top nasdaq companies")
            result = scrap_top_companies_symbols("https://www.slickcharts.com/nasdaq100", limit=limit, browser=browser)
            print("Finished fetching top nasdaq companies")
        scrap_history_of_companies(result, range, browser)
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="scrapper", description="CLI for scrapping data from NASDAQ's top X companies")
    parser.add_argument("--limit", type=int, default=NUMBER_OF_COMPANIES, help="Amount of top companies to pull historical data on")
    parser.add_argument("--range", type=parse_enum(Length), default=NASDAQ_REQUEST_LENGTH, help="Time interval of historical data to pull.\nPossible options are : ONE_MONTH, SIX_MONTH, YTD, YEAR, YEAR_FIVE, MAX")
    args = parser.parse_args()
    main(args.limit, args.range)