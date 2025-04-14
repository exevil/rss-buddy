from datetime import datetime
import json

class RSSBuddyJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for RSSBuddy.
    """
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)
