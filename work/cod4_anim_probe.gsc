#using_animtree("multiplayer");

init()
{
    precacheMpAnim("pb_combatrun_forward_loop");
    precacheMpAnim("pb_stand_death_nervedeath");
    thread connect_probe();
}

connect_probe()
{
    for (;;)
    {
        level waittill("connecting", player);
        player thread spawn_probe();
    }
}

spawn_probe()
{
    self endon("disconnect");
    level endon("game_ended");
    self waittill("spawned_player");
    wait 3;
    self setplayerangles((0, 0, 0));
    self setclientdvar("cg_thirdPerson", "0");
    self setclientdvar("cg_drawGun", "0");
    origin = self.origin + (160, 0, 0);
    actor = spawn("script_model", origin);
    actor setmodel(self getmodel());
    actor.angles = (0, 180, 0);
    actor useanimtree(#animtree);
    for (;;)
    {
        actor.origin = origin;
        actor ScriptModelPlayAnim("pb_combatrun_forward_loop");
        self iprintlnbold("^2CoD4 test: RUNNING");
        wait 8;
        actor ScriptModelPlayAnim("pb_stand_death_nervedeath");
        self iprintlnbold("^2CoD4 test: DEATH");
        wait 8;
    }
}
