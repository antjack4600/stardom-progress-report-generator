#!/usr/bin/env bash
# Build the Stardom Progress Report Generator as a desktop app for Linux/Kubuntu.
# Produces dist/stardom-progress-report-generator/ (PyInstaller onedir bundle) and
# installs a .desktop launcher + icon into ~/.local (no sudo needed).
set -euo pipefail
cd "$(dirname "$0")"

APP_NAME="stardom-progress-report-generator"

echo "==> Syncing dependencies"
uv sync

echo "==> Generating icon PNG"
uv run python - <<'EOF'
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

fig, ax = plt.subplots(figsize=(4, 4), dpi=64)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
ax.add_patch(FancyBboxPatch((0.04, 0.04), 0.92, 0.92,
                            boxstyle="round,pad=0.02,rounding_size=0.16",
                            fc="#0d5c63", ec="none"))
# page
ax.add_patch(Rectangle((0.22, 0.16), 0.56, 0.68, fc="#ffffff", ec="none"))
for y in [0.72, 0.64, 0.56]:
    ax.add_patch(Rectangle((0.28, y), 0.34, 0.04, fc="#0d5c63", ec="none"))
for x, h in [(0.30, 0.10), (0.44, 0.16), (0.58, 0.22)]:
    ax.add_patch(Rectangle((x, 0.22), 0.10, h, fc="#2a9d8f", ec="none"))
fig.savefig("assets/icon.png", transparent=True)
plt.close(fig)
print("wrote assets/icon.png")
EOF

echo "==> Building app (PyInstaller onedir)"
uv run pyinstaller --noconfirm --clean --onedir --windowed \
  --name "$APP_NAME" \
  --add-data "src:src" \
  --add-data "data/raw:data/raw" \
  --add-data "data/processed:data/processed" \
  --add-data "reports/output:reports/output" \
  --add-data "assets:assets" \
  --collect-all markdown \
  --hidden-import PySide6.QtSvg \
  desktop_app.py

BIN="$PWD/dist/$APP_NAME/$APP_NAME"
[ -x "$BIN" ] || { echo "Build failed: $BIN missing"; exit 1; }

echo "==> Installing desktop entry + icon"
mkdir -p "$HOME/.local/share/icons/hicolor/256x256/apps"
mkdir -p "$HOME/.local/share/applications"
cp assets/icon.png "$HOME/.local/share/icons/hicolor/256x256/apps/$APP_NAME.png"
sed "s|__EXEC__|$BIN|g" "packaging/$APP_NAME.desktop.in" \
  > "$HOME/.local/share/applications/$APP_NAME.desktop"
if command -v update-desktop-database >/dev/null; then
  update-desktop-database "$HOME/.local/share/applications" || true
fi

echo "Done."
echo "  Launch from your application menu: '${APP_NAME}'"
echo "  Or run directly: $BIN"
echo "  Note: reports are written next to the app bundle (dist/$APP_NAME/reports/output)."
