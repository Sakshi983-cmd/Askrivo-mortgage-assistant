class SakhiBot:
    @staticmethod
    def get_message(stage: str) -> str:
        messages = {
            "intro": "Hi! I'm Sakhi — quick feedback: how was your experience with Zara (the mortgage advisor)?",
            "rating": "Please rate from 1 (poor) to 5 (excellent).",
            "improvement": "What could we improve to make this more helpful?",
            "contact": "Would you like us to reach out? Share email or phone (optional).",
            "thanks": "Thanks — we appreciate your time!"
        }
        return messages.get(stage, messages["intro"])

