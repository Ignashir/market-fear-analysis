import json
import os
import pandas as pd


class Dataset:
    def __init__(self):
        self.COMPANY_HISTORY_PATH = os.path.join(os.getcwd(), "data", "nasdaq")
        self.FEAR_GREED_INDEX_PATH = os.path.join(os.getcwd(), "data", "fear_greed.csv")
        self.SECTORS_PATH = "data/sectors.json"

        self.DIRECTORY = "data/preprocessed"
        self.ONE_BY_ONE_DIRECTORY = os.path.join(os.getcwd(), self.DIRECTORY, "one_by_one.csv")
        self.SECTOR_DIRECTORY = os.path.join(os.getcwd(), self.DIRECTORY, "sector.csv")

        os.makedirs(self.DIRECTORY, exist_ok=True)
    
    def create_company_dataset(self):
        final_dataframe = pd.DataFrame()
        for company in os.listdir(self.COMPANY_HISTORY_PATH):
            comp = pd.read_csv(os.path.join(self.COMPANY_HISTORY_PATH, company))
            comp["High"] = comp["High"].str.replace(r'[\$]', '', regex=True).astype(float)
            comp["Low"] = comp["Low"].str.replace(r'[\$]', '', regex=True).astype(float)
            comp["avg"] = (comp["High"] + comp["Low"]) / 2
            comp["capital"] = comp["avg"] * comp["Volume"]

            comp = comp[['Date', 'capital']].rename(columns={"capital": company.split('.')[0]})
            if final_dataframe.empty:
                final_dataframe = comp
            else:
                final_dataframe = pd.merge(final_dataframe, comp, on='Date', how="outer")
        fear_dataframe = pd.read_csv(self.FEAR_GREED_INDEX_PATH)
        fear_dataframe = fear_dataframe.rename(columns={"date": 'Date'})

        fear_dataframe['Date'] = pd.to_datetime(fear_dataframe["Date"])
        final_dataframe['Date'] = pd.to_datetime(final_dataframe["Date"])
        
        final_dataframe = pd.merge(final_dataframe, fear_dataframe, on='Date', how="inner")
        final_dataframe = final_dataframe.sort_values("Date").reset_index(drop=True)
        final_dataframe.to_csv(self.ONE_BY_ONE_DIRECTORY, index=False)
        return final_dataframe
    
    def create_sector_dataset(self):
        with open(os.path.join(os.getcwd(), self.SECTORS_PATH)) as file:
            sectors = json.load(file)
        companies_dataframe = pd.read_csv(self.ONE_BY_ONE_DIRECTORY)
        sectors_dataframe = pd.DataFrame()
        for sector, companies in sectors.items():
            sector_df = pd.DataFrame(data={"Date": companies_dataframe['Date'], sector: companies_dataframe[companies].sum(axis=1)})
            if sectors_dataframe.empty:
                sectors_dataframe = sector_df
            else:
                sectors_dataframe = pd.merge(sectors_dataframe, sector_df, on='Date', how="outer")
        fear_df = companies_dataframe[["Date", "fear_greed_factor", "rating"]]
        sectors_dataframe = pd.merge(sectors_dataframe, fear_df, on='Date', how="inner")
        sectors_dataframe.to_csv(self.SECTOR_DIRECTORY, index=False)
        return sectors_dataframe

# TODO sprawdzic z tym inner