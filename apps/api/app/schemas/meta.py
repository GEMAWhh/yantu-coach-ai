from typing import Literal

from pydantic import BaseModel, ConfigDict


class ApiMetaResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    service: Literal["yantu-coach-api"]
    api_version: Literal["v1"]
    contract_version: Literal["contract-v1"]
    environment: Literal["dev", "test", "prod"]
    features: list[str]


class VersionCheckResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ok"]
    contract_version: Literal["contract-v1"]
