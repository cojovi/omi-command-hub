def join_transcript_segments(segments: list[dict]) -> str:
    parts = []
    for seg in segments:
        text = seg.get("text") or ""
        if text.strip():
            parts.append(text.strip())
    return "\n".join(parts)
