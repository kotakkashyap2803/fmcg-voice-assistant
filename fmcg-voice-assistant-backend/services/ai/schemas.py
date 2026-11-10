
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ProductMention(BaseModel):
    product_name: str = Field(
        description="Product name exactly as understood from the retailer's message."
    )
    brand_name: Optional[str] = Field(
        default=None,
        description="Brand name if explicitly mentioned."
    )
    quantity: Optional[int] = Field(
        default=None,
        description="Number of units requested, if explicitly mentioned."
    )
    pack_size: Optional[str] = Field(
        default=None,
        description="Pack size if explicitly mentioned, such as 500 ml or 1 litre."
    )


class RetailerIntent(BaseModel):
    intent: Literal[
        "GREETING",
        "PRODUCT_LIST_REQUEST",
        "PRODUCT_INQUIRY",
        "PRICE_INQUIRY",
        "SCHEME_INQUIRY",
        "STOCK_INQUIRY",
        "ORDER_REQUEST",
        "ORDER_CONFIRMATION",
        "ORDER_CANCELLATION",
        "FOLLOWUP_REQUEST",
        "COMPLAINT",
        "GOODBYE",
        "UNKNOWN"
    ]

    language: Literal["en", "hi", "mixed", "other"]

    original_message: str

    normalized_message: str = Field(
        description="A concise interpretation of the retailer's message."
    )

    product_mentions: list[ProductMention] = Field(default_factory=list)

    retailer_name: Optional[str] = None

    callback_requested: bool = False

    callback_time_mentioned: Optional[str] = None

    confirmation_explicit: bool = False

    confidence: float = Field(ge=0, le=1)

    missing_information: list[str] = Field(default_factory=list)
