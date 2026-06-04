import hashlib
import json
from typing import Any


def segment_hash(session_id: str, segment: dict[str, Any]) -> str:
    key = json.dumps(
        {
            "session_id": session_id,
            "text": segment.get("text"),
            "start": segment.get("start"),
            "end": segment.get("end"),
            "speaker": segment.get("speaker"),
        },
        sort_keys=True,
    )
    return hashlib.sha256(key.encode()).hexdigest()[:32]
