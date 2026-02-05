import argparse
import srt
from datetime import timedelta
import os


def extend_subs(input_file, output_file, extend_sub_start=0.5, extend_sub_end=2.0, min_gap=1.0):
    
    if min_gap <= extend_sub_start:
        print(
            f"Hold up! The value of min_gap should be greater than that of extend_sub_start."
        )
        return

    # Make sure the output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir:  # only create if there's actually a directory part
        os.makedirs(output_dir, exist_ok=True)

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            subs = list(srt.parse(f.read()))
    except Exception as e:
        print(f"Failed to read input file: {e}")
        return

    for i in range(len(subs) - 1):
        first, second = subs[i], subs[i + 1]
        gap = (second.start - first.end).total_seconds()

        if gap < min_gap:
            # Close small gaps by meeting in the middle
            first.end += timedelta(seconds=gap / 2)
            second.start -= timedelta(seconds=gap / 2)
        else:
            # Gap is large enough → extend backward from second sub
            extendable = gap - extend_sub_start
            if extendable > 0:
                extension = min(extendable, extend_sub_end)
                first.end += timedelta(seconds=extension)
                second.start -= timedelta(seconds=extend_sub_start)

        # Final safety net: prevent overlap / negative duration
        if second.start <= first.end:
            second.start = first.end + timedelta(milliseconds=10)

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(srt.compose(subs))
        print(f"Written extended subtitles to: {output_file}")
    except Exception as e:
        print(f"Failed to write output file: {e}")


def main():

    parser = argparse.ArgumentParser(
        description="Extend subtitle durations when there is a gap before the next subtitle."
    )

    parser.add_argument("input", help="Input SRT file")

    parser.add_argument(
        "-o", "--output",
        default="subgapfix.srt",
        help="Output SRT file (folders will be created if needed)"
    )

    parser.add_argument(
        "--extend-sub-start", "-ess",
        type=float, default=0.5,
        help="Seconds to try to pull start of next sub backward. Default: 0.5"
    )

    parser.add_argument(
        "--extend-sub-end", "-ese",
        type=float, default=2.0,
        help="Max seconds to extend end of current sub. Default: 2.0"
    )

    parser.add_argument(
        "--min-gap", "-mg",
        type=float, default=1.0,
        help="Minimum gap (seconds) required to apply extension. Default: 1.0"
    )

    args = parser.parse_args()

    extend_subs(
        args.input,
        args.output,
        args.extend_sub_start,
        args.extend_sub_end,
        args.min_gap
    )


if __name__ == "__main__":
    main()