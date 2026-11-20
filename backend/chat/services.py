from django.conf import settings
from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)


class AIProviderUnavailable(Exception):
    pass


def generate_reply(history):
    if not settings.OPENAI_API_KEY:
        last_user_message = next(
            (item["content"] for item in reversed(history) if item["role"] == "user"),
            "",
        )
        return (
            "DEMO MODE — OpenAI is not configured yet. "
            "I received your message: "
            f'"{last_user_message[:240]}". Add OPENAI_API_KEY to the backend '
            "environment to enable live AI responses."
        ), "demo", {"input_tokens": 0, "output_tokens": 0}

    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=45.0, max_retries=1)
    try:
        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            instructions=(
                "You are Syntrix, a concise and helpful AI workspace "
                "assistant. Give clear, practical answers."
            ),
            input=history,
            max_output_tokens=1200,
        )
    except AuthenticationError as exc:
        raise AIProviderUnavailable(
            "OpenAI rejected the configured API key. Check OPENAI_API_KEY in backend/.env."
        ) from exc
    except RateLimitError as exc:
        raise AIProviderUnavailable(
            "OpenAI rate limit or usage quota was reached. Check the OpenAI project usage and billing."
        ) from exc
    except (APITimeoutError, APIConnectionError) as exc:
        raise AIProviderUnavailable(
            "Could not connect to OpenAI in time. Check the network and try again."
        ) from exc
    except APIStatusError as exc:
        raise AIProviderUnavailable(
            "OpenAI could not complete the request. Check the configured model and try again."
        ) from exc
    except APIError as exc:
        raise AIProviderUnavailable(
            "The AI provider could not complete the request. Please try again."
        ) from exc

    if not response.output_text or not response.output_text.strip():
        raise AIProviderUnavailable("The AI provider returned an empty response.")
    content = response.output_text
    usage = response.usage
    return (
        content.strip(),
        "live",
        {
            "input_tokens": usage.input_tokens if usage else 0,
            "output_tokens": usage.output_tokens if usage else 0,
        },
    )
