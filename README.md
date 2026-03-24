# CrimsonWings
### Glide Stamina Patcher for Crimson Desert
*by DatGuySnowfox*

---

CrimsonWings is a lightweight patcher that lets you customize the stamina cost of gliding in Crimson Desert. Set any value between 0.001 and 65.535 for both normal and fast glide independently — lower the drain for a more relaxed experience or crank it up for a challenge.

A backup of the original file is created automatically on first patch so you can always restore defaults.

---

## Features

- Patch normal glide and fast glide stamina cost independently
- Auto-detects your Crimson Desert install across all drives
- Manual Browse and Scan Drives options if auto-detect misses it
- Automatic backup of the original file on first patch
- One-click restore to default values via the Uninstall tab
- Covers Damian, CrowWing, and RocketPack glide roots
- Single `.exe` — no install, no dependencies

---

## Requirements

- Crimson Desert (Steam)
- **Close the game before patching**
- No additional mods or files required

---

## Usage

### Pre-built EXE
1. Download `CrimsonWings.exe` from [Releases](../../releases)
2. Close Crimson Desert
3. Run `CrimsonWings.exe`
4. The game folder will be detected automatically — if not, click **Browse** or **Scan Drives**
5. Enter your desired stamina values and click **Apply Patch**

### Build from Source
Requires Python 3.8+ and PyInstaller.

```bash
# Clone the repo
git clone https://github.com/DatGuySnowfox/CrimsonWings.git
cd CrimsonWings

# Build the exe (Windows only)
build_exe.bat
```

The `.exe` will appear in the `dist` folder.

---

## Default Values

| Glide type | Default stamina cost |
|---|---|
| Normal glide | 25 |
| Fast glide | 50 |

Valid range: **0.001 – 65.535**

---

## Uninstalling / Restoring Defaults

Open `CrimsonWings.exe` and go to the **Uninstall** tab.

- If a backup exists it will be restored directly
- If no backup is found, the original default byte values are written back

---

## How It Works

CrimsonWings patches two byte offsets inside `0008\0.paz` in the Crimson Desert game directory. The stamina values are stored as little-endian two's-complement negations of the scaled integer value (cost × 1000). Guard bytes on either side of each offset are verified before any write to ensure compatibility with the current game build.

---

## Disclaimer

This tool modifies game files. Use at your own risk. Always keep a backup — CrimsonWings creates one automatically. Not affiliated with Pearl Abyss.
