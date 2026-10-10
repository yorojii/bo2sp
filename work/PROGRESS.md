Target: CoD4 D:\Call of Duty 4 -> BO2 Redacted MP D:\Call of Duty Black Ops II, third-person basics. User wants all work handled and no delivery until complete.

Local execution now works with unrestricted permissions. Do not repeat sandbox troubleshooting.

Built work/porter/porter.py tkinter app with OAT 0.33.0 tools. It scans CoD4 common_mp, maps 142 shared basic pb_ names including 22 deaths, builds BO2 common_mp retaining all 9285 asset records, verifies every raw XAnim byte after the 2-byte version matches source v17->v19. 4091 other animation payloads unchanged in first probe. Engine integration test work/test_porter.py passed after removing >level.@00012d3c metadata; latest report hash 5addf06bc6d3d345cbc0568a8bdc602af800aec6818bfd5f3147b829a614bb5f. Current app is an unfinished draft; do not deliver or call runtime verified.

Original game common_mp.ff saved work/recovery/common_mp.ff SHA256 93FE48B0F0D8CC6844BE875CCAD94E0CFCF635F62EEFF00AC33F2F668A77CB77, restored to game after runtime probes. No patch_redacted installed or GSC changed.

Runtime probes: t6mp.exe is incompatible with some installed plugins; use existing t6mpv43.exe. Original plain boot loads common_mp and stays alive. +set dedicated 2 generated Error (regular MP binary not suitable server). Unsigned rebuilt common_mp produced a failure on a +map/dedicated test, so cannot attribute conclusively until plain-boot comparison. Attempted REDACTED wrapped header (TAff0100/version0x1337/auth REDACTED/zero signature) loaded to common_mp but became busy/unresponsive; not validated, do not install. Original restored and owned test process terminated.

ZonePlugin.Red32n is VMProtect packed. Existing data/weapons/mp/patch_redacted.ff has custom 0x1337/REDACTED auth header. Stock FF TAff0100 v147 signed. OAT writes TAffu100 v147 encrypted unsigned. Need determine correct Redacted loader integration. Standard asset linking works but game runtime acceptance unresolved.

Computer-use skill and guidance/api/confirmations read fully. @oai/sky initialized in persistent node_repl. list_apps/list_windows worked. sky.launch_app t6mpv43.exe refused with exact message Computer Use was not approved to use T6MVM. Do not bypass that UI access refusal. Async question requested user enable Computer Use for T6MVM/BO2, then reply enabled. Need access to complete local-match visual testing. No finalized outputs exist, respecting user's instruction.

Greyhound source downloaded work/GameBlackOps2.cpp for game debugging. Latest Steam MP offsets 0xD4B340 pool, 0xD4AF80 sizes wrong for v43. Fallback signature DB pools 56 51 FF D2 8B F0 83 C4 04 85 F6; pointer at hit-0xB, size pointer hit+0x3B. XAnim index4, XModel5. SL string lookup stride24+4; signature 33 C9 66 89 0C 10 83 C0 02 83 F8 20, string table pointer hit-0x2E. Native T6 XAnimParts size104 bytes. Potential runtime verification using debugger memory; no injection implemented.

Next: obtain permitted game UI access, inspect startup errors with exact baseline/mod comparison, fix legacy Redacted fastfile load path, then test actual movement/death in local match. Package standalone exe via installed PyInstaller only once runtime works, include original backup/restore and OAT license/source attribution. Deliver only completed, tested artifact.
