"""Third-person camera helper for local Redacted multiplayer matches."""
from pathlib import Path

CAMERA_SCRIPT = '''// BO2SPAnims Third Person Camera v2
init()
{
    level thread tpc_connect();
}
tpc_connect()
{
    for (;;)
    {
        level waittill("connecting", player);
        player thread tpc_spawn();
    }
}
tpc_spawn()
{
    self endon("disconnect");
    level endon("game_ended");
    for (;;)
    {
        self waittill("spawned_player");
        if (self isHost())
        {
            if (!isDefined(self.tpcEnabled))
                self.tpcEnabled = true;
            wait 2;
            self setClientThirdPerson(self.tpcEnabled);
            self iprintln("^2Third Person Camera^7: hold [{+activate}] and press [{+actionslot 1}] to switch between third and first person.");
            self thread tpc_keys();
        }
    }
}
tpc_keys()
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
            if (self.tpcEnabled)
                self.tpcEnabled = false;
            else
                self.tpcEnabled = true;
            self setClientThirdPerson(self.tpcEnabled);
            if (self.tpcEnabled)
                self iprintlnbold("^2Third person");
            else
                self iprintlnbold("^3First person");
        }
        pressed = combo;
        wait 0.05;
    }
}
'''

# v1, installed as yoroji_third_person.gsc by Yoroji Tool and earlier BO2SPAnims builds; replaced on install.
LEGACY_SCRIPT = '''// Yoroji Tool camera helper v1
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
    """Install (or update) the Third Person Camera script. A script someone edited is never overwritten."""
    root=Path(folder)
    if not (root/'Redacted.ini').is_file():raise ValueError('Choose your BO2 Redacted folder first.')
    scripts=root/'data/scripts';path=scripts/'third_person_camera.gsc';legacy=scripts/'yoroji_third_person.gsc'
    data=CAMERA_SCRIPT.encode('ascii')
    if path.exists() and path.read_bytes()!=data:
        raise ValueError('third_person_camera.gsc was edited outside BO2SPAnims. It has been preserved.')
    if legacy.exists() and legacy.read_bytes()!=LEGACY_SCRIPT.encode('ascii'):
        raise ValueError('yoroji_third_person.gsc was edited outside BO2SPAnims. Remove it yourself first, or two camera scripts would run.')
    scripts.mkdir(parents=True,exist_ok=True)
    path.write_bytes(data)
    if legacy.exists():legacy.unlink() # The old version of this same script; two would fight over the camera.
    return path
