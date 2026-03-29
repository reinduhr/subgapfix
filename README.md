# SubGapFix

[![PyPI version](https://img.shields.io/pypi/v/subgapfix.svg)](https://pypi.org/project/subgapfix/)
[![Python versions](https://img.shields.io/pypi/pyversions/subgapfix.svg)](https://pypi.org/project/subgapfix/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**SubGapFix** is a lightweight CLI tool that makes subtitles easier and more comfortable to read by **intelligently extending their display duration** — especially useful for auto-generated subtitles.

It works great with transcriptions from **[WhisperX](https://github.com/m-bain/whisperX)**.

## ✨ Features

- Extends subtitle display time when there is a **gap** before the next line
- Safely prevents overlaps and negative durations
- Dry-run mode to preview changes without writing files
- Creates output folders automatically if needed
- Only processes valid `.srt` files
- Option to merge subtitles when a sentence is spanning over multiple subtitles (supported languages: English, Dutch)

## 📦 Installation

```bash
pip install subgapfix
```

Requires Python 3.8+.

Dependencies:
- `typer` — beautiful CLI interface
- `srt` — reliable SRT parsing

## 🚀 Quick Start

```bash
# Basic usage — creates episode_fixed.srt in the same folder
subgapfix episode.srt

# Custom output file (creates folders if needed)
subgapfix podcast/episode.srt -o podcast/enhanced/episode_subtitles.srt

# Preview changes without modifying anything
subgapfix input.srt --dry-run

# Customize timings
subgapfix input.srt --extend-sub-start 0.8 --extend-sub-end 3.0 --min-gap 1.5 --extend-final-sub 4.5

# Merge sentences (default language: en)
subgapfix input.srt --submerge --lang nl
```

## ⚙️ All Options

| Flag / Short | Default | Description |
|--------------|---------|-------------|
| `input_file` (positional) | — | Path to the input `.srt` file (must exist) |
| `-o, --output` | `<input>_fixed.srt` | Output file path (folders auto-created) |
| `--extend-sub-start`, `-ess` | `0.5` | Seconds to pull the **next** subtitle backward (tries to borrow from gap) |
| `--extend-sub-end`, `-ese` | `2.0` | Maximum seconds to extend current subtitle forward into the gap |
| `--min-gap`, `-mg` | `1.0` | Only apply extension if gap is at least this long (seconds) |
| `--dry-run` | `false` | Show how many pairs would change — no file written |
| `--extend-final-sub`, `-efs` | `1.0` | Number of seconds to add to the last subtitle |
| `--submerge`, `-sm` | `false` | Merge subtitles creating full sentences |
| `--lang`, `-l` | `en` | Set language in order to merge sentences correctly |
| `--help, -help` | — | Show full help and exit |

## How It Works

1. Reads and validates the `.srt` file
2. For each pair of consecutive subtitles:
   - If gap < `--min-gap` → splits the gap evenly (closes small gaps)
   - If gap ≥ `--min-gap` → extends current subtitle up to `--extend-sub-end`, pulls next one back by `--extend-sub-start`
3. Prevents any overlap by enforcing a tiny 10 ms safety gap
4. Add `--extend-final-sub` to the last subtitle for a precise ending
5. Writes the result (or just reports changes in dry-run)

**Before** (typical WhisperX-style tight timings):

```
1
00:00:01,837 --> 00:00:02,502
SubGapFix makes our lives

2
00:00:03,147 --> 00:00:03,571
much easier.

3
00:00:04,176 --> 00:00:04,518
Yes, I agree.
```

**After** (with defaults):

```
1
00:00:01,837 --> 00:00:02,824
SubGapFix makes our lives

2
00:00:02,834 --> 00:00:03,873
much easier.

3
00:00:03,883 --> 00:00:04,679
Yes, I agree.
```

## 💡 Why SubGapFix?

Modern speech-to-text tools often prioritize transcription accuracy over comfortable reading speed.  
Subtitles flash by too quickly → viewers miss text or feel rushed.

SubGapFix **does not shift timings** or re-sync — it only **lengthens display time** using existing gaps.  
This keeps perfect sync with the video while making subtitles far more readable.

Perfect for lectures, interviews, conversations, podcasts.