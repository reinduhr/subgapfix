from typing import Dict
import json
from pathlib import Path
import srt
from datetime import timedelta
import typer
from .fixsubtitle.submerge import merge_sentences_json
from .fixsubtitle.subsplit import split_sub_by_sentences
from .fixsentence.restoration.punctuation import add_punctuation
from .fixsentence.refinement.cleanup import cleanup_segments
from .fixsentence.refinement.grammar import polish_with_llm
from .helpers import convert_to_srt_subtitles, debug_save_json, two_subtitles_to_one


app = typer.Typer(
    help="Extend subtitle display durations in gaps (better readability without overlaps).",
    add_completion=True,
)


def validate_input_file(input_file: Path) -> None:
    """Check if the input is a valid .json file."""
    if input_file.suffix.lower() != ".json":
        typer.secho(
            f"Error: Input file must have .json extension (got: {input_file.name})",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)


def prepare_output_path(input_file: Path, output: Path | None) -> Path:
    """Determine output path — ensure it always ends in .srt."""
    if output is None:
        # Changes "file.json" to "file_fixed.srt"
        return input_file.with_stem(input_file.stem + "_fixed").with_suffix(".srt")
    
    # Even if a custom output path is provided, ensure it has the .srt suffix
    if output.suffix.lower() != ".srt":
        return output.with_suffix(".srt")
        
    return output


def validate_parameters(extend_start: float, min_gap: float, extend_final_sub: float) -> None:
    """Ensure logical parameter constraints."""
    if min_gap <= extend_start:
        typer.secho(
            f"Error: --min-gap ({min_gap}) must be > --extend-start ({extend_start})",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)
    
    if extend_final_sub < 0:
        typer.secho(
            f"Error: --extend-final-sub must be greater than or equal to 0",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)
    

def validate_language(lang: str) -> None:
    """Validate that the language is supported."""
    supported = {"en", "nl"}
    lang_lower = lang.lower().strip()
    
    if lang_lower not in supported:
        typer.secho(
            f"Error: Language '{lang}' is not supported. Use 'en' or 'nl'.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)


def load_subtitles(input_file: Path) -> list[srt.Subtitle]:
    """Read and parse the SRT file."""
    try:
        content = input_file.read_text(encoding="utf-8")
        return list(srt.parse(content))
    except Exception as e:
        typer.secho(f"Cannot parse SRT: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


def load_whisperx_json(input_file_json: Path) -> Dict:
    """Reads the WhisperX JSON export and returns the dictionary."""
    try:
        with open(input_file_json, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        typer.secho(f"Error reading JSON: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    

def extend_gaps(
    subs: list[srt.Subtitle],
    extend_start: float,
    extend_end_max: float,
    min_gap: float,
    extend_final_sub: float
) -> int:
    """Apply gap extension logic. Returns number of changed pairs."""
    changes = 0

    for i in range(len(subs) - 1):
        a, b = subs[i], subs[i + 1]
        gap = (b.start - a.end).total_seconds()

        old_a_end = a.end
        old_b_start = b.start

        if gap < min_gap:
            delta = gap / 2
            a.end += timedelta(seconds=delta)
            b.start -= timedelta(seconds=delta)
        elif gap >= min_gap:
            extendable = gap - extend_start
            if extendable > 0:
                extension = min(extendable, extend_end_max)
                a.end += timedelta(seconds=extension)
                b.start -= timedelta(seconds=extend_start)

        # Prevent overlap / negative duration
        if b.start <= a.end:
            b.start = a.end + timedelta(milliseconds=10)

        if a.end != old_a_end or b.start != old_b_start:
            changes += 1

    # Finally give the very last subtitle +1 second
    if subs and extend_final_sub > 0:
        last = subs[-1]
        last.end += timedelta(seconds=extend_final_sub)
        changes += 1

    return changes


@app.command()
def main(
    
    input_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    
    # input_file_json: Path = typer.Option(
    #     None,
    #     "--input-json",
    #     "-ij",
    #     exists=True,          # Ensure the file exists
    #     file_okay=True,       # Must be a file, not a folder
    #     dir_okay=False,       # Reject directories
    #     readable=True,        # Must have permissions to read
    #     help="Input file: whisperx json with word level timestamps"
    # ),
    
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file. Default: <input>_fixed.srt in same folder",
    ),
    
    extend_start: float = typer.Option(
        0.5, "--extend-sub-start", "-ess", help="Seconds to pull next sub backward"
    ),
    
    extend_end_max: float = typer.Option(
        2.0, "--extend-sub-end", "-ese", help="Max seconds to extend current sub forward"
    ),
    
    min_gap: float = typer.Option(
        1.0, "--min-gap", "-mg", help="Only extend when gap ≥ this value"
    ),
    
    dry_run: bool = typer.Option(False, "--dry-run", help="Show amount changes without writing"),
    
    extend_final_sub: float = typer.Option(
        1.0,
        "--extend-final-sub",
        "-efs",
        help="Seconds to add to the very last subtitle"
    ),

    fixsubs: bool = typer.Option(
        False,
        "--fixsubs",
        "-fs",
        help="Merge and split subtitles to create one sentence per subtitle",
    ),

    fixsubs_withllm: bool = typer.Option(
        False,
        "--fixsubs-llm",
        "-fsl",
        help="Merge and split subtitles to create one sentence per subtitle",
    ),

    lang: str = typer.Option(
        "en",
        "--lang",
        "-l",
        help="Language for sentence detection (en or nl)",
        case_sensitive=False,
    ),

    two_to_one: bool = typer.Option(
        False,
        "--two-to-one",
        "-tto",
        help="Combine two short subtitles into one",
    ),
):
    
    validate_input_file(input_file)

    output_path = prepare_output_path(input_file, output)

    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    validate_parameters(extend_start, min_gap, extend_final_sub)

    data = load_whisperx_json(input_file)

    # Extract subtitles (segments)
    segments = data if isinstance(data, list) else data.get("segments", [])
    
    if not segments:
        typer.secho("Error: No segments found in JSON", fg=typer.colors.RED)
        raise typer.Exit(1)
    
    if fixsubs:
        lang_str = lang if isinstance(lang, str) else "en"
        merged_segments, merge_map = merge_sentences_json(segments, lang=lang_str)
        #debug_save_json(merged_segments)
        merged_segments = cleanup_segments(merged_segments)
    else:
        merged_segments = segments

    if fixsubs_withllm:
        merged_segments = polish_with_llm(merged_segments)

    if fixsubs:
        merged_segments = add_punctuation(merged_segments)
        final_dict_segments = split_sub_by_sentences(merged_segments, lang=lang)

    subs = convert_to_srt_subtitles(final_dict_segments)

    if two_to_one:
        subs = two_subtitles_to_one(subs)

    changes = extend_gaps(subs, extend_start, extend_end_max, min_gap, extend_final_sub)

    if dry_run:
        typer.echo(f"Dry run completed. Would have made {changes} gap changes.")
        return

    # Save final SRT
    output_path.write_text(srt.compose(subs), encoding="utf-8")
    typer.secho(
        f"Done. Wrote {len(subs)} subtitles → {output_path}",
        fg=typer.colors.GREEN,
    )


# ====================== QUICK LOCAL TEST ======================
def quick_test():
    """Quick test function - easy to run during development"""
    test_file = "data/transcription/test/input/rancourt.json"        # ← Put your test .srt file here
    json_file = "data/transcription/test/input/rancourt.json"
    output_file = "data/transcription/test/output/test_merged_fixed.srt"

    print(f"Testing subgapfix with: {test_file}")

    # Simulate running main with -sm flag
    main(
        input_file=Path(test_file),
        #input_file_json=Path(json_file),
        output=Path(output_file),
        submerge=False,             # Enable sentence merging
        dry_run=False,
        #extend_start=0.5,
        #extend_end_max=2.0,
        #min_gap=1.0,
        #extend_final_sub=1.0,
    )

    print("✅ Test finished!")


if __name__ == "__main__":
    app()
    #quick_test()
