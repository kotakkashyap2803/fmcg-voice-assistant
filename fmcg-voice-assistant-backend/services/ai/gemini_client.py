
import logging

from django.conf import settings
from google import genai
from google.genai import types


logger = logging.getLogger(__name__)


class GeminiClient:

    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            api_key = getattr(settings, "GEMINI_API_KEY", "")

            if not api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY is not configured."
                )

            logger.info("Initializing Gemini client...")

            cls._client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    timeout=300000
                )
            )

        return cls._client

    @classmethod
    def generate_structured_response(
        cls,
        prompt,
        response_schema,
        temperature=0.1,
    ):
        client = cls.get_client()

        model = getattr(
            settings,
            "GEMINI_MODEL",
            "gemini-3.8-flash"
        )

        logger.info("Sending request to Gemini. Model: %s", model)

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=temperature,
                max_output_tokens=800,
            ),
        )

        logger.info("Gemini response received.")

        if not response.text:
            raise RuntimeError(
                "Gemini returned an empty response."
            )

        return response.text
