from google.oauth2.service_account import Credentials


class GoogleAuth:

    SCOPES = {
        "sheets": ["https://www.googleapis.com/auth/spreadsheets"],
        "sheets.readonly": ["https://www.googleapis.com/auth/spreadsheets.readonly"],
        "drive": ["https://www.googleapis.com/auth/drive"],
        "drive.readonly": ["https://www.googleapis.com/auth/drive.readonly"],
    }

    def __init__(self, credentials_path: str, scopes: list[str]):
        self.credentials = Credentials.from_service_account_file(
            credentials_path, scopes=scopes
        )

    @classmethod
    def for_sheets(cls, credentials_path: str = "credentials.json", readonly: bool = False):
        key = "sheets.readonly" if readonly else "sheets"
        return cls(credentials_path, cls.SCOPES[key])

    @classmethod
    def for_drive(cls, credentials_path: str = "credentials.json", readonly: bool = False):
        key = "drive.readonly" if readonly else "drive"
        return cls(credentials_path, cls.SCOPES[key])

    @classmethod
    def for_services(cls, credentials_path: str, scopes: list[str]):
        return cls(credentials_path, scopes)
