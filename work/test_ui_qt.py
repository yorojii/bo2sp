"""Qt window wiring, offscreen. No game writes (the importer start is stubbed).

Checks tab layout, the live-target card controls, hotkey labels, theme and watermark
against an isolated profile (work/ui_qt_test). Writes work/ui_qt_validation.json.
"""
import os,json,time
os.environ.setdefault('QT_QPA_PLATFORM','offscreen');os.environ.setdefault('QT_QPA_FONTDIR',r'C:\Windows\Fonts')
from pathlib import Path
from test_support import isolated_root
import core
from PySide6 import QtWidgets
root=isolated_root('ui_qt_test',lambda profile:(profile.pop('hotkeys',None),profile.pop('theme',None),profile.pop('favorites',None)))
core.Core.start=lambda self:None
import bo2spanims
app=QtWidgets.QApplication([]);window=bo2spanims.Window();window.show();result={}
def pump(seconds=0.3):
    end=time.monotonic()+seconds
    while time.monotonic()<end:app.processEvents();time.sleep(0.01)
try:
    pump()
    tabs=[window.tabs.tabText(i).split(' ')[0] if not window.tabs.tabText(i).startswith('★') else 'Favorites' for i in range(window.tabs.count())]
    assert tabs==['Favorites','CoD4','MW2','BO2','BO2','Replacements','Debug','Settings'],tabs;result['tabs']=[window.tabs.tabText(i) for i in range(window.tabs.count())]
    c=window.core
    assert window.apply_button.text()==f'[{c.apply_name}] Apply anim';result['apply_button_shows_key']=window.apply_button.text()
    assert 'use_clip:CoD4' not in window.buttons and 'lock_target' not in window.buttons;result['use_clip_and_lock_have_no_hotkey']=True
    c.last_snapshot={'ready':True,'primary':{'target':'pb_crouch_alert'}};c.detected_at=time.monotonic()
    window.lock.setChecked(True);pump(0.05);assert not c.follow_live and c.target=='pb_crouch_alert' and window.follow_label.text()=='Locked'
    window.lock.setChecked(False);pump(0.05);assert c.follow_live and window.follow_label.text()=='Following';result['lock_checkbox']=True
    was=c.freelook_enabled;window.freelook_button.click();pump(0.05);assert c.freelook_enabled==(not was) and window.freelook_enabled.isChecked()==c.freelook_enabled
    window.freelook_button.click();pump(0.05);result['freelook_toggle_syncs_settings']=True
    c.capture_action='stop_restore';c.assign_hotkey(0x4B,'K');pump(0.05)
    assert window.buttons['stop_restore'].text().startswith('[K] '),window.buttons['stop_restore'].text();result['hotkey_label']=window.buttons['stop_restore'].text()
    c.clear_hotkey('stop_restore');pump(0.05);assert not window.buttons['stop_restore'].text().startswith('[')
    before=window.styleSheet();window.sliders['h'].setValue(190);pump(0.6)
    assert c.theme['h']==190 and window.styleSheet()!=before and json.loads((root/'profile.json').read_text())['theme']['h']==190;result['hue_slider_recolors_and_saves']=True
    window.glow_box.setChecked(False);pump(0.05);assert window.card.graphicsEffect() is None
    window.glow_box.setChecked(True);pump(0.05);assert window.card.graphicsEffect() is not None;result['glow_toggle']=True
    assert window.watermark.pixmap() is not None and not window.watermark.pixmap().isNull()
    opened=[];bo2spanims.QtGui.QDesktopServices.openUrl=lambda url:opened.append(url.toString()) # Don't really open a browser.
    window.watermark.mousePressEvent(None);assert opened==['https://www.youtube.com/@Yorojiii'],opened;result['watermark_opens_channel']=opened[0]
    lib=window.libraries['CoD4'];lib.query.setText('mantle');pump(0.05);assert 0<lib.model.rowCount()<50;lib.table.selectRow(0);pump(0.05)
    assert c.replay_path==c.catalog[lib.model.rows[0]]['path'];result['library_search_and_select']=lib.model.rowCount()
    window.buttons['favorite:CoD4'].click();pump(0.05);assert window.libraries['Favorites'].model.rowCount()==1
    window.libraries['Favorites'].table.selectRow(0);window.buttons['favorite:Favorites'].click();pump(0.05);assert window.libraries['Favorites'].model.rowCount()==0;result['favorite_buttons']=True
    window.sliders['h'].setValue(32);pump(0.6)
finally:
    window.close();end=time.monotonic()+10
    while not window.core.finished() and time.monotonic()<end:app.processEvents();time.sleep(0.05)
    window.close();app.processEvents()
assert window.core.finished();result['closed_cleanly']=True
Path('work/ui_qt_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=1))
