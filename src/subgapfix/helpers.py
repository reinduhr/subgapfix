from pathlib import Path
from typing import List, Dict
import json
import typer
import spacy
import srt
from datetime import timedelta
from spacy.util import is_package

def is_gpu_active() -> bool:
    activated = spacy.prefer_gpu()

    if activated:
        typer.echo("✅ Success: spaCy is using the GPU!")
        return True
    
    typer.echo("❌ Failure: spaCy is falling back to CPU.")
    return False

def load_nlp_model(model_name: str = "en_core_web_trf"):
    """Checks for model existence and downloads if missing."""
    if not is_package(model_name):
        typer.echo(f"Model '{model_name}' not found. Downloading...")
        # Use spaCy's own CLI downloader
        spacy.cli.download(model_name)
    
    return spacy.load(model_name)

def format_seconds_to_srt(seconds):
    """
    Converts a float (seconds) into SRT time format: HH:MM:SS,mmm
    """
    # Calculate components
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    # Extract milliseconds and round to 3 digits
    millis = int(round((seconds % 1) * 1000))
    
    # Handle the overflow case (e.g., 999.7ms rounding to 1000ms)
    if millis == 1000:
        return format_seconds_to_srt(seconds + 0.001)

    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

def capitalize_sentence(text: str) -> str:
    if not text or not text.strip():
        return text
    
    text = text.strip()
    
    # If it already starts with a capital letter, return as-is
    if text[0].isupper():
        return text
    
    # Capitalize the first letter
    return text[0].upper() + text[1:]


def convert_to_srt_subtitles(segments: List[Dict]) -> List[srt.Subtitle]:
    """
    Converts list of segments (with 'start' and 'end' in seconds) 
    into a list of srt.Subtitle objects.
    """
    subtitles = []
    
    for idx, seg in enumerate(segments, start=1):
        text = seg.get('text', '').strip()
        # Convert float seconds to timedelta
        start_td = timedelta(seconds=seg['start'])
        end_td = timedelta(seconds=seg['end'])
        sentence = capitalize_sentence(text)
        
        subtitle = srt.Subtitle(
            index=idx,
            start=start_td,
            end=end_td,
            content=sentence,
        )
        subtitles.append(subtitle)
    
    return subtitles

def debug_save_json(data: List[Dict], filename: str = "debug_output.json"):
    """
    Writes a list of dictionaries to a JSON file with pretty-printing.
    Useful for inspecting spaCy segments or WhisperX word alignments.
    """
    output_path = Path(filename)
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            # indent=4 makes it readable; ensure_ascii=False keeps non-English chars
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        typer.secho(f"🐞 Debug data saved to: {output_path.absolute()}", fg=typer.colors.MAGENTA)
    except Exception as e:
        typer.secho(f"❌ Failed to save debug file: {e}", fg=typer.colors.RED)

def two_subtitles_to_one(
    subtitles: List[srt.Subtitle],
    min_duration: float = 1.2,          # seconds
    min_chars: int = 12,                # characters (excluding spaces)
    max_combined_duration: float = 7.0  # don't merge if combined is too long
) -> List[srt.Subtitle]:
    """
    Merges very short consecutive subtitles into one with a line break.
    Improves readability by reducing subtitle flashing.
    """
    if not subtitles:
        return []

    merged = []
    i = 0

    while i < len(subtitles):
        current = subtitles[i]

        # Check if current subtitle is "too short"
        duration = (current.end - current.start).total_seconds()
        char_count = len(current.content.replace(" ", ""))

        # If it's not short, or it's the last one, keep it as-is
        if duration >= min_duration or char_count >= min_chars or i == len(subtitles) - 1:
            merged.append(current)
            i += 1
            continue

        # Check if next subtitle also qualifies for merging
        if i + 1 < len(subtitles):
            next_sub = subtitles[i + 1]
            next_duration = (next_sub.end - next_sub.start).total_seconds()
            next_chars = len(next_sub.content.replace(" ", ""))

            combined_duration = (next_sub.end - current.start).total_seconds()

            # Merge if both are short and combined isn't too long
            if (next_duration < min_duration and next_chars < min_chars and 
                combined_duration <= max_combined_duration):

                # Create merged subtitle with line break
                merged_content = f"{current.content}\n{next_sub.content}"

                merged_sub = srt.Subtitle(
                    index=current.index,           # we'll renumber later if needed
                    start=current.start,
                    end=next_sub.end,
                    content=merged_content
                )
                merged.append(merged_sub)
                i += 2  # skip the next one
                continue

        # If we couldn't merge, keep current
        merged.append(current)
        i += 1

    # Renumber the subtitles properly
    for idx, sub in enumerate(merged, start=1):
        sub.index = idx

    return merged