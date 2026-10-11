BO2SPAnims
CoD4 single-player / multiplayer, MW2 actor and BO2 single-player / Zombies animations in BO2 Redacted MP

Open BO2SPAnims.exe. Your game folders and saved animation choices are ready.
Click "Launch BO2 & apply" (top right) to launch BO2 or attach to your
running game. Keep the tool open while playing or viewing demos.

The window
- Top bar: the BO2 and imports status, Launch BO2 & apply, Stop & restore.
- Live target card: what your character is playing now and its current
  replacement, the apply anim button, Lock target and Freelook.
- Tabs: Favorites, CoD4, MW2 Actors, BO2 SP, BO2 Zombies, Replacements,
  Debug (live animation layers and the log) and Settings.
- Footer: status, your hotkeys, and the creator watermark.
Settings has the accent color (hue, saturation, lightness, presets and
text glow), hotkeys, game folders and the library / camera tools.

Third-person camera
In Settings, click "Install third person plugin" once, then start a new
custom match. The camera switches to third person two seconds after the
host spawns. Hold F and press 1 to switch between first and third person
with your current bindings (Use + scorestreak up). Close the mod menu first.
The helper is installed at data/scripts/yoroji_third_person.gsc in BO2.
It stays installed between launches. The console cg_thirdperson setting
alone does not switch the live player's camera in this Redacted setup.

Third-person freelook: with Freelook on (the [Alt] Freelook button in the
live target card, or Settings), hold Alt in BO2 and move the mouse to orbit
the camera around your character without turning; the mouse wheel zooms.
Release Alt to snap back. Speed (Settings) is degrees per mouse pixel.
Right-click the Freelook button, or click its key in Settings, to choose
another key. While BO2 is focused the freelook key is not passed to the
game, so Alt+key no longer beeps; Alt+Tab, Alt+F4 and Alt+Enter still work.

Choosing animations
1. Start a multiplayer match. The live target card shows your current BO2
   body animation, such as Idle, Running or Sprinting.
2. Tick "Lock target" to keep that slot while browsing clips. Untick it to
   follow your current animation again.
3. Open CoD4, MW2 Actors, BO2 SP or BO2 Zombies and search a clip or filter
   by scene / zone.
4. Select a clip and click "Use selected clip" (or double-click it). It
   applies to the running match automatically.
The BO2 slot box below each list shows the slot clips go to; choosing one
there locks the target. The Debug tab lists the contributing animation
layers and blend weights; highlight a Body layer and click "Use highlighted
target" to lock it. Upper-body layers are shown for context; choose a Body
slot for actor clips.

Apply anim key
Select a clip, then press the apply anim key (default F6, shown on the
button as [F6] Apply anim) with BO2 in the foreground. It applies the clip
to your current slot and restarts it from the beginning. You can hold
another game button, such as aim or sprint, while pressing it. Each press
restarts the clip once; holding the key does not repeat. In Settings, the
Apply anim hotkey checkbox turns it off; click its key, then press any
keyboard key to change it (Esc cancels). Right-click the button to change
or clear the key from the card.
With Lock target off, every press applies the selected clip to the detected
body slot: running, crouching, prone or idle. With Lock target on, the key
uses the locked slot, which must currently contribute to your pose.
To play a one-shot clip on demand, lock a standing idle slot and apply your
clip there, then stay in that idle pose and press the key. If you change
weapon or stance, BO2 can use a different idle slot; with Lock target off
the next press follows it. Apply anim does not force an inactive locked
running or death slot onto an idle character. Your character can blend
several slots, so replace the contributing Body slots shown in Debug if the
original pose still blends in.

Hotkeys for buttons
Right-click most buttons (Stop & restore, ★ Favorite, Load set, …) and
choose Set hotkey. The key is shown on the button as [KEY] and presses it
while BO2 is in the foreground. Giving a key to a second button moves it
there. Keys still reach the game, so avoid keys your game uses.

Replacements, favorites and saved sets
The Replacements tab lists your choices. Removing an entry or clearing the
selection restores those slots during the active session. An empty
selection keeps the original animations. Choices are saved between
launches. You can mix clips from any library.
Favorites: select a clip in any library tab and click "★ Favorite"; the
Favorites tab lists all starred clips, filterable by game, and works like
the other tabs. Click "Remove favorite" there to unstar.
Saved sets: in Replacements, "Save set…" stores every current replacement
under a name. Pick a set and "Load set" to swap it in (it replaces the
current replacements and applies live if a match is running); "Delete set"
removes the saved copy only. Favorites and sets remember clips by game,
scene and name, so they survive library updates.
The detector follows your local character. Replacements affect every
character using the selected BO2 asset slot in this game session.

Libraries
The libraries contain 2,171 CoD4 character clips, 3,047 MW2 actor clips,
7,222 BO2 single-player clips and 2,218 BO2 Zombies clips extracted from
your installations. The CoD4 tab includes single-player scenes and
multiplayer animations. MW2 Actors contains single-player NPC/body clips,
including mission-specific scenes. BO2 SP contains the campaign and Strike
Force AI and cinematic character clips (ai_, ch_ ...), read from the
campaign zones in your BO2 folder's zone/all. BO2 Zombies contains zombie
AI clips plus the Zombies player body and upper-body clips.
In Settings, "Load CoD4 basics" resets to 142 compatible basics, including
22 deaths, plus running, walking, sprinting, crouching, crawling, jumping
and stances.

Building the libraries (one click)
On a new install, open Settings and click "Build libraries". It extracts
the character animations from every game it finds: BO2 single-player and
Zombies from your BO2 folder, plus CoD4 and MW2 if they are installed.
Games that aren't installed are skipped (and keep any clips already in the
library). Progress shows in the status line and the Debug log; it takes
several minutes. Click the button again (it reads "Cancel build") to stop;
building again continues where it stopped, because each zone is cached.
Game folders are found automatically (a running BO2, Steam libraries and
common install folders such as X:\Games). If one isn't found, set it in
Settings > Game folders or click "Detect game folders". Your replacements,
favorites and saved sets keep working after a rebuild.

Choose looping clips for movement slots and one-shot clips for deaths.
Scene clips retain their original timing and movement; their framing and
weapon pose depend on the BO2 model and the slot you choose. Optional
face, clothing or accessory bones absent from BO2 are omitted and listed
in the log. The character's core bones must be available before import.
This changes third-person body animation slots. Use a third-person view,
another player or a suitable demo camera to see the animations.
It does not import actor models, whole scripted scenes or first-person
weapon/hand animations.

"Import animation file" (Settings) accepts compiled CoD4/MW2/BO2 XAnim
binaries and Yoroji's .yanim cache files. GIF, SEAnim and XANIM_EXPORT text
files need a separate asset compiler and cannot be loaded directly.

Stop & restore, closing the tool or restarting BO2 returns to the original
animations. The tool updates session data, not the game's executable or
fastfiles. Keep the whole folder together, including _internal, tools,
library and state. No Python installation is required.
Animation streams share aligned memory blocks to reduce fragmentation.
Failed preparation reclaims new blocks before any game entries change.
Published data stays allocated until BO2 exits because animation trees
can retain references during transitions. Restart BO2 to clear that data
if you have changed or reapplied a large number of clips in one session.
Tested with this installation of Redacted MP 43.1337.7 (t6mpv43.exe).
All library records passed parsing checks. Representative clips passed
live import/restoration checks; not every clip/model/weapon combination
has been visually checked. Validation.json records the checks performed.
The individual-clip fix preserves BO2's original bone list and indices,
including when changing clips in a running match. All library clips passed
conversion and inverse-stream checks on BO2 body rigs, with bone motion
preserved. The 142 basic clips also passed against their own BO2 slots.
Static poses are encoded with a valid interpolation interval.
Actor clips without a torso stabilizer use the correct BO2 lower-spine
position basis, keeping the torso attached to the pelvis during playback.
Existing stabilized movement clips retain their original position tracks.

Source and licenses
The source/ folder contains the importer under GPL-3.0-or-later.
LICENSE.txt contains the license.
Build with Python 3.10, PySide6-Essentials 6.11.2 and PyInstaller 6.16:
python -m PyInstaller --windowed --onedir --name BO2SPAnims --icon source/assets/app.ico --add-data "source/assets;assets" source/bo2spanims.py
Keep tools/Unlinker.exe, library and profile.json beside the built executable.
The interface uses Qt for Python (PySide6), licensed under the LGPL-3.0;
see https://www.qt.io/qt-licensing and https://doc.qt.io/qtforpython-6/.
Unlinker is OpenAssetTools v0.33.0 (GPL-3.0):
https://github.com/Laupetin/OpenAssetTools/releases/tag/v0.33.0
Its source archive is source/OpenAssetTools-v0.33.0.zip.
Layout and discovery references:
https://github.com/Laupetin/OpenAssetTools
https://github.com/Scobalula/Greyhound
https://github.com/Amyst82/T6SDK
https://github.com/callofduty4x/CoD4x_Server
Python notices are in _internal/licenses/ where present.

Your settings are saved crash-safely: profile.json is written in one step,
and the previous copy is kept as profile.json.bak. If profile.json is ever
damaged, the tool loads the backup automatically and says so in the log.
