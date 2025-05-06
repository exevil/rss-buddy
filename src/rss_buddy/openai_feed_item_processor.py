from typing import Optional
import logging

from openai import OpenAI
from pydantic import BaseModel

from models import Item

class OpenAIFeedItemProcessor:
    """
    OpenAI feed item processor.
    """
    def __init__(
            self, 
            openai_api_key: str,
            global_filter_criteria: Optional[str] = None,
            model: str = "gpt-4o-mini",
            item_filter_criteria: Optional[str] = None,
            *,
            client: Optional[OpenAI] = None # if provided, client parameters will be ignored
        ):
        self.openai_api_key = openai_api_key
        self.model = model
        self.global_filter_criteria = global_filter_criteria
        self.item_filter_criteria = item_filter_criteria
        self.client = client or OpenAI(api_key=openai_api_key)

    def is_passed_filter(self, item: Item) -> bool:
        # Build the filter criteria.
        filter_criteria = ""
        if self.global_filter_criteria:
            filter_criteria += f"Global filter criteria: {self.global_filter_criteria}\n"
        if self.item_filter_criteria:
            filter_criteria += f"Item filter criteria: {self.item_filter_criteria}\n"

        if not filter_criteria:
            logging.warning("No filter criteria provided, item will pass the filter")
            return True

        system_prompt = f"""
        You are an RSS feed filtering assistant. Your task is to evaluate RSS feed items against specific criteria.

        {filter_criteria}

        Instructions:
        1. Analyze the RSS feed item provided to you
        2. Determine if the item matches the filter criteria
        3. Return ONLY a single integer as your response:
           - Return 1 if the item matches the criteria and should be included
           - Return 0 if the item does not match the criteria and should be excluded

        <example_response>
        1
        </example_response>
        """

        user_prompt = f"""
        Evaluate this RSS feed item against the filter criteria:
        <item_to_filter>
        {item.model_dump_json()}
        </item_to_filter>
        """

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        # Validate the response
        completion_text = ""
        if not completion.choices[0].message.content:
            logging.error(f"No content in the response from OpenAI, item: {item.title} will pass the filter")
            completion_text = "1"
        else:
            completion_text = completion.choices[0].message.content.strip()
        
        # Convert the response to a boolean
        passed_filter = False
        match completion_text:
            case "0":
                passed_filter = False
            case "1":
                passed_filter = True
            case _:
                # If the response is not 0 or 1, we will assume that the item will pass the filter
                logging.error(f"Invalid response from OpenAI: {completion_text}, item: {item.title} will pass the filter")
                passed_filter = True

        return passed_filter