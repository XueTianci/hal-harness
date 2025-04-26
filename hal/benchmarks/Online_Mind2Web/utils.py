from hal.utils.logging_utils import print_warning

import base64
import io
from openai import (
    APIConnectionError,
    APIError,
    RateLimitError,
    AzureOpenAI,
    OpenAI
)
import os
import backoff

def encode_image(image):
    """Convert a PIL image to base64 string."""
    if image.mode == "RGBA":
        image = image.convert("RGB")
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def extract_predication(response):
    try:
        if "success" in response.lower().split('status:')[1]:
            return 1
        else:
            return 0
    except:
        return 0

class OpenaiEngine():
    def __init__(
        self,
        api_key=None,
        stop=[],
        rate_limit=-1,
        model=None,
        tokenizer=None,
        temperature=0,
        port=-1,
        endpoint_target_uri = "",
        **kwargs,
    ) -> None:
        """Init an engine

        Args:
            api_key (_type_, optional): Auth key from OpenAI. Defaults to None.
            stop (list, optional): Tokens indicate stop of sequence. Defaults to ["\n"].
            rate_limit (int, optional): Max number of requests per minute. Defaults to -1.
            model (_type_, optional): Model family. Defaults to None.
        """
        assert (
                os.getenv("OPENAI_API_KEY", api_key) is not None
        ), "must pass on the api_key or set OPENAI_API_KEY in the environment"
        if os.getenv("OPENAI_API_KEY", api_key) is not None:
            api_key = os.getenv("OPENAI_API_KEY", api_key)
            self.client = OpenAI(
                        api_key=api_key,
                    )
        elif os.getenv("AZURE_OPENAI_API_KEY", api_key) is not None and os.getenv("AZURE_OPENAI_ENDPOINT", endpoint_target_uri) is not None and os.getenv("AZURE_OPENAI_API_VERSION", api_key) is not None:
            api_key = os.getenv("AZURE_OPEN AI_API_KEY", api_key)
            endpoint_target_uri = os.getenv("AZURE_OPENAI_ENDPOINT", endpoint_target_uri)
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", api_key)
            self.client = AzureOpenAI(
                api_key=api_key,
                endpoint=endpoint_target_uri,
                api_version=api_version,
            )
        else:
            raise ValueError("The API key must be set in the environment variable AZURE_OPENAI_API_KEY or OPENAI_API_KEY.")
        self.stop = stop
        self.temperature = temperature
        self.model = model
        # convert rate limit to minmum request interval
        self.request_interval = 0 if rate_limit == -1 else 60.0 / rate_limit

        self.reasoning_model_list = ["o4-mini", "o3-mini", "o1-mini", "o3", "o1"]

    def log_error(details):
        print(f"Retrying in {details['wait']:0.1f} seconds due to {details['exception']}")

    @backoff.on_exception(
        backoff.expo,
        (APIError, RateLimitError, APIConnectionError),
        max_tries=3,
        on_backoff=log_error
    )

    def is_model_in_list(self, model_name: str) -> bool:
        for known_model in self.reasoning_model_list:
            if known_model in model_name:
                return True
        return False

    def generate(self, messages, max_new_tokens=4096, temperature=0, model=None, **kwargs):
        model = model if model else self.model

        if self.is_model_in_list(model):
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_completion_tokens=max_new_tokens,
                # temperature=temperature,
                **kwargs,
            )
        else:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_new_tokens,
                temperature=temperature,
                **kwargs,
            )

        return [choice.message.content for choice in response.choices]
    