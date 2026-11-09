#!/bin/sh
# Thunderstruck from your own MuseScore arrangement (copyrighted: the score and everything made from
# it stay out of git, in out/ and public/shows/): shows thunderstruck-score and thunderstruck-electric.
# Usage: songs/thunderstruck/make.sh <thunderstruck.mxl> [--no-render]
set -eu
. "$(dirname "$0")/../lib.sh"
MXL=
for a in "$@"; do [ "$a" = --no-render ] || MXL=$a; done
[ -f "$MXL" ] || { echo "usage: $0 <thunderstruck.mxl> [--no-render]" >&2; exit 1; }
MXL=$(cd "$(dirname "$MXL")" && pwd)/$(basename "$MXL")
need bun "https://bun.sh"

"$PY" "$HERE/patch_score.py" "$MXL" "$OUT/score-patched.musicxml"
cd "$ROOT"
[ -d node_modules ] || bun install
bun run wasm
for p in P1 P2 P3; do
  bun tools/musicxml-to-notes.ts "$OUT/score-patched.musicxml" $p --spell our=owr --out "$OUT/$p.json"
done
"$PY" "$HERE/build.py"
[ "$RENDER" = 1 ] || { echo "--no-render: melody files in $OUT"; exit 0; }

need fluidsynth "and a General MIDI soundfont in SF2"
need ffmpeg "with mp3 (libmp3lame)"
SOUNDFONT=$(sf2)
cd "$OUT"
for v in score electric; do
  fluidsynth -ni -q -g 0.7 -r 48000 -o synth.reverb.room-size=0.4 -o synth.reverb.level=0.3 \
    -F band-$v.wav "$SOUNDFONT" band-$v.mid
done
while read -r s body; do
  case $s in lead|*_1) t=tele ;; *) t= ;; esac
  echo "$s $body${t:+ $t}"
done < jobs.txt > render-jobs.txt
render_all "$OUT/render-jobs.txt"

for v in score electric; do
  "$PY" "$HERE/mix.py" band-$v.wav thunderstruck-$v.wav
  ffmpeg -loglevel error -y -i thunderstruck-$v.wav -b:a 192k thunderstruck-$v.mp3
  T="Thunderstruck (as arranged: banjo, guitar, melodica)"; [ $v = electric ] && T="Thunderstruck (electric band)"
  install_show thunderstruck-$v thunderstruck-$v.mp3 lead.tele p2_1.tele p3_1.tele lead.json p2_1.json p3_1.json <<J
{ "title": "$T", "audio": "thunderstruck-$v.mp3", "bpm": 140, "downbeat": 0.5,
  "spell": {"owr": "our"},
  "voices": [{ "name": "Backing", "tele": "p2_1.tele", "melody": "p2_1.json" },
             { "name": "Lead", "tele": "lead.tele", "melody": "lead.json" },
             { "name": "Backing", "tele": "p3_1.tele", "melody": "p3_1.json" }] }
J
done
