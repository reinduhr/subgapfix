from pathlib import Path
import srt
from datetime import timedelta
import typer

app = typer.Typer(
    help="Extend subtitle display durations in gaps (better readability without overlaps).",
    add_completion=True,
)


@app.command()
def main(
    input_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    output: Path = typer.Option(
        None,
        "--output", "-o",
        help="Output file. Default: <input>_fixed.srt in same folder",
    ),
    extend_start: float = typer.Option(
        0.5, "--extend-start", "-ess", help="Seconds to pull next sub backward"
    ),
    extend_end_max: float = typer.Option(
        2.0, "--extend-end-max", "-ese", help="Max seconds to extend current sub forward"
    ),
    min_gap: float = typer.Option(
        1.0, "--min-gap", "-mg", help="Only extend when gap ≥ this value"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show changes without writing"),
):
    if output is None:
        output = input_file.with_stem(input_file.stem + "_fixed")

    if min_gap <= extend_start:
        typer.secho(
            f"Error: --min-gap ({min_gap}) must be > --extend-start ({extend_start})",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    try:
        subs = list(srt.parse(input_file.read_text(encoding="utf-8")))
    except Exception as e:
        typer.secho(f"Cannot parse SRT: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

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

        # Overlap safety
        if b.start <= a.end:
            b.start = a.end + timedelta(milliseconds=10)

        if a.end != old_a_end or b.start != old_b_start:
            changes += 1

    if dry_run:
        typer.echo(f"Would apply changes to {changes} subtitle pairs.")
        return

    output.write_text(srt.compose(subs), encoding="utf-8")
    typer.secho(f"Done. Wrote {len(subs)} subtitles → {output}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()