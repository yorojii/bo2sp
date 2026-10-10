"""Third-person camera helper for local Redacted multiplayer matches."""
from pathlib import Path

CAMERA_SCRIPT = '''// Yoroji Tool camera helper v1
init()
{
    level thread yoroji_camera_connect();
}
yoroji_camera_connect()
{
    for (;;)
    {
        level waittill("connecting", player);
        player thread yoroji_camera_spawn();
    }
}
yoroji_camera_spawn()
{
    self endon("disconnect");
    level endon("game_ended");
    for (;;)
    {
        self waittill("spawned_player");
        if (self isHost())
        {
            if (!isDefined(self.yorojiCameraEnabled))
                self.yorojiCameraEnabled = true;
            wait 2;
            self setClientThirdPerson(self.yorojiCameraEnabled);
            self iprintln("^2Yoroji camera: hold [{+activate}] and press [{+actionslot 1}] to toggle third person.");
            self thread yoroji_camera_keys();
        }
    }
}
yoroji_camera_keys()
{
    self endon("disconnect");
    self endon("death");
    level endon("game_ended");
    pressed = false;
    for (;;)
    {
        combo = false;
        if (self useButtonPressed() && self actionSlotOneButtonPressed())
            combo = true;
        menu_open = false;
        if (isDefined(self.MenuOpen))
        {
            if (self.MenuOpen)
                menu_open = true;
        }
        if (combo && !pressed && !menu_open)
        {
            if (self.yorojiCameraEnabled)
                self.yorojiCameraEnabled = false;
            else
                self.yorojiCameraEnabled = true;
            self setClientThirdPerson(self.yorojiCameraEnabled);
            if (self.yorojiCameraEnabled)
                self iprintlnbold("^2Third person ON");
            else
                self iprintlnbold("^3First person ON");
        }
        pressed = combo;
        wait 0.05;
    }
}
'''

def install_camera(folder):
    root=Path(folder)
    if not (root/'Redacted.ini').is_file():raise ValueError('Choose your BO2 Redacted folder first.')
    path=root/'data/scripts/yoroji_third_person.gsc'
    data=CAMERA_SCRIPT.encode('ascii')
    if path.exists() and path.read_bytes()!=data:
        raise ValueError('The camera script was edited outside Yoroji Tool. It has been preserved.')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(data)
    return path
