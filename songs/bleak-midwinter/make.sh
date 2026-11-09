#!/bin/sh
# Holst, In the Bleak Midwinter (Cranham), SATB a cappella, twelve singers: show bleak-midwinter.
# Usage: songs/bleak-midwinter/make.sh [--no-render]
set -eu
. "$(dirname "$0")/../lib.sh"

"$PY" "$HERE/build.py" "$OUT"
[ "$RENDER" = 1 ] || { echo "--no-render: melody files in $OUT"; exit 0; }
need ffmpeg "with mp3 (libmp3lame)"

cd "$OUT"
for f in soprano?.json alto?.json tenor?.json bass?.json; do
  s=${f%.json}
  case $s in *1) t=tele ;; *) t= ;; esac
  echo "$s $(cat "$s.body")${t:+ $t}"
done > jobs.txt
render_all "$OUT/jobs.txt"

"$PY" "$HERE/mix.py" "$OUT"
ffmpeg -loglevel error -y -i choir.wav -b:a 192k choir.mp3
install_show bleak-midwinter choir.mp3 soprano1.tele alto1.tele tenor1.tele bass1.tele \
  soprano1.json alto1.json tenor1.json bass1.json <<'J'
{ "title": "Holst: In the Bleak Midwinter (Cranham), SATB", "audio": "choir.mp3", "bpm": 66, "downbeat": 1.909,
  "voices": [{ "name": "Soprano", "tele": "soprano1.tele", "melody": "soprano1.json" },
             { "name": "Alto", "tele": "alto1.tele", "melody": "alto1.json" },
             { "name": "Tenor", "tele": "tenor1.tele", "melody": "tenor1.json" },
             { "name": "Bass", "tele": "bass1.tele", "melody": "bass1.json" }] }
J
