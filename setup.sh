#!/usr/bin/env bash
# ==============================================================
#   Automated Master Build: krkrz_dev + Plugins  (Linux)
# ==============================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
pushd "$ROOT_DIR" >/dev/null

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

log()  { echo -e "${GREEN}[+]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[FATAL ERROR]${NC} $*" >&2; exit 1; }

# -----------------------------------------------------
# Parse flags
# -----------------------------------------------------
NO_SUDO=false
for arg in "$@"; do
    case "$arg" in
        --no-sudo) NO_SUDO=true ;;
    esac
done

if $NO_SUDO; then
    log "--no-sudo specified: skipping package manager installs."
fi

# -----------------------------------------------------
# Step 0: Detect Build Configuration
# -----------------------------------------------------
log "Configuration Setup"

ARCH="x64"
# Allow CFG=1 (Release) or CFG=2 (Debug) from environment
if [ -n "${CFG:-}" ]; then
    case "$CFG" in
        1) CONFIG="Release" ;;
        2) CONFIG="Debug" ;;
        *) warn "Unknown CFG=$CFG, defaulting to Release."; CONFIG="Release" ;;
    esac
else
    echo "[1] Release"
    echo "[2] Debug"
    read -p "Choose 1 or 2 (default: Release): " cfg_opt
    case "$cfg_opt" in
        1) CONFIG="Release" ;;
        2) CONFIG="Debug" ;;
        *) if [ -z "${cfg_opt:-}" ]; then
               CONFIG="Release"
           else
               warn "Invalid choice, defaulting to Release."
               CONFIG="Release"
           fi ;;
    esac
fi

log "Build configuration: $ARCH / $CONFIG"

# -----------------------------------------------------
# Step 1: Detect Package Manager & Install Prerequisites
# -----------------------------------------------------
log "Installing build prerequisites via package manager..."

PKG_MANAGER=""
if command -v apt-get >/dev/null 2>&1; then
    PKG_MANAGER="apt"
elif command -v dnf >/dev/null 2>&1; then
    PKG_MANAGER="dnf"
elif command -v yum >/dev/null 2>&1; then
    PKG_MANAGER="yum"
elif command -v pacman >/dev/null 2>&1; then
    PKG_MANAGER="pacman"
elif command -v zypper >/dev/null 2>&1; then
    PKG_MANAGER="zypper"
else
    err "Unsupported package manager. Please install the following manually:"
    echo "  git curl cmake ninja-build nasm gcc g++ libogg-dev libvorbis-dev"
    exit 1
fi

install_pkg() {
    local pkg="$1"
    if command -v "$pkg" >/dev/null 2>&1; then
        log "$pkg already installed"
        return
    fi
}

# Check if we can use sudo
HAS_SUDO=false
if command -v sudo >/dev/null 2>&1; then
    # Passwordless sudo?
    if sudo -n true 2>/dev/null; then
        HAS_SUDO=true
    # Interactive terminal → assume user can enter password
    elif [[ -t 0 ]]; then
        log "Interactive session detected — using sudo with password prompt."
        HAS_SUDO=true
    fi
fi

if ! $NO_SUDO; then
    case "$PKG_MANAGER" in
        apt)
            if $HAS_SUDO; then
                sudo apt-get update -y
                sudo apt-get install -y build-essential git curl cmake ninja-build nasm \
                    libogg-dev libvorbis-dev zlib1g-dev
            else
                warn "sudo unavailable (no passwordless access). Attempting without sudo..."
                apt-get update -y 2>/dev/null || warn "apt-get update failed without sudo."
                apt-get install -y build-essential git curl cmake ninja-build nasm \
                    libogg-dev libvorbis-dev zlib1g-dev 2>/dev/null || \
                    err "Cannot install packages (no sudo access and non-root user). Run this script with root privileges or install prerequisites manually."
            fi
            ;;
        dnf|yum)
            if $HAS_SUDO; then
                sudo $PKG_MANAGER install -y gcc gcc-c++ make git curl cmake ninja-build \
                    nasm libogg-devel libvorbis-devel zlib-devel
            else
                warn "sudo unavailable for $PKG_MANAGER. Please ensure prerequisites are installed manually."
            fi
            ;;
        pacman)
            if $HAS_SUDO; then
                sudo $PKG_MANAGER -S --needed --noconfirm base-devel git curl cmake ninja \
                    nasm libogg libvorbis zlib
            else
                warn "sudo unavailable for $PKG_MANAGER. Please ensure prerequisites are installed manually."
            fi
            ;;
        zypper)
            if $HAS_SUDO; then
                sudo $PKG_MANAGER install -y gcc gcc-c++ make git curl cmake ninja-build \
                    nasm libogg-devel libvorbis-devel zlib-devel
            else
                warn "sudo unavailable for $PKG_MANAGER. Please ensure prerequisites are installed manually."
            fi
            ;;
    esac
else
    # --no-sudo: skip package manager entirely, verify tools are already present
    log "Skipping package installs (--no-sudo). Verifying prerequisites..."
fi

# -----------------------------------------------------
# Step 2: Verify Required Tools
# -----------------------------------------------------
log "Checking required tools..."

for tool in git nasm cmake ninja; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        err "Required tool '$tool' not found. Please install it."
    fi
done

# Verify compiler (need at least g++ or clang++)
if ! command -v g++ >/dev/null 2>&1 && ! command -v clang++ >/dev/null 2>&1; then
    err "No C++ compiler found. Install g++ or clang++."
fi

CXX=""
if command -v g++ >/dev/null 2>&1; then
    CXX="g++"
elif command -v clang++ >/dev/null 2>&1; then
    CXX="clang++"
fi
log "Using C++ compiler: $CXX ($( $CXX --version | head -1 ))"

# -----------------------------------------------------
# Step 3: Setup vcpkg and Audio Dependencies
# -----------------------------------------------------
log "Setting up vcpkg..."
VCPKG_DIR="$ROOT_DIR/vcpkg"

# Ensure vcpkg is fully cloned (not shallow) — needed for port resolution
if [ ! -d "$VCPKG_DIR/.git/shallow" ]; then
    if [ -d "$VCPKG_DIR" ]; then
        rm -rf "$VCPKG_DIR"
    fi
    git clone https://github.com/microsoft/vcpkg.git "$VCPKG_DIR"
fi
if [ ! -f "$VCPKG_DIR/vcpkg" ]; then
    pushd "$VCPKG_DIR" >/dev/null
    ./bootstrap-vcpkg.sh -disableMetrics
    popd >/dev/null
fi

# Use a static vcpkg overlay for local installs
if ! $NO_SUDO && $HAS_SUDO; then
    # Attempt integrated install (may require sudo on some distros)
    sudo "$VCPKG_DIR/vcpkg" integrate install 2>/dev/null || warn "vcpkg integrate failed (non-fatal)"
elif $NO_SUDO; then
    log "Skipping vcpkg integrate (--no-sudo)."
else
    warn "sudo unavailable — skipping vcpkg integrate (non-fatal)."
fi

log "Installing vcpkg dependencies (x64-linux-release / x64-linux-debug)..."
"$VCPKG_DIR/vcpkg" install libogg libvorbis

export VCPKG_ROOT="$VCPKG_DIR"

# -----------------------------------------------------
# Step 4: Clone Repositories
# -----------------------------------------------------
log "Cloning repositories..."
REPO_DIR="$ROOT_DIR/krkrz_dev"

if [ ! -d "$REPO_DIR" ]; then
    git clone --recursive https://github.com/wamsoft/krkrz_dev.git "$REPO_DIR" || err "Failed to clone krkrz_dev"
else
    log "krkrz_dev already exists, skipping clone."
fi

# -----------------------------------------------------
# Step 5: Build krkrz_dev (CMake)
# -----------------------------------------------------
log "Building krkrz_dev ($CONFIG)..."
pushd "$REPO_DIR" >/dev/null

BUILD_DIR="build/x64-linux-$CONFIG"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

cmake . \
    -G Ninja \
    -DCMAKE_BUILD_TYPE="$CONFIG" \
    -DCMAKE_CXX_COMPILER="$CXX" \
    -DCMAKE_ASM_NASM_COMPILER="$(command -v nasm)" \
    -DVCPKG_TARGET_TRIPLET=x64-linux-release \
    -DCMAKE_TOOLCHAIN_FILE="$VCPKG_DIR/scripts/buildsystems/vcpkg.cmake" \
    -B "$BUILD_DIR" || err "CMake configuration failed"

cmake --build "$BUILD_DIR" --config "$CONFIG" || err "Build failed"

popd >/dev/null

# -----------------------------------------------------
# Step 5b: Clone SamplePlugin and init submodules
# -----------------------------------------------------
log "Cloning SamplePlugin (for extrans plugin)..."
SAMPLE_DIR="$ROOT_DIR/SamplePlugin"

if [ ! -d "$SAMPLE_DIR" ]; then
    git clone https://github.com/krkren/SamplePlugin.git "$SAMPLE_DIR" || err "Failed to clone SamplePlugin"
else
    log "SamplePlugin already exists, skipping clone."
fi

log "Initializing git submodules (tp_stub)..."
cd "$SAMPLE_DIR"
git submodule update --init --recursive || err "Failed to init submodules"
cd "$ROOT_DIR"

# -----------------------------------------------------
# Step 5c: Build extrans plugin from SamplePlugin
# -----------------------------------------------------
log "Building extrans plugin..."
pushd "$SAMPLE_DIR" >/dev/null
if [ -d "build-linux" ]; then rm -rf build-linux; fi
cmake --preset linux-x64 || err "SamplePlugin CMake configure failed"
CONFIG_LOWER=$(echo "$CONFIG" | tr '[:upper:]' '[:lower:]')
    cmake --build --preset "linux-x64-$CONFIG_LOWER" || err "SamplePlugin build failed"
popd >/dev/null

# -----------------------------------------------------
# Step 6: Move Files to Output
# -----------------------------------------------------
log "Moving compiled artifacts to final folder..."

mkdir -p plugin

BLD="$REPO_DIR/build/x64-linux-$CONFIG"

# Main executable — try multiple possible locations
KRKRZ=""
for candidate in \
    "$BLD/core/krkrz" \
    "$BLD/core/$CONFIG/krkrz" \
    "$BLD/core/Release/krkrz"; do
    if [ -f "$candidate" ]; then
        KRKRZ="$candidate"
        break
    fi
done
if [ -n "$KRKRZ" ]; then
    cp "$KRKRZ" ./krkrz
    log "Copied krkrz from $(dirname $KRKRZ)"
else
    # Last resort: find any executable named krkrz in the build tree
    FOUND=$(find "$BLD" -name krkrz -type f 2>/dev/null | head -1)
    if [ -n "$FOUND" ]; then
        cp "$FOUND" ./krkrz
        log "Copied krkrz from $FOUND"
    else
        err "krkrz executable not found in $BLD"
    fi
fi

# SDL3 shared library
SDL3=""
for candidate in \
    "$BLD/_deps/sdl3-build/libSDL3.so" \
    "$BLD/_deps/sdl3-build/libSDL3.so.0" \
    "$BLD/core/$CONFIG/SDL3.so" \
    "$BLD/core/Release/SDL3.so"; do
    if [ -f "$candidate" ]; then
        SDL3="$candidate"
        break
    fi
done
if [ -n "$SDL3" ]; then
    cp "$SDL3" ./ 2>/dev/null || true
fi
# Also copy any SDL3 .so files found in _deps
for f in $(find "$BLD/_deps/sdl3-build" -name "libSDL3.so*" -type f 2>/dev/null); do
    cp "$f" ./ 2>/dev/null || true
done

# All compiled .so plugins — programmatic, no hardcoding
PLUGIN_COUNT=0
while IFS= read -r -d '' so_file; do
    if [ ! -f "./plugin/$(basename "$so_file")" ]; then
        cp "$so_file" ./plugin/ 2>/dev/null && log "Copied $(basename "$so_file") to plugin/"
        PLUGIN_COUNT=$((PLUGIN_COUNT + 1))
    fi
done < <(find "$BLD" -name "*.so" -type f -print0 2>/dev/null)

if [ "$PLUGIN_COUNT" -eq 0 ]; then
    warn "No .so plugin files found in the build tree."
fi

# Copy extrans plugin to plugin folder
if [ -f "$SAMPLE_DIR/build-linux/libextrans.so" ]; then
    cp "$SAMPLE_DIR/build-linux/libextrans.so" ./plugin/ && \
    log "Copied libextrans.so to plugin/"
else
    warn "libextrans.so not found at $SAMPLE_DIR/build-linux/libextrans.so"
fi

# -----------------------------------------------------
# Step 7: Cleanup source trees (optional)
# -----------------------------------------------------
log "Cleaning up build artifacts and clones for distribution..."

if [ -d "$VCPKG_DIR" ]; then rm -rf "$VCPKG_DIR"; fi
if [ -d "$REPO_DIR" ]; then rm -rf "$REPO_DIR"; fi
if [ -d "$SAMPLE_DIR" ]; then rm -rf "$SAMPLE_DIR"; fi

echo ""
echo "==================================================="
echo -e "${GREEN}[SUCCESS]${NC} Engine and plugins compiled successfully."
echo "  Architecture : $ARCH"
echo "  Configuration: $CONFIG"
echo "==================================================="
popd >/dev/null
exit 0
