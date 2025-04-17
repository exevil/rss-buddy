import json
from typing import Optional
import logging

from openai import OpenAI

from rss_buddy.models import Item, ProcessedItem
from rss_buddy.protocols import FeedItemProcessor
from rss_buddy.utils.json_encoder import RSSBuddyJSONEncoder

class OpenAIFeedItemProcessor(FeedItemProcessor):
    """
    OpenAI feed item processor.
    """
    def __init__(
            self, 
            openai_api_key: str,
            model: str = "gpt-4o-mini",
            global_filter_criteria: str = "",
            item_filter_criteria: str = "",
            *,
            client: Optional[OpenAI] = None # if provided, client parameters will be ignored
        ):
        self.openai_api_key = openai_api_key
        self.model = model
        self.global_filter_criteria = global_filter_criteria
        self.item_filter_criteria = item_filter_criteria
        self.client = client or OpenAI(api_key=openai_api_key)

    def process(self, item: Item) -> ProcessedItem:
        system_prompt = f"""
        You are an RSS feed filtering assistant. Your task is to evaluate RSS feed items against specific criteria.

        Global filter criteria:
        {self.global_filter_criteria}

        Item filter criteria:
        {self.item_filter_criteria}

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
        {json.dumps(item.__dict__, cls=RSSBuddyJSONEncoder)}
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

        return ProcessedItem(
            item=item, 
            passed_filter=passed_filter
        )