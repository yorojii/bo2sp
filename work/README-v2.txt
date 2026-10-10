Yoroji Tool
CoD4 single-player / multiplayer and MW2 actor animations in BO2 Redacted MP

Open Yoroji Tool.exe. Your game folders and saved animation choices are ready.
Click "Launch BO2 & apply" to launch BO2 or attach to your running game.
Keep Yoroji Tool open while playing or viewing demos.

Third-person camera
Click "Enable third-person camera" once, then start a new custom match.
The camera switches to third person two seconds after the host spawns.
Hold F and press 1 to switch between first and third person with your
current bindings (Use + scorestreak up). Close the mod menu first.
The helper is installed at data/scripts/yoroji_third_person.gsc in BO2.
It stays installed between launches. The console cg_thirdperson setting
alone does not switch the live player's camera in this Redacted setup.

Choosing animations
1. Start a multiplayer match. Live character target shows your current
   BO2 body animation, such as Idle, Running or Sprinting.
2. Click "Lock current target" to keep that slot while browsing clips.
3. Open CoD4 or MW2 Actors and search a clip or filter by scene / zone.
4. Select a clip and click "Use selected clip". It applies to the running
   match automatically. Keep Yoroji Tool open.
Leave "Follow current animation" checked to select your current slot
automatically. Turn it off to choose a BO2 slot manually. The Live target
tab lists contributing animation layers and blend weights. Highlight a
Body layer and click "Use highlighted target" to lock it. Upper-body
layers are shown for context; choose a Body slot for actor clips.

You can change clips while the importer is active. Clicking the same
clip again restarts it from the beginning if that target is currently
playing on your character. A running or death slot plays when BO2 uses
that action. A one-shot clip in an idle slot may hold its final pose.
Select a clip, then press F6 with BO2 in the foreground to apply and replay it.
The Replay hotkey checkbox and key dropdown let you disable or change it.
Replay now performs the same action from the tool. Each press restarts
the clip once; holding the key does not repeatedly restart it. The key
and selected clip are saved. Choose a key unused by your game controls.
With Follow current animation enabled, every press applies the selected
clip to the detected body slot: running, crouching, prone or idle. You
can highlight another source clip without clicking Use selected clip,
then return to BO2 and press F6. Imports start automatically if needed.
With Follow disabled, F6 uses the slot displayed in BO2 slot to replace.
That locked slot must currently contribute to your character's pose.
To play a one-shot clip on demand, lock a standing idle slot and apply
your clip there, then stay in that idle pose and press the replay key.
If you change weapon or stance, BO2 can use a different idle slot. Follow
current animation handles that change on the next press. Replay does
not force an inactive locked running or death slot onto an idle character.
Your character can blend several slots, so replace the contributing
Body slots shown in Live target if the original pose still blends in.

The Selected replacements tab lists your choices. Removing an entry or
clearing the selection restores those slots during the active session.
An empty selection keeps the original animations. Basics are loaded only
when you click "Load CoD4 basics". Choices are saved between launches.
You can mix clips from both games or clear the selection to use just one.
The detector follows your local character. Replacements affect every
character using the selected BO2 asset slot in this game session.

The libraries contain 2,171 CoD4 character clips and 3,047 MW2 actor clips
extracted from your installations. The CoD4 tab includes single-player
scenes and multiplayer animations. MW2 Actors contains single-player
NPC/body clips, including mission-specific scenes.
"Load CoD4 basics" resets to 142 compatible basics, including 22 deaths,
plus running, walking, sprinting, crouching, crawling, jumping and stances.
"Refresh source libraries" re-extracts character clips from the game folders.
Game folders can be changed using the Game folders button.

Choose looping clips for movement slots and one-shot clips for deaths.
Scene clips retain their original timing and movement; their framing and
weapon pose depend on the BO2 model and the slot you choose. Optional
face, clothing or accessory bones absent from BO2 are omitted and listed
in the log. The character's core bones must be available before import.
This changes third-person body animation slots. Use a third-person view,
another player or a suitable demo camera to see the animations.
It does not import actor models, whole scripted scenes or first-person
weapon/hand animations.

"Import animation file" accepts compiled CoD4/MW2 XAnim binaries and
Yoroji's .yanim cache files. GIF, SEAnim and XANIM_EXPORT text files need
a separate asset compiler and cannot be loaded directly.

Stop & restore, closing Yoroji Tool or restarting BO2 returns to the
original animations. The tool updates session data, not the game's
executable or fastfiles. Keep the whole folder together, including
_internal, tools, library and state. No Python installation is required.
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
including when changing clips in a running match. All 5,218 library clips
passed conversion and inverse-stream checks on three BO2 body rigs, with
bone motion preserved. The 142 basic clips also passed against their own
BO2 slots. Static poses are encoded with a valid interpolation interval.
Actor clips without a torso stabilizer now use the correct BO2 lower-spine
position basis, keeping the torso attached to the pelvis during playback.
Existing stabilized movement clips retain their original position tracks.

Source and licenses
The source/ folder contains the importer under GPL-3.0-or-later.
LICENSE.txt contains the license.
Build with Python 3.12 and PyInstaller:
python -m PyInstaller --windowed --onedir --name "Yoroji Tool" source/runtime_app.py
Keep tools/Unlinker.exe, library and profile.json beside the built executable.
Unlinker is OpenAssetTools v0.33.0 (GPL-3.0):
https://github.com/Laupetin/OpenAssetTools/releases/tag/v0.33.0
Its source archive is source/OpenAssetTools-v0.33.0.zip.
Layout and discovery references:
https://github.com/Laupetin/OpenAssetTools
https://github.com/Scobalula/Greyhound
https://github.com/Amyst82/T6SDK
https://github.com/callofduty4x/CoD4x_Server
Python and Tcl/Tk notices are in _internal/licenses/.
