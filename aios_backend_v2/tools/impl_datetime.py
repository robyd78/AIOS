from datetime import datetime
import os

import pytz

from .base import Tool


class GetDateTime(Tool):
    name = "get_datetime"
    description = "Get the current date/time in ISO8601 and a human string."
    permissions = []
    params_schema = {
        "type": "object",
        "properties": {"tz": {"type": "string"}},
        "additionalProperties": False,
    }

    async def run(self, args):
        tz = args.get("tz") or os.getenv("TZ") or "Europe/Madrid"
        try:
            tzinfo = pytz.timezone(tz)
        except Exception:
            tzinfo = pytz.timezone("UTC")
        now = datetime.now(tzinfo)
        return {
            "iso": now.isoformat(),
            "human": now.strftime("%A, %d %B %Y %H:%M"),
        }


tool = GetDateTime()
