import argparse
import srt
from datetime import timedelta

def extend_subs(input_file, output_file, extend_sub_start=0.5, extend_sub_end=2.0, min_gap=1.0):
    
    if min_gap > extend_sub_start:

        with open(input_file, "r", encoding="utf-8") as f:
            subs = list(srt.parse(f.read()))

        for i in range(len(subs) - 1):
            first, second = subs[i], subs[i + 1]
            gap = (second.start - first.end).total_seconds()
            
            if gap < min_gap:
                first.end += timedelta(seconds=gap/2)
                second.start -= timedelta(seconds=gap/2)

            if gap >= min_gap:
                extendable = gap - extend_sub_start
                if extendable > 0:
                    extension = min(extendable, extend_sub_end)
                    first.end += timedelta(seconds=extension)
                    second.start -= timedelta(seconds=extend_sub_start)

            # Make sure subs don't overlap each other
            if second.start <= first.end:
                second.start = first.end + timedelta(milliseconds=10)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(srt.compose(subs))

    else:
        print("Hold up! The value of min_gap should be greater than that of extended_sub_start.")

def main():
    parser = argparse.ArgumentParser(
        description="Extend subtitle durations when there is a gap before the next subtitle."
    )
    parser.add_argument("input", help="Input SRT file")
    parser.add_argument("-o", "--output", default="subgapfix.srt", help="Output SRT file")
    parser.add_argument("--extend-sub-start", "-ess", type=float, default=0.5, help="Seconds to add to start of subtitle. Default is: -ess 0.5")
    parser.add_argument("--extend-sub-end", "-ese", type=float, default=2.0, help="Seconds to add to end of subtitle. Default is: -ese 2.0")
    parser.add_argument("--min-gap", "-mg", type=float, default=1.0, help="Minimum gap (in seconds) required to apply extension. Default is: -mg 1.0")
    args = parser.parse_args()

    extend_subs(args.input, args.output, args.extend_sub_start, args.extend_sub_end, args.min_gap)

if __name__ == "__main__":
    main()
