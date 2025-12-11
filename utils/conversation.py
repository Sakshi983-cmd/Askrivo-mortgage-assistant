
import re
from datetime import datetime

class ConversationManager:
    def __init__(self):
        self.messages = []  # list of dicts {role, content, ts}
        self.user_data = {}  # parsed fields: monthly_income, property_price, monthly_rent, years_planning

    def add_message(self, role: str, content: str):
        if not self.messages or self.messages[-1]["content"] != content or self.messages[-1]["role"] != role:
            self.messages.append({"role": role, "content": content, "timestamp": datetime.utcnow().isoformat()})

    def get_context(self, last_n: int = 10):
        return "\n".join([f'{m["role"]}: {m["content"]}' for m in self.messages[-last_n:]])

    def extract_user_data(self, text: str):
        # robust numeric extraction
        t = text.lower()
        numbers = re.findall(r'[\d,]+(?:\.\d+)?', text.replace(',', ''))
        nums = [float(n.replace(',', '')) for n in numbers] if numbers else []

        if any(k in t for k in ["income", "salary"]):
            if nums:
                self.user_data["monthly_income"] = nums[0]
        if any(k in t for k in ["price", "aed", "apartment", "flat", "property"]):
            if nums:
                self.user_data["property_price"] = nums[0]
        if "rent" in t:
            if nums:
                self.user_data["monthly_rent"] = nums[0]
        if any(k in t for k in ["year", "years", "stay"]):
            if nums:
                # use first integer-like number for years
                self.user_data["years_planning"] = int(nums[0])

        return self.user_data
