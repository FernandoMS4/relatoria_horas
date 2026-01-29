from googleapiclient.discovery import build

from src.modules.google_auth import GoogleAuth


class GoogleDriveClient:
    """
    Falta implementar
    """
    def __init__(self, auth: GoogleAuth):
        self.service = build("drive", "v3", credentials=auth.credentials)

    def list_files(self, query: str | None = None, page_size: int = 100) -> list[dict]:
        results = self.service.files().list(
            q=query,
            pageSize=page_size,
            fields="files(id, name, mimeType, modifiedTime)",
        ).execute()
        return results.get("files", [])

    def download_file(self, file_id: str) -> bytes:
        return self.service.files().get_media(fileId=file_id).execute()
