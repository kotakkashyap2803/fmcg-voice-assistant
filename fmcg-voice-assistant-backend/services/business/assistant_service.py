
from decimal import Decimal

from django.db import transaction
from django.db.models import Prefetch

from apps.catalogue.models import Inventory, Product, ProductVariant
from apps.catalogue.services import ProductService
from apps.conversations.models import (
    Conversation,
    ConversationMessage,
)
from apps.conversations.services import ConversationService
from apps.orders.models import Order
from apps.orders.services import OrderService
from apps.schemes.services import SchemeService

from services.ai.intent_service import IntentService
from services.business.product_resolver import ProductResolver
from services.business.response_builder import ResponseBuilder

import re
from datetime import timedelta

from django.utils import timezone

from apps.followups.models import FollowUp
from apps.followups.services import FollowUpService


class AssistantService:

    @staticmethod
    def _language(intent_data, conversation):
        """
        Conversation supports English and Hindi only.
        Mixed-language messages use the conversation's language.
        """
        language = intent_data.get("language", "en")

        if language == "hi":
            return "hi"

        if language == "en":
            return "en"

        return conversation.language

    @staticmethod
    def _save_agent_message(
        conversation,
        message,
        intent,
        confidence,
        extracted_data
    ):
        return ConversationService.add_message(
            conversation.id,
            {
                "speaker": ConversationMessage.Speaker.AGENT,
                "message_type": ConversationMessage.MessageType.TEXT,
                "content": message,
                "confidence": confidence,
                "intent": intent,
                "extracted_data": extracted_data,
            }
        )

    @staticmethod
    def _save_retailer_message(conversation, message, intent_data):
        return ConversationService.add_message(
            conversation.id,
            {
                "speaker": ConversationMessage.Speaker.RETAILER,
                "message_type": ConversationMessage.MessageType.TEXT,
                "content": message,
                "confidence": intent_data.get("confidence"),
                "intent": intent_data.get("intent", "UNKNOWN"),
                "extracted_data": intent_data,
            }
        )

    @staticmethod
    def _get_pending_order(conversation):
        return (
            Order.objects.filter(
                conversation=conversation,
                status=Order.Status.DRAFT
            )
            .prefetch_related("items")
            .order_by("-created_at")
            .first()
        )

    @staticmethod
    def _is_order_confirmation_message(message):
        """
        Detect explicit confirmation of an existing draft order.
        Generic acknowledgements such as 'okay' are not sufficient.
        """

        text = re.sub(
            r"[^\w\s]",
            " ",
            str(message).lower()
        )

        text = re.sub(r"\s+", " ", text).strip()

        confirmation_phrases = [
            "okay place my order",
            "ok place my order",
            "place my order",
            "go ahead and place my order",
            "go ahead place my order",
            "confirm my order",
            "yes confirm my order",
            "yes place my order",
            "proceed with my order",
            "place the order",
            "confirm the order",
            "haan order confirm karo",
            "haan order laga do",
            "order confirm karo",
            "order place kar do",
            "theek hai order laga do",
        ]

        return any(
            phrase in text
            for phrase in confirmation_phrases
        )

    @staticmethod
    def _get_last_agent_message(conversation):
        return (
            ConversationMessage.objects.filter(
                conversation=conversation,
                speaker=ConversationMessage.Speaker.AGENT
            )
            .order_by("-sequence")
            .first()
        )

    @classmethod
    def _get_pending_clarification(cls, conversation):
        """
        Retrieve the clarification state saved in the
        most recent agent response.
        """

        last_message = cls._get_last_agent_message(conversation)

        if not last_message:
            return None

        extracted_data = last_message.extracted_data or {}

        return extracted_data.get("pending_clarification")

    @staticmethod
    def _save_pending_clarification(result_data, clarification):
        """
        Attach pending context to the agent message.
        ConversationService already persists extracted_data.
        """

        result_data["pending_clarification"] = clarification

    @staticmethod
    def _extract_quantity(message):
        """
        Extract a simple positive integer quantity from replies
        such as '10', '10 bottles', or 'I need 10 packs'.
        """

        match = re.search(
            r"\b(\d+)\b",
            str(message)
        )

        if not match:
            return None

        quantity = int(match.group(1))

        return quantity if quantity > 0 else None


    @classmethod
    def _restore_pending_context(cls, conversation, message, intent_data):

        intent = intent_data.get("intent")

        # Do not interpret unrelated requests as clarification answers.
        if intent in [
            "GREETING",
            "GOODBYE",
            "FOLLOWUP_REQUEST",
            "ORDER_CANCELLATION",
            "ORDER_CONFIRMATION",
            "PRODUCT_LIST_REQUEST",
        ]:
            return intent_data

        # If Gemini already extracted a product, retain it.
        # if intent_data.get("product_mentions"):
        #     return intent_data

        if (
            intent == "ORDER_REQUEST"
            and not intent_data.get("product_mentions")
        ):
            last_agent_message = cls._get_last_agent_message(
                conversation
            )

            if last_agent_message:
                previous_data = (
                    last_agent_message.extracted_data or {}
                )

                previous_product = previous_data.get("product") or {}
                previous_variant = previous_data.get("variant") or {}
                previous_offer = previous_data.get("offer") or {}

                variant_id = previous_variant.get("id")
                product_id = previous_product.get("id")
                quantity = previous_offer.get("quantity")

                if variant_id and product_id and quantity:
                    try:
                        quantity = Decimal(str(quantity))
                    except (ValueError, TypeError):
                        quantity = Decimal("0")

                    if quantity > 0:
                        variant = (
                            ProductVariant.objects
                            .select_related("product", "product__brand")
                            .filter(
                                id=variant_id,
                                product_id=product_id,
                                is_active=True,
                                product__is_active=True
                            )
                            .first()
                        )

                        if variant:
                            contextual_data = dict(intent_data)

                            contextual_data["product_mentions"] = [{
                                "product_name": variant.product.name,
                                "brand_name": variant.product.brand.name,
                                "pack_size": (
                                    f"{variant.pack_size} {variant.unit}"
                                ),
                                "quantity": int(quantity),
                            }]

                            return contextual_data

        # If Gemini already extracted a product, retain it.
        if intent_data.get("product_mentions"):
            return intent_data

        contextual_data = dict(intent_data)

        # --------------------------------------------------
        # Recover product context from the previous response
        # --------------------------------------------------

        if intent in [
            "PRODUCT_INQUIRY",
            "PRICE_INQUIRY",
            "STOCK_INQUIRY",
            "SCHEME_INQUIRY",
            "ORDER_REQUEST",
        ]:

            last_agent_message = cls._get_last_agent_message(
                conversation
            )

            if last_agent_message:

                previous_data = last_agent_message.extracted_data or {}
                listed_products = previous_data.get("products", [])

                # Automatically identify the product when exactly
                # one product was listed in the previous response.
                if len(listed_products) == 1:

                    previous_product = listed_products[0]

                    contextual_data["product_mentions"] = [{
                        "product_name": previous_product["name"],
                        "brand_name": previous_product.get("brand"),
                        "quantity": None,
                        "pack_size": None,
                    }]

                    return contextual_data

        # --------------------------------------------------
        # Restore an existing pending clarification
        # --------------------------------------------------

        pending = cls._get_pending_clarification(conversation)

        if not pending:
            return contextual_data

        pending_type = pending.get("type")

        if pending_type == "PRODUCT_VARIANT":

            pack_size = cls._parse_pack_size_from_message(message)

            if not pack_size:
                contextual_data["intent"] = "UNKNOWN"
                contextual_data["product_mentions"] = []
                contextual_data["_preserve_pending_clarification"] = pending
                return contextual_data

            variant = cls._match_pending_variant(
                pending["product_id"],
                pack_size
            )

            if not variant:
                contextual_data["intent"] = "UNKNOWN"
                contextual_data["product_mentions"] = []
                contextual_data["_preserve_pending_clarification"] = pending
                return contextual_data

            contextual_data["intent"] = pending.get(
                "intent", "PRODUCT_INQUIRY"
            )

            contextual_data["product_mentions"] = [{
                "product_name": pending["product_name"],
                "brand_name": pending.get("brand_name"),
                "pack_size": f"{variant.pack_size} {variant.unit}",
                "quantity": pending.get("quantity"),
            }]

        elif pending_type == "QUANTITY":

            quantity = cls._extract_quantity(message)

            if quantity is None:
                contextual_data["intent"] = "UNKNOWN"
                contextual_data["product_mentions"] = []
                contextual_data["_preserve_pending_clarification"] = pending
                return contextual_data

            contextual_data["intent"] = pending.get(
                "intent", "ORDER_REQUEST"
            )

            contextual_data["product_mentions"] = [{
                "product_name": pending["product_name"],
                "brand_name": pending.get("brand_name"),
                "pack_size": pending.get("pack_size"),
                "quantity": int(quantity),
            }]

        return contextual_data


    @staticmethod
    def _parse_pack_size_from_message(message):
        match = re.search(
            r"\b(\d+(?:\.\d+)?)\s*(ml|millilitres?|l|litres?|liters?|g|grams?|kg|kilograms?)\b",
            message.lower()
        )

        if not match:
            return None

        return f"{match.group(1)} {match.group(2)}"

    @staticmethod
    def _match_pending_variant(product_id, pack_size):
        parsed = ProductResolver._parse_pack_size(pack_size)

        if not parsed:
            return None

        requested_size, requested_unit = parsed

        unit_groups = {
            "G": ("MASS", Decimal("1")),
            "GRAM": ("MASS", Decimal("1")),
            "GRAMS": ("MASS", Decimal("1")),
            "KG": ("MASS", Decimal("1000")),
            "ML": ("VOLUME", Decimal("1")),
            "L": ("VOLUME", Decimal("1000")),
            "LTR": ("VOLUME", Decimal("1000")),
            "LITRE": ("VOLUME", Decimal("1000")),
            "LITRES": ("VOLUME", Decimal("1000")),
            "PCS": ("COUNT", Decimal("1")),
            "PACK": ("PACK", Decimal("1")),
            "BOX": ("BOX", Decimal("1")),
        }

        requested_group = unit_groups.get(
            str(requested_unit).upper()
        )

        if not requested_group:
            return None

        requested_base = requested_size * requested_group[1]

        variants = ProductVariant.objects.filter(
            product_id=product_id,
            is_active=True
        )

        for variant in variants:

            variant_group = unit_groups.get(
                str(variant.unit).upper()
            )

            if not variant_group:
                continue

            if variant_group[0] != requested_group[0]:
                continue

            variant_base = (
                Decimal(str(variant.pack_size))
                * variant_group[1]
            )

            if variant_base == requested_base:
                return variant

        return None



    @staticmethod
    def _parse_callback_due_at(callback_time):
        """
        Convert common callback time expressions into an aware datetime.

        Initially supports today/tomorrow, relative hours,
        morning, afternoon, evening, and explicit clock times.
        """
        if not callback_time:
            return None

        value = str(callback_time).strip().lower()

        now = timezone.localtime(timezone.now())

        # Handle relative hours, e.g. "in 2 hours".
        relative_match = re.search(
            r"in\s+(\d+)\s+hours?",
            value
        )

        if relative_match:
            return now + timedelta(
                hours=int(relative_match.group(1))
            )

        # Determine the callback date.
        if any(word in value for word in ["tomorrow", "kal"]):
            callback_date = now.date() + timedelta(days=1)

        elif any(word in value for word in ["today", "aaj"]):
            callback_date = now.date()

        else:
            return None

        # Default times for broad time-of-day expressions.
        if any(word in value for word in [
            "morning", "subah"
        ]):
            hour, minute = 10, 0

        elif any(word in value for word in [
            "afternoon", "dopahar"
        ]):
            hour, minute = 14, 0

        elif any(word in value for word in [
            "evening", "shaam"
        ]):
            hour, minute = 17, 0

        elif any(word in value for word in [
            "night", "raat"
        ]):
            hour, minute = 19, 0

        else:
            hour, minute = 10, 0

        # Override defaults when an explicit time is supplied.
        time_match = re.search(
            r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b",
            value
        )

        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            meridiem = time_match.group(3)

            if hour < 1 or hour > 12 or minute > 59:
                return None

            if meridiem == "pm" and hour != 12:
                hour += 12

            elif meridiem == "am" and hour == 12:
                hour = 0

        due_at = now.replace(
            year=callback_date.year,
            month=callback_date.month,
            day=callback_date.day,
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0
        )

        if due_at <= now:
            return None

        return due_at

    @staticmethod
    def _resolve_product(intent_data):
        mentions = intent_data.get("product_mentions") or []

        if not mentions:
            return None

        # Initial implementation handles one product per message.
        return ProductResolver.resolve(mentions[0])

    @staticmethod
    def _variant_options(product_result):
        variants = product_result.get("variants", [])

        return [
            {
                "id": variant.id,
                "name": variant.variant_name,
                "sku": variant.sku,
                "pack_size": str(variant.pack_size),
                "unit": variant.unit,
                "selling_price": str(variant.selling_price),
            }
            for variant in variants
        ]

    @classmethod
    @transaction.atomic
    def process_message(cls, conversation_id, message, user=None):
        """
        Main orchestration entry point.

        1. Extract retailer intent using Gemini/fallback.
        2. Save retailer message.
        3. Resolve products against the database.
        4. Execute the appropriate business operation.
        5. Save and return the agent response.

        The LLM never calculates business values or directly
        modifies orders or inventory.
        """

        conversation = (
            Conversation.objects.select_for_update()
            .select_related("retailer")
            .get(id=conversation_id)
        )

        if conversation.status != Conversation.Status.ACTIVE:
            raise ValueError("This conversation is not active.")

        if not isinstance(message, str) or not message.strip():
            raise ValueError("Message cannot be empty.")

        message = message.strip()

        extraction = IntentService.extract(message)
        intent_data = extraction["data"]

        # --------------------------------------------------
        # 1. Detect explicit confirmation of an existing draft
        # --------------------------------------------------

        pending_order = cls._get_pending_order(conversation)

        if (
            pending_order
            and cls._is_order_confirmation_message(message)
        ):

            intent_data["intent"] = "ORDER_CONFIRMATION"
            intent_data["confirmation_explicit"] = True

            intent_data["product_mentions"] = []

        # --------------------------------------------------
        # 2. Restore previous clarification context
        # --------------------------------------------------

        intent_data = cls._restore_pending_context(
            conversation,
            message,
            intent_data
        )

        preserved_context = intent_data.pop(
            "_preserve_pending_clarification",
            None
        )

        intent = intent_data.get("intent", "UNKNOWN")
        confidence = intent_data.get("confidence", 0.0)

        language = cls._language(intent_data, conversation)

        # Save the original retailer message before processing.
        cls._save_retailer_message(
            conversation,
            message,
            intent_data
        )

        response = ""
        result_data = {
            "intent": intent,
            "ai_source": extraction.get("source"),
        }

        # preserved_context = intent_data.pop(
        #     "_preserve_pending_clarification",
        #     None
        # )

        if preserved_context:
            cls._save_pending_clarification(
                result_data,
                preserved_context
            )

        if intent == "GREETING":

            response = ResponseBuilder.greeting(language)

        elif intent == "GOODBYE":

            response = ResponseBuilder.goodbye(language)

        elif intent == "PRODUCT_LIST_REQUEST":

            products = Product.objects.filter(
                is_active=True,
                variants__is_active=True,
            ).select_related(
                "brand",
                "category",
            ).prefetch_related(
                Prefetch(
                    "variants",
                    queryset=ProductVariant.objects.filter(
                        is_active=True
                    ).order_by("pack_size"),
                    to_attr="active_variants",
                )
            ).distinct().order_by("name")

            product_list = []

            for product in products:

                variants = []

                for variant in product.active_variants:

                    variants.append({
                        "id": variant.id,
                        "variant_name": variant.variant_name,
                        "sku": variant.sku,
                        "pack_size": str(variant.pack_size),
                        "unit": variant.unit,
                        "selling_price": str(variant.selling_price),
                        "mrp": str(variant.mrp),
                    })

                if variants:

                    product_list.append({
                        "id": product.id,
                        "name": product.name,
                        "brand": product.brand.name,
                        "category": product.category.name,
                        "variants": variants,
                    })

            result_data["products"] = product_list
            result_data["product_count"] = len(product_list)

            result_data["variant_count"] = sum(
                len(product["variants"])
                for product in product_list
            )

            if not product_list:

                response = (
                    "There are currently no active products in our catalogue."
                    if language == "en"
                    else "Hamare catalogue mein filhaal koi active product nahi hai."
                )

            else:

                product_descriptions = []

                for product in product_list:

                    variant_descriptions = []

                    for variant in product["variants"]:

                        variant_descriptions.append(
                            f'{variant["pack_size"]} {variant["unit"]} '
                            f'at Rs. {variant["selling_price"]}'
                        )

                    product_descriptions.append(
                        f'{product["brand"]} {product["name"]}: '
                        + ", ".join(variant_descriptions)
                    )

                response = (
                    "Here are our available products: "
                    + ". ".join(product_descriptions)
                    if language == "en"
                    else "Yeh hamare available products hain: "
                    + ". ".join(product_descriptions)
                )

        elif intent in [
            "PRODUCT_INQUIRY",
            "PRICE_INQUIRY",
            "STOCK_INQUIRY",
            "SCHEME_INQUIRY",
            "ORDER_REQUEST",
        ]:

            product_result = cls._resolve_product(intent_data)

            if not product_result:

                response = (
                    "Which product are you interested in?"
                    if language == "en"
                    else "αñåαñ¬ αñòαÑîαñ¿αñ╕αñ╛ αñòαÑÇαñ£αñ┐αñÅ αñ¼αñ╛αññ αñòαñ░αññ αñ╣αÑêαñé?"
                )

            else:

                result_data["product_resolution"] = product_result[
                    "status"
                ]

                if product_result["status"] == "PRODUCT_NOT_FOUND":

                    response = ResponseBuilder.product_not_found(
                        intent_data.get("product_mentions", [{}])[0].get(
                            "product_name", "that product"
                        ),
                        language
                    )

                elif product_result["status"] in [
                    "VARIANT_REQUIRED",
                    "VARIANT_NOT_FOUND",
                ]:

                    response = ResponseBuilder.pack_size_required(
                        product_result["product"].name,
                        product_result["variants"],
                        language
                    )

                    result_data["available_variants"] = (
                        cls._variant_options(product_result)
                    )

                    mention = (
                        intent_data.get("product_mentions") or [{}]
                    )[0]

                    cls._save_pending_clarification(
                        result_data,
                        {
                            "type": "PRODUCT_VARIANT",
                            "intent": intent,
                            "product_id": product_result["product"].id,
                            "product_name": product_result["product"].name,
                            "brand_name": product_result["product"].brand.name,
                            "quantity": mention.get("quantity"),
                        }
                    )

                elif product_result["status"] == "NO_ACTIVE_VARIANTS":

                    response = product_result["message"]

                elif product_result["status"] == "RESOLVED":

                    variant = product_result["variant"]
                    product = product_result["product"]

                    result_data["product"] = {
                        "id": product.id,
                        "name": product.name,
                        "brand": product.brand.name,
                    }

                    result_data["variant"] = {
                        "id": variant.id,
                        "name": variant.variant_name,
                        "sku": variant.sku,
                        "selling_price": str(variant.selling_price),
                    }

                    if intent == "PRODUCT_INQUIRY":

                        response = ResponseBuilder.product_details(
                            variant,
                            language
                        )

                    elif intent == "PRICE_INQUIRY":

                        response = ResponseBuilder.product_details(
                            variant,
                            language
                        )

                    elif intent == "STOCK_INQUIRY":

                        inventory = ProductService.get_inventory(
                            variant.id
                        )

                        response = ResponseBuilder.stock_details(
                            variant,
                            inventory.quantity_on_hand,
                            language
                        )

                        result_data["stock_quantity"] = str(
                            inventory.quantity_on_hand
                        )

                    elif intent == "SCHEME_INQUIRY":

                        mentions = intent_data.get(
                            "product_mentions", []
                        )

                        quantity = (
                            mentions[0].get("quantity")
                            if mentions else None
                        )

                        if not quantity:

                            response = ResponseBuilder.quantity_required(
                                product.name,
                                language
                            )

                            cls._save_pending_clarification(
                                result_data,
                                {
                                    "type": "QUANTITY",
                                    "intent": "SCHEME_INQUIRY",
                                    "product_name": product.name,
                                    "brand_name": product.brand.name,
                                    "pack_size": (
                                        f"{variant.pack_size} {variant.unit}"
                                    ),
                                }
                            )

                        else:

                            offers_result = SchemeService.calculate_offers(
                                variant.id,
                                int(quantity)
                            )

                            best_offer = offers_result["best_offer"]

                            if best_offer:

                                response = ResponseBuilder.scheme_details(
                                    best_offer,
                                    language
                                )

                                result_data["offer"] = best_offer

                            else:

                                response = (
                                    "There is currently no applicable scheme "
                                    "for this product and quantity."
                                )

                    elif intent == "ORDER_REQUEST":

                        mentions = intent_data.get(
                            "product_mentions", []
                        )

                        quantity = (
                            mentions[0].get("quantity")
                            if mentions else None
                        )

                        if not quantity:

                            response = ResponseBuilder.quantity_required(
                                product.name,
                                language
                            )

                            cls._save_pending_clarification(
                                result_data,
                                {
                                    "type": "QUANTITY",
                                    "intent": "ORDER_REQUEST",
                                    "product_name": product.name,
                                    "brand_name": product.brand.name,
                                    "pack_size": f"{variant.pack_size} {variant.unit}",
                                }
                            )

                        else:

                            pending_order = cls._get_pending_order(
                                conversation
                            )

                            if not pending_order:

                                pending_order = OrderService.create_draft(
                                    retailer_id=conversation.retailer_id,
                                    user=user or conversation.handled_by,
                                    conversation_id=conversation.id,
                                    notes="Created through voice assistant."
                                )

                            OrderService.add_item(
                                order_id=pending_order.id,
                                variant_id=variant.id,
                                quantity=Decimal(str(quantity)),
                                user=user or conversation.handled_by
                            )

                            pending_order.refresh_from_db()

                            response = (
                                ResponseBuilder.order_draft_created(
                                    pending_order,
                                    language
                                )
                            )

                            result_data["order"] = {
                                "id": pending_order.id,
                                "order_number": pending_order.order_number,
                                "status": pending_order.status,
                                "total_amount": str(
                                    pending_order.total_amount
                                ),
                            }

                            ConversationService.add_capture(
                                conversation.id,
                                {
                                    "variant": variant,
                                    "capture_type": "ORDER_INTENT",
                                    "quantity": int(quantity),
                                    "notes": (
                                        f"Draft order {pending_order.order_number}"
                                    ),
                                }
                            )

        elif intent == "ORDER_CONFIRMATION":

            pending_order = cls._get_pending_order(conversation)

            if not pending_order:

                response = (
                    "There is no pending order to confirm."
                    if language == "en"
                    else "αñòαÑïαñëαÑçαñé αñ¼αñ╛αñòαÑÇ αñ¬αÑüαñ╖αÑìαñƒαñ┐ αñ¿αñ╣αÑÇαñé αñ╣αÑêαÑñ"
                )

            elif not intent_data.get("confirmation_explicit"):

                response = (
                    "Please explicitly confirm if you want me to place "
                    "this order."
                )

            else:

                confirmed_order = OrderService.confirm_order(
                    pending_order.id,
                    user or conversation.handled_by
                )

                response = ResponseBuilder.order_confirmed(
                    confirmed_order,
                    language
                )

                result_data["order"] = {
                    "id": confirmed_order.id,
                    "order_number": confirmed_order.order_number,
                    "status": confirmed_order.status,
                    "total_amount": str(
                        confirmed_order.total_amount
                    ),
                }

        elif intent == "ORDER_CANCELLATION":

            pending_order = cls._get_pending_order(conversation)

            if pending_order:

                cancelled_order = OrderService.cancel_order(
                    pending_order.id,
                    user or conversation.handled_by,
                    reason="Cancelled through voice assistant."
                )

                response = ResponseBuilder.order_cancelled(language)

                result_data["order"] = {
                    "id": cancelled_order.id,
                    "order_number": cancelled_order.order_number,
                    "status": cancelled_order.status,
                }

            else:

                response = "There is no pending order to cancel."

        elif intent == "FOLLOWUP_REQUEST":

            callback_time = intent_data.get(
                "callback_time_mentioned"
            )

            due_at = cls._parse_callback_due_at(
                callback_time
            )

            if not due_at:

                response = (
                    "Certainly. When would you like our representative "
                    "to call you? Please specify a date and time."
                )

                result_data["callback_requested"] = True
                result_data["callback_scheduled"] = False
                result_data["callback_time"] = callback_time

            else:

                retailer = conversation.retailer

                assigned_to = (
                    retailer.sales_representative
                    or conversation.handled_by
                )

                followup = FollowUpService.create_followup(
                    data={
                        "retailer": retailer,
                        "conversation": conversation,
                        "assigned_to": assigned_to,
                        "followup_type": FollowUp.FollowUpType.CALL,
                        "priority": FollowUp.Priority.MEDIUM,
                        "title": f"Callback - {retailer.name}",
                        "description": (
                            f"Callback requested by retailer during "
                            f"conversation #{conversation.id}. "
                            f"Original request: {message}"
                        ),
                        "due_at": due_at,
                    },
                    user=user or conversation.handled_by
                )

                formatted_time = timezone.localtime(
                    followup.due_at
                ).strftime("%d %b %Y, %I:%M %p")

                response = (
                    f"Certainly. Your callback has been scheduled "
                    f"for {formatted_time}. Our representative will "
                    f"contact you."
                )

                result_data["callback_requested"] = True
                result_data["callback_scheduled"] = True
                result_data["followup"] = {
                    "id": followup.id,
                    "status": followup.status,
                    "due_at": followup.due_at.isoformat(),
                    "assigned_to": (
                        followup.assigned_to_id
                    ),
                }

        elif intent == "UNKNOWN" and preserved_context:

            if preserved_context.get("type") == "PRODUCT_VARIANT":

                product_result = ProductResolver.resolve({
                    "product_name": preserved_context["product_name"],
                    "brand_name": preserved_context.get("brand_name"),
                })

                if product_result["status"] in [
                    "VARIANT_REQUIRED",
                    "VARIANT_NOT_FOUND",
                ]:

                    response = ResponseBuilder.pack_size_required(
                        product_result["product"].name,
                        product_result["variants"],
                        language
                    )

                    result_data["available_variants"] = (
                        cls._variant_options(product_result)
                    )

                    result_data["pending_clarification"] = preserved_context

                else:
                    response = ResponseBuilder.generic_fallback(language)

            else:
                response = ResponseBuilder.generic_fallback(language)

        else:

            response = ResponseBuilder.generic_fallback(language)

        # Persist the generated agent response.
        cls._save_agent_message(
            conversation=conversation,
            message=response,
            intent=intent,
            confidence=confidence,
            extracted_data=result_data
        )

        return {
            "success": True,
            "conversation_id": conversation.id,
            "intent": intent,
            "language": language,
            "ai_source": extraction.get("source"),
            "response": response,
            "data": result_data,
        }
