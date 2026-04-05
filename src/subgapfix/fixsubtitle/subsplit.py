from typing import List, Dict
from ..helpers import load_nlp_model


def split_sub_by_sentences(
    segments: List[Dict],
    lang: str = "en"
) -> List[Dict]:
    """
    Splits segments so that each final segment contains exactly ONE natural sentence.
    Prioritizes sentence boundaries over duration.
    """
    if not segments:
        return []

    nlp = load_nlp_model()
    final_segments = []

    for seg in segments:
        text = seg.get("text", "").strip()
        words = seg.get("words", [])

        if not text or not words:
            continue

        # Use spaCy to detect sentence boundaries
        doc = nlp(text)

        current_word_idx = 0

        for sent in doc.sents:
            sent_text = sent.text.strip()
            if not sent_text:
                continue

            sent_words = []
            
            # Collect words belonging to this sentence
            for i in range(current_word_idx, len(words)):
                sent_words.append(words[i])
                current_word_idx = i + 1

                # Stop when we've covered most of the sentence text
                reconstructed = " ".join(w["word"] for w in sent_words)
                if len(reconstructed) >= len(sent_text) * 0.82:   # flexible matching
                    break

            if sent_words:
                new_segment = {
                    "start": sent_words[0]["start"],
                    "end": sent_words[-1]["end"],
                    "text": sent_text,
                    "words": sent_words.copy()
                }
                final_segments.append(new_segment)

    return final_segments
