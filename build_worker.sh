#!/bin/bash
set -e

echo "Installing requirements..."
pip install -r requirements.txt --break-system-packages --upgrade

# Create the binaries directory in the tauri app if it doesn't exist
mkdir -p ../autonome-desktop/src-tauri/binaries/

echo "Compiling worker.py to a standalone executable..."
# Include web3 and eth_account as hidden imports as requested
pyinstaller --onefile \
    --hidden-import web3 \
    --hidden-import eth_account \
    --copy-metadata py_ecc \
    --collect-all eth_account \
    --collect-all eth_utils \
    --collect-all web3 \
    --collect-all botchain \
    --name worker-bin \
    worker.py

echo "Detecting host target triple for Tauri sidecar..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    TARGET_TRIPLE="x86_64-unknown-linux-gnu"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # Assuming Apple Silicon for now, or x86_64-apple-darwin
    if [[ $(uname -m) == "arm64" ]]; then
        TARGET_TRIPLE="aarch64-apple-darwin"
    else
        TARGET_TRIPLE="x86_64-apple-darwin"
    fi
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    TARGET_TRIPLE="x86_64-pc-windows-msvc"
else
    TARGET_TRIPLE="unknown"
    echo "Could not detect OS. Please rename the binary manually."
fi

if [ "$TARGET_TRIPLE" != "unknown" ]; then
    echo "Copying binary to Tauri binaries folder as worker-bin-$TARGET_TRIPLE"
    if [[ "$TARGET_TRIPLE" == *"windows"* ]]; then
        cp dist/worker-bin.exe "../autonome-desktop/src-tauri/binaries/worker-bin-$TARGET_TRIPLE.exe"
    else
        cp dist/worker-bin "../autonome-desktop/src-tauri/binaries/worker-bin-$TARGET_TRIPLE"
    fi
fi

echo "Build complete."
