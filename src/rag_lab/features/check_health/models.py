from pydantic import BaseModel


class LiveResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    dependencies: dict[str, str]
