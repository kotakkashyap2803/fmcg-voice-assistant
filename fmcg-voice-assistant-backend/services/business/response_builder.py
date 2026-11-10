
from decimal import Decimal, ROUND_HALF_UP


class ResponseBuilder:

    @staticmethod
    def money(value):
        amount = Decimal(str(value)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )
        return f"₹{amount:,.2f}"

    @staticmethod
    def greeting(language="en"):
        if language == "hi":
            return "नमस्ते! मैं आपकी क्या सहायता कर सकता हूँ?"

        return "Hello! How can I help you today?"

    @staticmethod
    def goodbye(language="en"):
        if language == "hi":
            return "धन्यवाद! आपका दिन शुभ हो।"

        return "Thank you! Have a great day."

    @staticmethod
    def quantity_required(product_name, language="en"):
        if language == "hi":
            return f"आप कितनी मात्रा में {product_name} लेना चाहेंगे?"

        return f"How many units of {product_name} would you like?"

    @staticmethod
    def pack_size_required(product_name, variants, language="en"):
        options = ", ".join(
            str(variant.variant_name) for variant in variants
        )

        if language == "hi":
            return (
                f"{product_name} के लिए उपलब्ध पैक साइज हैं: "
                f"{options}। आप कौन सा पैक लेना चाहेंगे?"
            )

        return (
            f"Available pack sizes for {product_name} are: "
            f"{options}. Which pack would you prefer?"
        )

    @staticmethod
    def product_not_found(product_name, language="en"):
        if language == "hi":
            return f"माफ़ कीजिए, मुझे {product_name} नहीं मिला।"

        return f"Sorry, I couldn't find {product_name} in our catalogue."

    @staticmethod
    def product_details(variant, language="en"):
        price = ResponseBuilder.money(variant.selling_price)

        if language == "hi":
            return (
                f"{variant.product.name}, {variant.variant_name} की "
                f"कीमत {price} है।"
            )

        return (
            f"{variant.product.name}, {variant.variant_name}, "
            f"is available at {price}."
        )

    @staticmethod
    def stock_details(variant, quantity, language="en"):
        if language == "hi":
            return (
                f"{variant.variant_name} के "
                f"{quantity} यूनिट स्टॉक में उपलब्ध हैं।"
            )

        return (
            f"We currently have {quantity} units of "
            f"{variant.variant_name} in stock."
        )

    @staticmethod
    def out_of_stock(product_name, language="en"):
        if language == "hi":
            return f"माफ़ कीजिए, फिलहाल {product_name} स्टॉक में नहीं है।"

        return f"Sorry, {product_name} is currently out of stock."

    @staticmethod
    def scheme_details(offer, language="en"):
        discount = ResponseBuilder.money(offer["discount_amount"])
        final_amount = ResponseBuilder.money(offer["final_amount"])

        if language == "hi":
            return (
                f"{offer['scheme_name']} ऑफर के तहत आपको "
                f"{discount} की छूट मिलेगी। कुल राशि {final_amount} है।"
            )

        return (
            f"You qualify for {offer['scheme_name']}. "
            f"You save {discount}. Your final amount is {final_amount}."
        )

    @staticmethod
    def order_draft_created(order, language="en"):
        total = ResponseBuilder.money(order.total_amount if hasattr(
            order, "total_amount"
        ) else order.total)

        if language == "hi":
            return (
                f"आपका ऑर्डर ड्राफ्ट तैयार है। "
                f"कुल राशि {total} है। क्या आप इसकी पुष्टि करना चाहेंगे?"
            )

        return (
            f"Your order draft is ready. The total is {total}. "
            f"Would you like to confirm your order?"
        )

    @staticmethod
    def order_confirmed(order, language="en"):
        if language == "hi":
            return f"आपका ऑर्डर {order.order_number} सफलतापूर्वक कन्फर्म हो गया है।"

        return f"Your order {order.order_number} has been confirmed successfully."

    @staticmethod
    def order_cancelled(language="en"):
        if language == "hi":
            return "आपका ऑर्डर रद्द कर दिया गया है।"

        return "Your order has been cancelled."

    @staticmethod
    def generic_fallback(language="en"):
        if language == "hi":
            return "माफ़ कीजिए, मैं आपकी बात पूरी तरह समझ नहीं पाया। कृपया दोबारा बताएं।"

        return "Sorry, I couldn't understand that. Could you please repeat?"
