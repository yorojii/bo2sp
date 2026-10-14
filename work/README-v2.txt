BO2SP
Animations from COD4, MW2, MW3, BO2 SP and BO2 ZM in BO2 Redacted multiplayer, applied live

What it does
Pick a body animation from another Call of Duty game, choose which BO2
animation it replaces, and your character plays it straight away in BO2
Redacted MP (t6mpv43.exe). Built for staging scenes in custom matches and
filming them in Theater with t6mvm. Nothing on disk is changed: Stop &
restore, closing the tool or restarting BO2 brings the originals back.

First run
1. Unzip anywhere and keep the whole folder together (_internal, tools).
   No Python or other install is needed.
2. Open BO2SP.exe. It looks for your games automatically (a running
   BO2, Steam libraries, X:\Games and similar folders). Check or set them
   in Settings > Game folders.
3. Settings > Build libraries. Tick the games to extract (games found and
   not yet in your library are ticked) and click Build libraries. This
   takes several minutes; progress shows at the bottom. Click again to
   cancel; building again continues where it stopped.
4. Click "Launch BO2 & apply" (top right), or start BO2 yourself; the tool
   attaches to it.
5. Settings > Install Third Person Camera, once, to play custom matches you
   host in third person (hold F and press 1 to switch views).

Libraries (built from your own installs)
- COD4: single-player and multiplayer character animations.
- MW2: single-player actor animations (Steam version).
- MW3: campaign and Spec Ops actor animations (Steam version). MP
  animations aren't included yet.
- BO2 SP: campaign and Strike Force animations, from your Redacted folder.
- BO2 ZM: Zombies animations, from your Redacted folder.
A game's tab appears once its library has clips. A full build of every
game is about 19,000 clips (~900 MB).

Choosing animations
1. In a match, the Live Target card shows the BO2 animation your character
   plays right now (Idle, Running, ...).
2. Tick Lock target to keep that slot while you browse; untick it to follow
   your character again.
3. Open a game's tab, search or filter by scene / zone, and click a header
   to sort (click again to reverse).
4. Select a clip and click "Use selected clip" (or double-click it). It
   applies to the running match immediately.
Choose looping clips for movement slots and one-shot clips for deaths.
Replacements affect every character using that BO2 slot. The Debug tab
shows the animation layers blending on your character.

Apply anim key
Press the key on the [F6] Apply anim button (default F6) with BO2 focused
to apply the selected clip to your current slot and restart it. Right-click
the button, or use Settings > Hotkeys, to choose any key.

Freelook, movement and hotkeys
- Freelook (Alt): tick it on the Live Target card, then hold Alt in BO2 and
  move the mouse to orbit the camera without turning. The wheel zooms.
  Right-click it to change the key; speed is in Settings.
- Movement: opens a Speed slider (10-300%) for walking, running and
  sprinting in matches you host. Not timescale: animations play normally.
- Right-click most buttons to give them a hotkey. Keys still reach BO2.

Favorites, sets and sharing
Hover the first column of a clip list and click the star to favorite it.
Replacements > Save set... stores your current replacements; Load set swaps
them in. "Copy share code" turns a set (or your appearance) into a text
code starting with BO2SP1- that a friend pastes with "Paste share code".

Appearance
Settings > Appearance: Terminal, iOS (frosted glass; the window is left out
of screenshots and recordings while it's on) and Android (a deliberately
pixelated joke). The accent color uses full hue / saturation / lightness.

Getting help
Debug > "Copy log for support" copies your setup and recent log, with your
Windows username hidden, ready to paste. Logs are saved in logs/ (the
previous session is kept as bo2sp.old.log).

Limits
This replaces third-person body animations only: not actor models, whole
scripted scenes or first-person weapon animations. Bones the BO2 character
doesn't have (faces, gear) are left out. Not every clip / weapon / model
combination has been checked visually. Tested with Redacted MP 43.1337.7.
Published animation data stays in BO2's memory until it exits; restart BO2
after reapplying very many clips in one session.

Source and licenses
BO2SP is free software under GPL-3.0 (LICENSE.txt); its source is in
source/. Build with Python 3.10, PySide6-Essentials 6.11.2 and
PyInstaller 6.16 (see BO2SP.spec in the repository).
The interface uses Qt for Python (PySide6), LGPL-3.0.
tools/Unlinker.exe is OpenAssetTools v0.33.0 (GPL-3.0); its source is
source/OpenAssetTools-v0.33.0.zip.
https://github.com/Laupetin/OpenAssetTools/releases/tag/v0.33.0
References: OpenAssetTools, Greyhound (Scobalula) and T6SDK (Amyst82).
Animation data comes from games you own and stays on your PC; none is
included with BO2SP.

Created by Yoroji & brokn - https://www.youtube.com/@Yorojiii
