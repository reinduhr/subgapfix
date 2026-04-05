from typing import List, Dict
import re
import typer

def clean_whisper_text(text: str) -> str:
    """
    Intelligent cleanup for WhisperX ASR output.
    Handles repetitions, contractions, hesitations, and basic grammar issues.
    """
    if not text:
        return text

    text = text.strip()

    # 1. Fix common repetitions (you're you're → you're)
    text = re.sub(r'\b(\w+)\s+\1\b', r'\1', text, flags=re.IGNORECASE)

    # 2. Fix spaced contractions (you 're → you're, we 've → we've, etc.)
    contractions = {
        r"(\w+)\s+'re": r"\1're",
        r"(\w+)\s+'ve": r"\1've",
        r"(\w+)\s+'ll": r"\1'll",
        r"(\w+)\s+'d": r"\1'd",
        r"(\w+)\s+'m": r"\1'm",
    }
    for pattern, replacement in contractions.items():
        text = re.sub(pattern, replacement, text)

    # 3. Fix "Well , you're" → "Well, you're"
    text = re.sub(r'\s+([.,!?])', r'\1', text)
    text = re.sub(r'([.,!?])\s+', r'\1 ', text)

    # 4. Remove filler words / hesitations at start of sentence (common in WhisperX)
    fillers = ['uh', 'um', 'uhh', 'umm', 'hmm', 'ah', 'er', 'like', 'you know']
    for filler in fillers:
        text = re.sub(rf'^\s*{filler}\s*,\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(rf'^\s*{filler}\s+', '', text, flags=re.IGNORECASE)

    # 5. Capitalize first letter of sentence
    if text and text[0].islower():
        text = text[0].upper() + text[1:]

    # 6. Fix double spaces
    text = re.sub(r'\s+', ' ', text)

    # 7. Fix common ASR artifacts
    text = text.replace(" .", ".")
    text = text.replace(" ,", ",")
    text = text.replace(" ?", "?")
    text = text.replace(" !", "!")

    return text.strip()


def cleanup_segments(segments: List[Dict]) -> List[Dict]:
    """Apply intelligent cleanup to all segments."""
    if not segments:
        return []

    cleaned = []
    for seg in segments:
        new_seg = seg.copy()
        if "text" in new_seg:
            new_seg["text"] = clean_whisper_text(new_seg["text"])
        cleaned.append(new_seg)

    typer.echo(f"✅ Intelligent cleanup applied to {len(cleaned)} segments")
    return cleaned