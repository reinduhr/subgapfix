import srt
from typing import List
from .language.en.en_US import ABBREVIATIONS_EN
from .language.nl.nl_NL import ABBREVIATIONS_NL

# ====================== CONFIG ======================
SENTENCE_ENDERS = {
    ".", "!", "?", "…", "...",
    ".'", '."', "!'", '!"', "?'", '?"',
    ".\"", "!\"", "?\"", ".'\"",
    "?!", "!?",
    ".)", ".]", ".}",
    "!”", "?”", ".”", "!’", "?’", ".’",
    "…\"", "...\"",
    "!!", "??", "!!!", "???",
}

# ====================== HELPER FUNCTIONS ======================
def get_language_config(lang: str = "en"):
    if lang == "nl":
        ABBREVIATIONS = ABBREVIATIONS_NL
    else:
        ABBREVIATIONS = ABBREVIATIONS_EN
    return ABBREVIATIONS

def is_sentence_end(text: str, lang: str = "en") -> bool:
    """Returns True if the subtitle text ends a real sentence."""
    if not text or not text.strip():
        return False

    cleaned = text.strip()
    lower_cleaned = cleaned.lower()
    words = lower_cleaned.split()
    if not words:
        return False
    last_word = words[-1]

    # 1. Check abbreviations
    ABBREVIATIONS = get_language_config(lang)
    if last_word in ABBREVIATIONS:
        return False

    common_abbrs = {"mr.", "mrs.", "dr.", "prof.", "dhr.", "mevr.", "etc.", "bijv.", "d.w.z.", "a.m.", "p.m."}
    if any(last_word.startswith(a) for a in common_abbrs):
        if len(cleaned) > len(last_word) and cleaned[len(last_word):].strip() and cleaned[len(last_word)].islower():
            return False

    # 2. Check sentence enders (longest first)
    for ender in sorted(SENTENCE_ENDERS, key=len, reverse=True):
        if lower_cleaned.endswith(ender):
            return True

    # 3. Fallback
    if cleaned and cleaned[-1] in ".!?":
        return True

    return False


def merge_subtitles(segments: List[dict], lang: str = "en") -> List[dict]:
    """Merge multiple consecutive subtitles that don't end a sentence."""
    merged = []
    i = 0
    while i < len(segments):
        curr = segments[i]

        if is_sentence_end(curr['text'], lang):
            merged.append(curr)
            i += 1
            continue

        # Start merging block
        start_time = curr['start']
        merged_text = curr['text'].rstrip()
        end_time = curr['end']
        i += 1

        # Keep merging while next does NOT end sentence
        while i < len(segments) and not is_sentence_end(segments[i]['text'], lang):
            merged_text += " " + segments[i]['text'].lstrip()
            end_time = segments[i]['end']
            i += 1

        # Add the final row that ends the sentence
        if i < len(segments):
            merged_text += " " + segments[i]['text'].lstrip()
            end_time = segments[i]['end']
            i += 1

        merged.append({
            'start': start_time,
            'end': end_time,
            'text': merged_text.strip()
        })

    return merged


# ====================== MAIN PROCESS FUNCTION ======================
def merge_sentences(subs: List[srt.Subtitle], lang: str = "en") -> List[srt.Subtitle]:
    lang = lang.lower().strip()
    """
    Merges sentence fragments across multiple subtitles.
    Returns a new list of srt.Subtitle objects.
    """
    if not subs:
        return []

    # Convert to dicts for easier merging
    segments = [
        {'start': sub.start, 'end': sub.end, 'text': sub.content.strip()}
        for sub in subs
    ]

    # Do the merging
    merged_segments = merge_subtitles(segments, lang)

    # Convert back to srt.Subtitle objects
    result = []
    for idx, seg in enumerate(merged_segments, start=1):
        result.append(
            srt.Subtitle(
                index=idx,
                start=seg['start'],
                end=seg['end'],
                content=seg['text']
            )
        )
    return result