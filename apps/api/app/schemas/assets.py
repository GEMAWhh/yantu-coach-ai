from datetime import datetime
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from app.models.asset import Asset

AssetState = Literal["inbox", "organized", "archived", "deleted"]
AssetMimeType = Literal["image/png", "image/jpeg", "application/pdf"]


class AssetUploadRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    original_name: str = Field(min_length=1, max_length=255)
    mime_type: AssetMimeType
    content_base64: str = Field(min_length=1)
    state: Literal["inbox", "organized", "archived"] = "inbox"


class AssetResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    sha256: str
    original_name: str
    storage_path: str
    mime_type: AssetMimeType
    size_bytes: int
    state: AssetState
    reference_count: int

    @classmethod
    def from_model(cls, asset: Asset) -> "AssetResponse":
        return cls(
            id=asset.id,
            version=asset.version,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
            sha256=asset.sha256,
            original_name=asset.original_name,
            storage_path=asset.storage_path,
            mime_type=cast(AssetMimeType, asset.mime_type),
            size_bytes=asset.size_bytes,
            state=cast(AssetState, asset.state),
            reference_count=asset.reference_count,
        )


class AssetContentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: AssetResponse
    content_base64: str


class ResourceCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    asset_id: str = Field(min_length=1)


class ResourceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    resource_type: Literal["asset"]
    asset: AssetResponse

    @classmethod
    def from_asset(cls, asset: Asset) -> "ResourceResponse":
        return cls(id=asset.id, resource_type="asset", asset=AssetResponse.from_model(asset))


class ResourceListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[ResourceResponse]
    total: int
