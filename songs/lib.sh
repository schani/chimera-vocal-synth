# Sourced by songs/*/make.sh (after `set -eu`). Sets HERE (the song's folder), ROOT (the repo), OUT,
# PY, CHIMERA, NPROC, RENDER (0 with --no-render) and the helpers below. Set SONG_PY=0 first if the
# song needs no Python.
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
OUT=$HERE/out
PY=${PYTHON:-python3}
case $PY in */*) PY=$(cd "$(dirname "$PY")" && pwd)/$(basename "$PY") ;; esac
CHIMERA=$ROOT/target/release/chimera
NPROC=${JOBS:-$(nproc 2>/dev/null || sysctl -n hw.ncpu)}
RENDER=1
for a in "$@"; do [ "$a" = --no-render ] && RENDER=0; done
export CHIMERA
mkdir -p "$OUT"

need() {  # need <command> <hint>
  command -v "$1" >/dev/null 2>&1 || { echo "missing: $1 ($2)" >&2; exit 1; }
}

if [ "${SONG_PY:-1}" = 1 ]; then  # a song without Python (SONG_PY=0 before sourcing) skips this
  need "$PY" "python3, or set PYTHON"
  "$PY" -c "import numpy, scipy, mido, music21" 2>/dev/null ||
    { echo "missing python packages: $PY -m pip install -r songs/requirements.txt" >&2; exit 1; }
fi
need cargo "Rust: https://rustup.rs"
(cd "$ROOT" && cargo build --release -q -p chimera-cli)

sf2() {  # the General MIDI soundfont: $SF2, else a usual install path
  for f in "${SF2:-}" /usr/share/sounds/sf2/FluidR3_GM.sf2 /usr/share/soundfonts/FluidR3_GM.sf2 \
           /opt/homebrew/share/soundfonts/FluidR3_GM.sf2 /usr/local/share/soundfonts/FluidR3_GM.sf2; do
    [ -n "$f" ] && [ -f "$f" ] && { echo "$f"; return; }
  done
  echo "no soundfont: set SF2=/path/to/a/General-MIDI.sf2 (e.g. FluidR3_GM.sf2)" >&2; exit 1
}

render_all() {  # render_all <jobs>: "<stem> <body>[ tele]" per line, melodies in $OUT, NPROC at a time
  # (no trailing blank on a line: xargs -L would join the next one)
  echo "rendering $(wc -l < "$1" | tr -d ' ') voices, $NPROC at a time"
  (cd "$OUT" && xargs -L 1 -P "$NPROC" sh "$ROOT/songs/render.sh" < "$1")
}

install_show() {  # install_show <id> <files...> (show.json on stdin)
  id=$1; shift
  mkdir -p "$ROOT/public/shows/$id"
  cp "$@" "$ROOT/public/shows/$id/"
  cat > "$ROOT/public/shows/$id/show.json"
  echo "installed public/shows/$id (?show=$id)"
}
