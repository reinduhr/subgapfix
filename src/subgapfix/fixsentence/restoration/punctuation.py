from typing import List, Dict
from deepmultilingualpunctuation import PunctuationModel
import typer

# Global model instance (loaded once)
_punctuation_model = None


def get_punctuation_model() -> PunctuationModel:
    """Lazy load the punctuation model (singleton)."""
    global _punctuation_model
    if _punctuation_model is None:
        typer.echo("Loading deepmultilingualpunctuation model (large)...")
        _punctuation_model = PunctuationModel()   # This uses the large model by default
        typer.echo("✅ Punctuation model loaded successfully.")
    return _punctuation_model


def add_punctuation(segments: List[Dict]) -> List[Dict]:
    """
    Restore proper punctuation to each segment using oliverguhr's model.
    
    This is the recommended way according to the official repo.
    """
    if not segments:
        return []

    model = get_punctuation_model()

    new_segments = []

    for seg in segments:
        original_text = seg.get("text", "").strip()
        
        if not original_text:
            new_segments.append(seg)
            continue

        # Restore punctuation
        restored_text = model.restore_punctuation(original_text)

        # Create new segment with restored text (keep everything else the same)
        new_seg = seg.copy()
        new_seg["text"] = restored_text
        new_segments.append(new_seg)

    typer.echo(f"✅ Punctuation restored for {len(new_segments)} segments.")
    return new_segments