
import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from google.genai import types

from apps.orders.models import Order
from .models import (
    Conversation,
    ConversationMessage,
    ConversationCapture,
)
from services.ai.gemini_client import GeminiClient
from django.conf import settings


logger = logging.getLogger(__name__)


def make_json_safe(value):
    """
    Recursively convert values into JSON-serializable types.
    Decimal values become strings to preserve precision.
    """
    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, dict):
        return {
            key: make_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            make_json_safe(item)
            for item in value
        ]

    return value


class ConversationService:

    @staticmethod
    @transaction.atomic
    def start_conversation(retailer, user, channel, language):

        conversation = Conversation.objects.create(
            retailer=retailer,
            handled_by=user,
            channel=channel,
            language=language,
            status=Conversation.Status.ACTIVE
        )

        ConversationMessage.objects.create(
            conversation=conversation,
            sequence=1,
            speaker=ConversationMessage.Speaker.SYSTEM,
            message_type=ConversationMessage.MessageType.TEXT,
            content=f"Conversation started with {retailer.name}."
        )

        return conversation

    @staticmethod
    @transaction.atomic
    def add_message(conversation_id, data):

        conversation = Conversation.objects.select_for_update().get(
            id=conversation_id
        )

        if conversation.status != Conversation.Status.ACTIVE:
            raise ValueError("Cannot add messages to a closed conversation.")

        last_message = (
            ConversationMessage.objects
            .filter(conversation=conversation)
            .order_by("-sequence")
            .first()
        )

        next_sequence = (
            last_message.sequence + 1 if last_message else 1
        )

        extracted_data = make_json_safe(
            data.get("extracted_data", {})
        )

        message = ConversationMessage.objects.create(
            conversation=conversation,
            sequence=next_sequence,
            speaker=data["speaker"],
            message_type=data.get("message_type", "VOICE"),
            content=data["content"],
            confidence=data.get("confidence"),
            intent=data.get("intent", ""),
            extracted_data=extracted_data
        )

        return message

    @staticmethod
    @transaction.atomic
    def add_capture(conversation_id, data):

        conversation = Conversation.objects.select_for_update().get(
            id=conversation_id
        )

        if conversation.status != Conversation.Status.ACTIVE:
            raise ValueError(
                "Cannot capture information in a closed conversation."
            )

        return ConversationCapture.objects.create(
            conversation=conversation,
            variant=data.get("variant"),
            capture_type=data["capture_type"],
            quantity=data.get("quantity"),
            notes=data.get("notes", "")
        )

    @staticmethod
    def _build_completion_context(conversation):
        messages = list(
            conversation.messages.order_by("sequence")
        )

        captures = list(
            conversation.captures.select_related(
                "variant",
                "variant__product"
            ).all()
        )

        orders = list(
            conversation.orders.prefetch_related("items").all()
        )

        followups = list(
            conversation.followups.all()
        )

        transcript = [
            f"{message.speaker}: {message.content}"
            for message in messages
            if message.speaker != ConversationMessage.Speaker.SYSTEM
        ]

        products = []
        for capture in captures:
            if capture.variant_id:
                product_name = capture.variant.product.name
                variant_name = capture.variant.variant_name
            else:
                product_name = capture.notes or "Product discussed"
                variant_name = ""

            products.append({
                "product": product_name,
                "variant": variant_name,
                "quantity": capture.quantity,
                "type": capture.capture_type,
                "notes": capture.notes,
            })

        order_data = []
        for order in orders:
            items = []
            for item in order.items.all():
                items.append({
                    "product": item.product_name,
                    "variant": item.variant_name,
                    "quantity": str(item.quantity),
                    "free_quantity": str(item.free_quantity),
                    "amount": str(item.total_amount),
                })

            order_data.append({
                "order_number": order.order_number,
                "status": order.status,
                "total_amount": str(order.total_amount),
                "items": items,
            })

        followup_data = [
            {
                "title": followup.title,
                "type": followup.followup_type,
                "status": followup.status,
                "due_at": (
                    followup.due_at.isoformat()
                    if followup.due_at else None
                ),
                "description": followup.description,
            }
            for followup in followups
        ]

        return {
            "transcript": transcript,
            "products": products,
            "orders": order_data,
            "followups": followup_data,
        }

    @staticmethod
    def _derive_outcome(conversation, context):
        orders = conversation.orders.all()

        if orders.filter(
            status__in=[
                Order.Status.DRAFT,
                Order.Status.CONFIRMED,
            ]
        ).exists():
            return Conversation.Outcome.ORDER_REQUESTED

        if conversation.followups.exists():
            return Conversation.Outcome.FOLLOWUP_REQUIRED

        captures = conversation.captures.all()

        if captures.exists():
            # if captures.filter(
            #     capture_type=ConversationCapture.CaptureType.INTEREST
            # )
            if captures.filter(capture_type="INTEREST").exists():
                return Conversation.Outcome.INTERESTED

            return Conversation.Outcome.ENQUIRY

        intents = [
            (message.intent or "").upper()
            for message in conversation.messages.all()
        ]

        if any("INTEREST" in intent for intent in intents):
            return Conversation.Outcome.INTERESTED

        if any(
            keyword in intent
            for intent in intents
            for keyword in (
                "PRODUCT",
                "PRICE",
                "STOCK",
                "SCHEME",
                "ENQUIRY",
                "INQUIRY",
            )
        ):
            return Conversation.Outcome.ENQUIRY

        if any(
            "NOT_INTERESTED" in intent
            for intent in intents
        ):
            return Conversation.Outcome.NOT_INTERESTED

        return Conversation.Outcome.NO_ACTION

    @staticmethod
    def _fallback_summary(conversation, context, outcome):
        retailer_name = conversation.retailer.name

        product_names = []
        for product in context["products"]:
            name = product["product"]
            if product["variant"]:
                name = f"{name} ({product['variant']})"

            if name not in product_names:
                product_names.append(name)

        if not product_names:
            for order in context["orders"]:
                for item in order["items"]:
                    name = item["product"]
                    if item["variant"]:
                        name = f"{name} ({item['variant']})"

                    if name not in product_names:
                        product_names.append(name)

        product_text = (
            ", ".join(product_names)
            if product_names
            else "no specific products"
        )

        sentences = [
            f"{retailer_name} had a sales conversation with the assistant.",
            f"The discussion covered {product_text}.",
        ]

        if context["orders"]:
            order_descriptions = []
            for order in context["orders"]:
                order_descriptions.append(
                    f"{order['order_number']} ({order['status']}, "
                    f"₹{order['total_amount']})"
                )

            sentences.append(
                "Order status: " + ", ".join(order_descriptions) + "."
            )
        else:
            sentences.append("No order was created during the conversation.")

        if context["followups"]:
            followup_descriptions = []
            for followup in context["followups"]:
                due = followup["due_at"] or "time not specified"
                followup_descriptions.append(
                    f"{followup['title']} ({due})"
                )

            sentences.append(
                "Follow-up required: "
                + ", ".join(followup_descriptions)
                + "."
            )
        else:
            sentences.append("No follow-up was scheduled.")

        return " ".join(sentences)

    @staticmethod
    def _generate_summary(conversation, context, outcome):
        fallback = ConversationService._fallback_summary(
            conversation,
            context,
            outcome,
        )

        try:
            client = GeminiClient.get_client()

            model = getattr(settings, "GEMINI_MODEL", "gemini-3.8-flash")

            prompt = f"""
You are preparing a concise CRM summary of an FMCG retailer sales
conversation.

Write exactly 3 to 5 short sentences.
Mention:
1. What the retailer asked about.
2. Products, pack sizes and quantities discussed, when available.
3. Whether an order was drafted or confirmed.
4. Any follow-up action and its scheduled time.

Use only the supplied information. Do not invent details, quantities,
prices, confirmations or follow-up dates.

Outcome: {outcome}

Retailer: {conversation.retailer.name}

Conversation data:
{context}
"""

            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=350,
                ),
            )

            summary = (response.text or "").strip()

            if summary:
                return summary

        except Exception:
            logger.exception(
                "Gemini conversation summary failed; using fallback."
            )

        return fallback

    @staticmethod
    @transaction.atomic
    def complete_conversation(conversation_id):

        conversation = Conversation.objects.select_for_update().get(
            id=conversation_id
        )

        if conversation.status != Conversation.Status.ACTIVE:
            raise ValueError("This conversation is already closed.")

        context = ConversationService._build_completion_context(
            conversation
        )

        outcome = ConversationService._derive_outcome(
            conversation,
            context,
        )

        summary = ConversationService._generate_summary(
            conversation,
            context,
            outcome,
        )

        conversation.status = Conversation.Status.COMPLETED
        conversation.outcome = outcome
        conversation.summary = summary
        conversation.ended_at = timezone.now()

        conversation.save(
            update_fields=[
                "status",
                "outcome",
                "summary",
                "ended_at",
                "updated_at",
            ]
        )

        return conversation
