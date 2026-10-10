Yoroji Tool — CoD4 animations in BO2 Redacted multiplayer

Open Yoroji Tool.exe and click "Launch BO2 & apply".
Your game folders and 142 basic animations are already selected.
It also attaches to BO2 if the game is already open.
Keep the importer open while playing. "Stop & restore" or closing the
importer restores the original animation entries. BO2's fastfiles and
executable are not changed. Restarting BO2 also clears the imports.

The presets contain 22 death clips plus compatible running, walking,
sprinting, crouching, crawling, jumping, and stance animations. These
replace third-person body animation slots, so use a third-person view,
another player, or a suitable demo camera to see them. First-person
weapon/hand animations are outside this tool's scope.

To add another CoD4 animation, use "Import a clip...", select a compiled
CoD4 XAnim (binary version 17), and choose the BO2 body slot to replace.
Selections are saved. "Load basic animations" resets the selection to
the presets and extracts them from your CoD4 installation.
GIF, SEAnim and XANIM_EXPORT text files require a separate asset compiler;
they cannot be imported directly here.

Keep the entire folder together, including _internal and tools.
Tested on this machine with Redacted MP build 43.1337.7, t6mpv43.exe,
on Carrier. All 142 clips passed data and restoration checks; running
and a representative death clip were inspected on the BO2 character.
Every clip/weapon/model combination has not been visually inspected.
Supported animation-bank signatures are checked before changes are made.
If BO2 runs elevated, the importer must have matching process access.

Source and licenses
The importer source is in source/ under GPL-3.0-or-later (LICENSE.txt).
Build with Python 3.12 and PyInstaller:
python -m PyInstaller --windowed --onedir --name "Yoroji Tool" source/runtime_app.py
Place tools/Unlinker.exe beside the resulting executable.
Unlinker is OpenAssetTools v0.33.0 (GPL-3.0):
https://github.com/Laupetin/OpenAssetTools/releases/tag/v0.33.0
https://github.com/Laupetin/OpenAssetTools/tree/v0.33.0
Its corresponding source archive is in source/OpenAssetTools-v0.33.0.zip.
Animation format and pool discovery references:
https://github.com/Laupetin/OpenAssetTools
https://github.com/Scobalula/Greyhound/blob/master/src/WraithXCOD/WraithXCOD/GameBlackOps2.cpp
Python and Tcl/Tk license notices are in _internal/licenses/.
