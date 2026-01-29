from google_auth import GoogleAuth
from google_sheets import GoogleSheetsClient


class GSGoldenBagres:
    def __init__(self, sheet_id: str, worksheet: str,show_ = bool ):
        auth = GoogleAuth.for_sheets()
        self.sheets = GoogleSheetsClient(auth)
        self.sheet_id = sheet_id
        self.worksheet = worksheet
        self.show_ = show_

    def start(self):
        worksheets = self.sheets.list_worksheets(self.sheet_id)

        df = self.sheets.worksheet_to_df(self.sheet_id, self.worksheet)
        if self.show_ == True:
            print(worksheets)
            print(df)
        return df


if __name__ == '__main__':
    sid = '1ej9meDW8js9sPvqylB9eNbNLp3-phJlb7UE8j_BPvFk'
    client = GSGoldenBagres(sheet_id=sid, worksheet='HORAS',show_=True)
    client.start()
