import json
import logging

from pydantic import ValidationError

from services.ai.gemini_client import GeminiClient
from services.ai.schemas import RetailerIntent


logger = logging.getLogger(__name__)


class IntentService:


    SYSTEM_INSTRUCTION = """
You are an intent extraction engine for an FMCG retailer voice assistant.

Understand retailer messages in English, Hindi, and Hinglish.

Your primary responsibility is to identify the retailer's actual intention,
not merely the product mentioned.

INTENT CLASSIFICATION RULES:

1. ORDER_REQUEST:
   Select ORDER_REQUEST when the retailer expresses an intention to purchase,
   buy, order, or place an order for products.

   Examples:
   - I want to order GoldDrop sunflower oil.
   - Please place an order for 10 bottles.
   - I want to buy 500 ml GoldDrop oil.
   - Send me 20 packets.
   - GoldDrop oil ke 10 bottle order karne hain.
   - Mujhe 5 litre oil chahiye, order kar do.

   An explicit purchase intention takes priority over a general
   product inquiry.

2. ORDER_CONFIRMATION:
   Select ORDER_CONFIRMATION only when the retailer explicitly confirms
   an existing pending order.

   Examples:
   - Yes, confirm my order.
   - Go ahead.
   - Haan, order confirm karo.

   Do not classify a new purchase request as ORDER_CONFIRMATION.

3. ORDER_CANCELLATION:
   Select ORDER_CANCELLATION when the retailer explicitly requests
   cancellation of an existing order.

4. PRICE_INQUIRY:
   Select PRICE_INQUIRY when the retailer asks about product pricing,
   rates, or costs without expressing an intention to purchase.

5. SCHEME_INQUIRY:
   Select SCHEME_INQUIRY when the retailer asks about offers,
   discounts, promotional schemes, or quantity-based benefits.

6. STOCK_INQUIRY:
   Select STOCK_INQUIRY when the retailer asks about product availability
   or stock without explicitly requesting a purchase.

7. PRODUCT_LIST_REQUEST:
   Select PRODUCT_LIST_REQUEST when the retailer asks to see,
   list, or browse all available products or the product catalogue.

   Examples:
   - Show me all available products.
   - List all products.
   - What products do you have?
   - Show your product catalogue.
   - Saare products dikhao.
   - Kaun kaun se products available hain?

   Do not require a product name.
   Keep product_mentions empty for general catalogue requests.

8. PRODUCT_INQUIRY:
   Select PRODUCT_INQUIRY when the retailer wants general information
   about a product without expressing an intention to purchase.

9. FOLLOWUP_REQUEST:
   Select FOLLOWUP_REQUEST when the retailer requests a callback
   or asks the agent to contact them later.

10. GREETING:
   Select GREETING for greetings.

11. GOODBYE:
    Select GOODBYE when ending the conversation.

12. COMPLAINT:
    Select COMPLAINT when the retailer reports a problem or expresses
    dissatisfaction.

13. UNKNOWN:
    Select UNKNOWN only when the intention cannot reasonably be identified.

INTENT PRIORITY:

When multiple signals appear in one message, use this priority:

ORDER_CANCELLATION
ORDER_CONFIRMATION
ORDER_REQUEST
FOLLOWUP_REQUEST
COMPLAINT
SCHEME_INQUIRY
PRICE_INQUIRY
STOCK_INQUIRY
PRODUCT_LIST_REQUEST
PRODUCT_INQUIRY
GREETING
GOODBYE
UNKNOWN

PRODUCT EXTRACTION RULES:

1. Extract product names and brand names only when explicitly mentioned
   or clearly identifiable from the retailer's message.
2. Extract quantity only when explicitly mentioned.
3. Extract pack size only when explicitly mentioned.
4. Do not treat generic words such as bottles, packets, pieces,
   products, items, or units as product names.
5. Do not create product mentions from generic scheme questions.
6. If the retailer says "10 bottles", extract quantity 10 only if
   the context clearly indicates that it refers to a product purchase.
7. Do not invent product names, brands, quantities, or pack sizes.
8. Preserve the retailer's original message.

CONFIRMATION RULES:

1. Set confirmation_explicit to true only when the retailer explicitly
   confirms an existing pending order.
2. Purchase expressions such as "I want to order" or "I want to buy"
   are not order confirmations.
3. Never assume an order has been confirmed merely because the retailer
   expresses interest.

CALLBACK RULES:

1. Detect explicit requests for callbacks or follow-ups.
2. Extract the mentioned callback time when possible.
3. Do not invent a callback time.

LANGUAGE RULES:

Return:
- en = English
- hi = Hindi
- mixed = Hindi and English together
- other = another language

CONFIDENCE:

Return a confidence score between 0 and 1.

IMPORTANT BUSINESS RULES:

- Never calculate prices, discounts, inventory, or order totals.
- Never claim that an order has been placed.
- Never assume stock availability.
- Never assume an order is confirmed.

Return only the requested structured JSON matching the supplied schema.
"""


    @classmethod
    def extract(cls, message):

        if not isinstance(message, str) or not message.strip():
            raise ValueError("Message cannot be empty.")

        prompt = f"""
{cls.SYSTEM_INSTRUCTION}

Retailer message:

{message.strip()}
"""

        try:
            raw_response = GeminiClient.generate_structured_response(
                prompt=prompt,
                response_schema=RetailerIntent,
            )

            parsed = json.loads(raw_response)

            result = RetailerIntent.model_validate(parsed)

            # Always preserve the actual incoming message.
            result.original_message = message.strip()

            return {
                "success": True,
                "source": "gemini",
                "data": result.model_dump(),
            }

        except Exception as exc:
            logger.exception(
                "Gemini intent extraction failed: %s",
                str(exc)
            )

            return {
                "success": False,
                "source": "fallback",
                "error": "AI intent extraction is currently unavailable.",
                "data": cls.rule_based_fallback(message),
            }

    @staticmethod
    def rule_based_fallback(message):

        text = message.lower().strip()

        if any(phrase in text for phrase in [
            "list all products",
            "show all products",
            "show me all products",
            "show me all available products",
            "all available products",
            "available products",
            "product catalogue",
            "product catalog",
            "what products do you have",
            "list products",
            "saare products",
            "sabhi products",
            "products dikhao",
        ]):
            intent = "PRODUCT_LIST_REQUEST"

        elif any(word in text for word in [
            "hello", "hi", "hey", "namaste", "नमस्ते"
        ]):
            intent = "GREETING"

        elif any(word in text for word in [
            "price", "rate", "cost", "कीमत", "दाम"
        ]):
            intent = "PRICE_INQUIRY"

        elif any(word in text for word in [
            "scheme", "offer", "discount", "ऑफर", "स्कीम"
        ]):
            intent = "SCHEME_INQUIRY"

        elif any(word in text for word in [
            "stock", "available", "उपलब्ध", "स्टॉक"
        ]):
            intent = "STOCK_INQUIRY"

        elif any(word in text for word in [
            "order", "चाहिए", "मंगवाना", "भेज दो"
        ]):
            intent = "ORDER_REQUEST"

        elif any(word in text for word in [
            "cancel", "रद्द", "कैंसल"
        ]):
            intent = "ORDER_CANCELLATION"

        elif any(word in text for word in [
            "call me", "callback", "बाद में फोन", "बाद में कॉल"
        ]):
            intent = "FOLLOWUP_REQUEST"

        elif any(word in text for word in [
            "bye", "goodbye", "धन्यवाद", "अलविदा"
        ]):
            intent = "GOODBYE"

        else:
            intent = "UNKNOWN"

        language = (
            "hi" if any("\u0900" <= char <= "\u097f" for char in text)
            else "en"
        )

        return {
            "intent": intent,
            "language": language,
            "original_message": message.strip(),
            "normalized_message": message.strip(),
            "product_mentions": [],
            "retailer_name": None,
            "callback_requested": intent == "FOLLOWUP_REQUEST",
            "callback_time_mentioned": None,
            "confirmation_explicit": False,
            "confidence": 0.3,
            "missing_information": [],
        }