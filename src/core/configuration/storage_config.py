from pydantic import BaseModel


class StorageSettings(BaseModel):
    path: str = "storage"
    public_url: str = "/api/v1/storage"

    @property
    def is_served_locally(self) -> bool:
        return self.public_url.startswith("/")

    def url(self, key: str | None) -> str | None:
        return f"{self.public_url.rstrip('/')}/{key}" if key else None
