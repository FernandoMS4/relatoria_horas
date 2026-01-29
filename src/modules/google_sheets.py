import gspread
import pandas as pd

from google_auth import GoogleAuth


class GoogleSheetsClient:

    def __init__(self, auth: GoogleAuth):
        self.client = gspread.authorize(auth.credentials)

    def open_sheet(self, sheet_id: str) -> gspread.Spreadsheet:
        return self.client.open_by_key(sheet_id)

    def list_worksheets(self, sheet_id: str) -> list[str]:
        sheet = self.open_sheet(sheet_id)
        return [ws.title for ws in sheet.worksheets()]

    def worksheet_to_df(self, sheet_id: str, worksheet_name: str) -> pd.DataFrame:
        sheet = self.open_sheet(sheet_id)
        data = sheet.worksheet(worksheet_name).get_all_values()
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(columns=data[0], data=data[1:])
