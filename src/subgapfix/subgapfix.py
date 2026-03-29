from pathlib import Path
import srt
from datetime import timedelta
import typer
from .submerge.submerge import merge_sentences


app = typer.Typer(
    help="Extend subtitle display durations in gaps (better readability without overlaps).",
    add_completion=True,
)


def validate_input_file(input_file: Path) -> None:
    """Check if the input is a valid .srt file."""
    if input_file.suffix.lower() != ".srt":
        typer.secho(
            f"Error: Input file must have .srt extension (got: {input_file.name})",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)


def prepare_output_path(input_file: Path, output: Path | None) -> Path:
    """Determine output path — use default if not provided."""
    if output is None:
        return input_file.with_stem(input_file.stem + "_fixed")
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

    submerge: bool = typer.Option(
        False,
        "--submerge",
        "-sm",
        help="Merge subtitles that belong to the same sentence before fixing gaps",
    ),

    lang: str = typer.Option(
        "en",
        "--lang",
        "-l",
        help="Language for sentence detection (en or nl)",
        case_sensitive=False,
    ),
):
    
    validate_input_file(input_file)

    output_path = prepare_output_path(input_file, output)

    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    validate_parameters(extend_start, min_gap, extend_final_sub)

    subs = load_subtitles(input_file)
    
    if submerge:
        lang_str = lang if isinstance(lang, str) else "en"
        subs = merge_sentences(subs, lang=lang_str)

    changes = extend_gaps(subs, extend_start, extend_end_max, min_gap, extend_final_sub)

    if dry_run:
        typer.echo(f"The dry run ran succesfully and detected {changes} changes to subtitle pairs.")
        return

    output_path.write_text(srt.compose(subs), encoding="utf-8")
    typer.secho(
        f"Done. Wrote {len(subs)} subtitles → {output_path}",
        fg=typer.colors.GREEN,
    )


# ====================== QUICK LOCAL TEST ======================
def quick_test():
    """Quick test function - easy to run during development"""
    test_file = "data/transcription/input.srt"        # ← Put your test .srt file here
    output_file = "test_merged_fixed.srt"

    print(f"Testing subgapfix with submerge on: {test_file}")

    # Simulate running main with -sm flag
    main(
        input_file=Path(test_file),
        output=Path(output_file),
        submerge=True,             # Enable sentence merging
        dry_run=False,
        extend_start=0.5,
        extend_end_max=2.0,
        min_gap=1.0,
        extend_final_sub=1.0,
    )

    print("✅ Test finished!")


if __name__ == "__main__":
    app()
    #quick_test()
