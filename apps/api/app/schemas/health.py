from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ok"]
    service: Literal["yantu-coach-api"]
    environment: Literal["dev", "test", "prod"]
    data_root: str
