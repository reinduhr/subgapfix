import srt
from typing import List, Dict, Tuple, Any
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


def merge_subtitles_json(
    segments: List[Dict], 
    lang: str = "en"
) -> Tuple[List[Dict], List[List[int]]]:
    """
    Merge consecutive WhisperX JSON segments that belong to the same sentence.
    
    Args:
        segments: List of WhisperX segments (each has 'start', 'end', 'text', and optionally 'words')
        lang: Language code ('en' or 'nl')
    
    Returns:
        merged_segments: List of merged segments (same structure as input)
        merge_groups:    List of lists containing original indices for each merged group
                         e.g. [[0,1,2], [3], [4,5,6]] 
    """
    if not segments:
        return [], []

    merged = []
    merge_groups = []        # Tracks original indices for each final segment
    i = 0

    while i < len(segments):
        curr = segments[i]

        # If current segment already ends a sentence → keep as is
        if is_sentence_end(curr.get('text', ''), lang):
            merged.append(curr.copy())          # shallow copy is fine here
            merge_groups.append([i])
            i += 1
            continue

        # Start merging block
        start_time = curr['start']
        merged_text = curr['text'].rstrip() if curr.get('text') else ""
        end_time = curr['end']
        group_indices = [i]

        # Collect all 'words' from segments being merged
        merged_words = curr.get('words', [])[:]

        i += 1

        # Keep merging while next segment does NOT end a sentence
        while i < len(segments) and not is_sentence_end(segments[i].get('text', ''), lang):
            next_seg = segments[i]
            merged_text += " " + next_seg.get('text', '').lstrip()
            end_time = next_seg['end']
            group_indices.append(i)
            
            if 'words' in next_seg:
                merged_words.extend(next_seg['words'])
                
            i += 1

        # Add the final segment that ends the sentence
        if i < len(segments):
            next_seg = segments[i]
            merged_text += " " + next_seg.get('text', '').lstrip()
            end_time = next_seg['end']
            group_indices.append(i)
            
            if 'words' in next_seg:
                merged_words.extend(next_seg['words'])
                
            i += 1

        # Create merged segment
        merged_segment = {
            'start': start_time,
            'end': end_time,
            'text': merged_text.strip(),
        }
        if merged_words:
            merged_segment['words'] = merged_words

        merged.append(merged_segment)
        merge_groups.append(group_indices)

    return merged, merge_groups


# ====================== MAIN PROCESS FUNCTION ======================
def merge_sentences_json(
    json_segments: List[Dict], 
    lang: str = "en"
) -> Tuple[List[Dict], List[List[int]]]:
    """
    Main entry point for merging WhisperX JSON output.
    
    Returns:
        merged_segments: List of merged JSON-style segments
        merge_groups:    List of original indices for each merged segment
    """
    lang = lang.lower().strip()
    
    if not json_segments:
        return [], []

    merged_segments, merge_groups = merge_subtitles_json(json_segments, lang=lang)
    
    return merged_segments, merge_groups