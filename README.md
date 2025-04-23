Analysis of the impact of market attitude on capital distribution according to fear factor.

Project made as a part of Data Mining coursework.

## Preparing dataset

### Before running the script, please include .env file in root directory of the project.
```
NASDAQ_REQUEST_DELAY = 30 (delay time, for NASDAQ it is 30 seconds)
NUMBER_OF_COMPANIES = 100 (amount of top companies to pull form NASDAQ)
NASDAQ_REQUEST_PATH = "https://www.nasdaq.com/market-activity/stocks/COMPANY_SYMBOL/historical?page=1&rows_per_page=100&timeline=DOWNLOAD_RANGE" (path to the desired page to pull data from)
DATASET_DIRECTORY = "data" (directory where all the files will be saved)
```

```console
cd Market_fear
python web_scraper/scraper.py --limit={Desired amount of companies} --range={Desired Range}
```
#### Keep in mind that this process WILL take some time because of the delays that NASDAQ _enforces_ on crawling, which is 30 seconds per request
