# Songs

Each folder rebuilds one or more duet shows (`public/shows/<id>/`, opened at `?show=<id>` on
`bun run dev`) with one command, from the repo root. Intermediates go to `songs/<song>/out/`; both
are gitignored.

| Command | Shows | Voices to render |
|---|---|---|
| `songs/ave-maria/make.sh` | `ave-maria-de`, `ave-maria-de-trio`, `ave-maria-voices`, `ave-maria-six` | 6 × 6-7 min |
| `songs/bleak-midwinter/make.sh` | `bleak-midwinter` | 12 × 5 min |
| `songs/thunderstruck/make.sh <your.mxl>` | `thunderstruck-score`, `thunderstruck-electric` | 7 × 4 min |

A voice renders at roughly 1-2× its length on one CPU core, and the voices render in parallel, one
per core (`JOBS=n` to change): on 8 cores Ave Maria takes 6-12 min, Bleak Midwinter 10-20,
Thunderstruck 5-10, plus a few minutes of mixing; on 2 cores, 2-4× that. A rerun skips voices
whose melody, body and engine are unchanged. `--no-render` stops once the melody files are written.

Ave Maria (Schubert, Mutopia 1054) and Bleak Midwinter (Holst, Open Hymnal) are public domain and
their scores are here. Thunderstruck is not: bring your own MuseScore arrangement (`.mxl`); the
score, its words and everything made from it stay out of git.

## Requirements

- Rust and Bun (see the main README); the scripts build `chimera-cli` themselves.
- Python 3 with numpy, scipy, mido and music21, e.g. in a venv:
  `python3 -m venv songs/.venv && songs/.venv/bin/pip install -r songs/requirements.txt`, then run
  the scripts with `PYTHON=songs/.venv/bin/python` (default: `python3`).
- ffmpeg with mp3.
- Ave Maria: LilyPond 2.24+.
- Ave Maria and Thunderstruck: fluidsynth and a General MIDI soundfont such as `FluidR3_GM.sf2`.
  Set `SF2=/path/to/soundfont.sf2` unless it's at `/usr/share/sounds/sf2/FluidR3_GM.sf2`.

On a Mac: `brew install python ffmpeg fluid-synth lilypond`, and download a GM soundfont for `SF2`.

## Ready-made shows

The public-domain shows are also on the `shows` release, to skip the voice renders:

```sh
gh release download shows -R schani/chimera-vocal-synth -p '*.tar.gz' -D /tmp
for f in /tmp/*-show.tar.gz; do tar xzf "$f" -C public/shows; done
```

## Video

`tools/show-video.sh <show-id> [out.mp4]` records a show as an MP4 on this machine's GPU: headless
through Metal on a Mac, in visible Chrome windows elsewhere. Without a GPU, `bun tools/duet-video.ts`
(no `--gpu`) works in software, at seconds a frame.
