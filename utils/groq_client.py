import logging
import time
from typing import Optional
from groq import Groq

logger = logging.getLogger(__name__)

class GroqClient:
    def __init__(self, api_key: str, model_name: str = "llama3-70b-8192", max_retries: int = 3):
        self.api_key = api_key
        self.client = Groq(api_key=api_key)
        self.model_name = model_name
        self.max_retries = max_retries
        logger.info("Groq client initialized")

    def generate_with_retry(self, prompt: str, attempt: int = 1) -> str:
        """
        Returns assistant text or a fallback message.
        """
        try:
            logger.info(f"Groq generate attempt {attempt}")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "system", "content": "You are Zara, a helpful UAE mortgage assistant."},
                          {"role": "user", "content": prompt}]
            )
            # Different SDKs may shape response differently; adapt if needed
            # This expects: response.choices[0].message["content"]
            try:
                return response.choices[0].message["content"]
            except Exception:
                # fallback to other common shapes
                return getattr(response.choices[0], "text", str(response))
        except Exception as e:
            logger.error(f"Groq error on attempt {attempt}: {e}", exc_info=True)
            if attempt < self.max_retries:
                wait = 2 ** attempt
                logger.info(f"Retrying after {wait}s")
                time.sleep(wait)
                return self.generate_with_retry(prompt, attempt + 1)
            logger.error("Groq max retries reached; returning fallback message.")
            return "Sorry — I can't reach my language service right now. I can still show calculations."

