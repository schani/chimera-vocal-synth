#!/bin/sh
# Schubert, Ave Maria D 839, sung German over piano: shows ave-maria-de (soprano) and
# ave-maria-de-trio (soprano, tenor, child). Usage: songs/ave-maria/make.sh [--no-render]
set -eu
. "$(dirname "$0")/../lib.sh"
need lilypond "LilyPond 2.24+"

# score.ly (Mutopia 1054) -> per-staff event lists and the MIDI, then melody files and piano.mid
mkdir -p "$OUT/ly"
cp "$HERE/score.ly" "$OUT/ly/"
(cd "$OUT/ly" && rm -f ./*.notes && lilypond -dno-point-and-click score.ly 2>&1 | grep -E "error|Success" || true)
[ -f "$OUT/ly/score-voice.notes" ] || { echo "lilypond failed: run it in $OUT/ly" >&2; exit 1; }
"$PY" "$HERE/build.py" "$OUT"
[ "$RENDER" = 1 ] || { echo "--no-render: melody files in $OUT"; exit 0; }

need fluidsynth "and a General MIDI soundfont in SF2"
need ffmpeg "with mp3 (libmp3lame)"
SOUNDFONT=$(sf2)
fluidsynth -ni -q -g 0.8 -r 48000 -o synth.reverb.room-size=0.6 -o synth.reverb.level=0.5 \
  -F "$OUT/piano.wav" "$SOUNDFONT" "$OUT/piano.mid"

printf '%s\n' "voice-female female tele" "voice-male male tele" "voice-child child tele" > "$OUT/jobs.txt"
render_all "$OUT/jobs.txt"

cd "$OUT"
"$PY" "$HERE/mix.py" piano.wav voice-female.wav ave-maria-soprano.wav 6
"$PY" -c "
from scipy.io import wavfile; import numpy as np
v=[wavfile.read(f'voice-{b}.wav')[1].astype(float) for b in ('female','male','child')]
n=max(len(x) for x in v); v=[np.pad(x,(0,n-len(x))) for x in v]
s=v[0]*1.0+v[1]*0.85+v[2]*0.6; wavfile.write('voice-trio.wav',48000,(s/abs(s).max()*0.75*32767).astype(np.int16))"
"$PY" "$HERE/mix.py" piano.wav voice-trio.wav ave-maria-trio.wav 6
for f in soprano trio; do ffmpeg -loglevel error -y -i ave-maria-$f.wav -b:a 192k ave-maria-$f.mp3; done

install_show ave-maria-de ave-maria-soprano.mp3 voice-female.tele voice-female.json <<'J'
{ "title": "Schubert: Ave Maria (D 839), sung German", "audio": "ave-maria-soprano.mp3", "bpm": 26, "downbeat": 2.3077,
  "voices": [{ "name": "Soprano", "tele": "voice-female.tele", "melody": "voice-female.json" }] }
J
install_show ave-maria-de-trio ave-maria-trio.mp3 voice-female.tele voice-male.tele voice-child.tele \
  voice-female.json voice-male.json voice-child.json <<'J'
{ "title": "Schubert: Ave Maria (D 839), sung German, three voices", "audio": "ave-maria-trio.mp3", "bpm": 26, "downbeat": 2.3077,
  "voices": [{ "name": "Tenor", "tele": "voice-male.tele", "melody": "voice-male.json" },
             { "name": "Child", "tele": "voice-child.tele", "melody": "voice-child.json" },
             { "name": "Soprano", "tele": "voice-female.tele", "melody": "voice-female.json" }] }
J
