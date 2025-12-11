import logging
import time
import os
from groq import Groq

logger = logging.getLogger(__name__)

class GroqClient:
    def __init__(self, model_name: str = "llama3-70b-8192", max_retries: int = 3):
        """
        Automatically loads GROQ_API_KEY from Streamlit Secrets.
        """
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY missing. Set it in Streamlit → Settings → Secrets.")

        self.client = Groq(api_key=api_key)
        self.model_name = model_name
        self.max_retries = max_retries

        logger.info("Groq client initialized.")

    def generate_with_retry(self, prompt: str, attempt: int = 1) -> str:
        """
        Attempts a Groq completion with retries. Returns assistant text or fallback.
        """
        try:
            logger.info(f"Groq generate attempt {attempt}")

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are Zara, a helpful UAE mortgage assistant."},
                    {"role": "user", "content": prompt},
                ]
            )

            # Preferred response shape
            try:
                return response.choices[0].message["content"]
            except Exception:
                # Fallback shapes
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
