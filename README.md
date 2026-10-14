# BO2SP

Swap animations from other Call of Duty games into **Black Ops II Redacted multiplayer**, live, while the game is running.

Pick a clip from COD4, MW2, MW3 (single-player actors), BO2 SP, or BO2 ZM, choose which BO2 body animation to replace, and see it on your character. This is useful for staging scenes in custom matches and filming them in Theater (works alongside t6mvm).

## Features

- **Over 19,000 body animations**: COD4 (MP + SP), MW2, MW3 (campaign + Spec Ops actors), BO2 SP (campaign/Strike Force), and BO2 ZM (Zombies), all searchable.
- **Live target**: follows the animation your character is playing right now, so you know which slot you're replacing.
- **Apply anim hotkey** (default F6, rebindable): apply the selected clip to your current slot and restart it, without tabbing out.
- **Freelook** (hold Alt, rebindable): orbit the third-person camera around your character without turning them.
- **Favorites and saved sets**: star clips, save replacement sets, and share them as copy-paste codes.
- **Hotkeys on anything**: right-click any button to bind a key to it.
- **Appearance**: Terminal, iOS (liquid glass), and Android styles, with a full HSL accent color.
- **One-click library build**: detects your game folders and extracts the animation libraries itself.
- **Nothing permanent**: your game files aren't touched. "Stop & restore", closing the tool, or restarting BO2 puts the original animations back.

## Requirements

- Windows 10/11
- BO2 Redacted (`t6mpv43.exe`, build 43.1337.7)
- Optional: COD4, MW2 and MW3 installs to build their libraries (MW3: campaign and Spec Ops; Steam version). The BO2 SP and BO2 ZM libraries come from your Redacted install.

## Usage

1. Run `BO2SP.exe` (keep the whole folder together).
2. On a fresh install, open **Settings → Build libraries**.
3. Click **Launch BO2 & apply** (or start BO2 first; the tool attaches).
4. In a match, pick a clip, choose the BO2 slot (or let Live target follow you), and press **Apply anim**.
5. Use third person to see your own character. **Settings → Install third person plugin** adds a toggle.

Replacements apply to every character using that slot, and they show during Theater playback while the tool is open.

## Building from source

Python 3.10+, PySide6-Essentials, and PyInstaller:

```
pip install PySide6-Essentials pyinstaller
cd work
python -m PyInstaller --noconfirm --clean BO2SP.spec
```

Entry point: `work/porter/bo2sp.py`. Library extraction uses [OpenAssetTools](https://github.com/Laupetin/OpenAssetTools) (`Unlinker.exe`, GPL-3.0) placed in `tools/` next to the EXE.

## Credits

- Created by [Yoroji](https://www.youtube.com/@Yorojiii) & brokn
- [OpenAssetTools](https://github.com/Laupetin/OpenAssetTools), [Greyhound](https://github.com/Scobalula/Greyhound), and [T6SDK](https://github.com/Amyst82/T6SDK) for format and engine references

## License

[GPL-3.0](LICENSE). Bundled OpenAssetTools is also GPL-3.0.

Animation data stays on your machine and is extracted from games you own. None is included in this repository.
