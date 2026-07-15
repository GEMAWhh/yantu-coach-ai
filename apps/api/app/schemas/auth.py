from typing import Literal

from pydantic import BaseModel, ConfigDict


class AuthStatusResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    authenticated: Literal[True] = True
    mode: Literal["personal_token"] = "personal_token"
