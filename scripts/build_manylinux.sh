#!/usr/bin/env bash
# Build tools only; no development paths enter Python runtime.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${CARGO_HOME:?Mount a Rust 1.90.0 toolchain and set CARGO_HOME}"
: "${RUSTUP_HOME:?Set RUSTUP_HOME for the same toolchain}"
export PATH="$CARGO_HOME/bin:$PATH"
PYTHON=${PY_SKIA_BUILD_PYTHON:-/opt/python/cp313-cp313/bin/python}
export CARGO_TARGET_DIR=${CARGO_TARGET_DIR:-"$PWD/target"}
"$PYTHON" -m venv "$CARGO_TARGET_DIR/build-venv"
export PATH="$CARGO_TARGET_DIR/build-venv/bin:$PATH"
python -m pip install maturin==1.9.6 meson==1.7.2 ninja==1.13.0
# Obtain the original pinned Skia sources and embedded FreeType capability set.
FORCE_SKIA_BUILD=1 cargo build --release --locked -p py-skia-canvas-native
SKIA_SOURCE=${SKIA_SOURCE_DIR:-"$PWD/crates/skia-bindings/skia"}
test -f "$SKIA_SOURCE/third_party/externals/freetype/builds/unix/configure.raw"
SKIA_LIB=$(find "$CARGO_TARGET_DIR/release/build" -path '*/out/skia/libskia.a' -print -quit)
test -n "$SKIA_LIB"
FC_DIR="$CARGO_TARGET_DIR/fontconfig-2.17.1"
python - "$FC_DIR" <<'PY'
import hashlib,io,sys,tarfile,urllib.request
from pathlib import Path
p=Path(sys.argv[1]);p.mkdir(exist_ok=False)
raw=urllib.request.urlopen('https://archive.ubuntu.com/ubuntu/pool/main/f/fontconfig/fontconfig_2.17.1.orig.tar.gz').read()
assert hashlib.sha256(raw).hexdigest()=='f07504cef87f171ee1748352e2df9b9f125352f620fa0d03a9284306ea2c40a4'
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as t:t.extractall(p,filter='data')
PY
mkdir -p "$CARGO_TARGET_DIR/freetype-pc"
# FreeType's pkg-config version is its libtool version, not its API version.
FT_PC_VERSION=$(sed -n "s/^version_info='\([^']*\)'/\1/p" "$SKIA_SOURCE/third_party/externals/freetype/builds/unix/configure.raw" | tr : .)
printf 'Name: FreeType 2\nDescription: Pinned Skia embedded FreeType\nVersion: %s\nLibs: -L%s -lskia -lstdc++ -lm -ldl -lpthread\nCflags: -I%s/third_party/externals/freetype/include\n' "$FT_PC_VERSION" "$(dirname "$SKIA_LIB")" "$SKIA_SOURCE" > "$CARGO_TARGET_DIR/freetype-pc/freetype2.pc"
export PKG_CONFIG_PATH="$CARGO_TARGET_DIR/freetype-pc"
FC_SOURCE=$(find "$FC_DIR" -mindepth 1 -maxdepth 1 -type d -print -quit)
meson setup --wrap-mode=nofallback "$CARGO_TARGET_DIR/fontconfig-build" "$FC_SOURCE" --prefix=/opt/skia-static-libs --libdir=lib --sysconfdir=/etc --localstatedir=/var --default-library=static --buildtype=release -Db_staticpic=true -Ddoc=disabled -Dtools=disabled -Dtests=disabled -Dcache-build=disabled -Dnls=disabled -Dxml-backend=expat
meson compile -C "$CARGO_TARGET_DIR/fontconfig-build"
meson install -C "$CARGO_TARGET_DIR/fontconfig-build"
export SKIA_STATIC_FONTCONFIG_DIR=/opt/skia-static-libs/lib
maturin build --release --locked --interpreter "$PYTHON" --compatibility manylinux_2_28 --out dist
