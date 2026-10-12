"""Third Person Camera install/upgrade in a throwaway game folder. No game access.
Writes work/camera_validation.json.
"""
import json,shutil,sys
from pathlib import Path
sys.path.insert(0,'work/porter')
from camera import install_camera,CAMERA_SCRIPT,LEGACY_SCRIPT,PREVIOUS_SCRIPT
root=Path('work/camera_test');shutil.rmtree(root,ignore_errors=True);root.mkdir();result={}
try:install_camera(root);raise AssertionError('Installed without Redacted.ini')
except ValueError:result['needs_redacted_folder']=True
(root/'Redacted.ini').write_text('');scripts=root/'data/scripts'
path=install_camera(root);assert path.name=='third_person_camera.gsc' and path.read_text()==CAMERA_SCRIPT;result['fresh_install']=True
assert install_camera(root)==path;result['reinstall_is_harmless']=True
path.write_text(PREVIOUS_SCRIPT,newline='\n');install_camera(root);assert path.read_text()==CAMERA_SCRIPT and PREVIOUS_SCRIPT!=CAMERA_SCRIPT;result['v0_5_0_script_updated']=True
assert 'yoroji' not in CAMERA_SCRIPT.lower() and 'Third Person Camera' in CAMERA_SCRIPT;result['renamed']=True
path.unlink();(scripts/'yoroji_third_person.gsc').write_text(LEGACY_SCRIPT,newline='\n')
install_camera(root);assert path.exists() and not (scripts/'yoroji_third_person.gsc').exists();result['old_script_replaced']=True
(scripts/'yoroji_third_person.gsc').write_text(LEGACY_SCRIPT+'// my edit\n')
try:install_camera(root);raise AssertionError('Ran beside an edited old script')
except ValueError as e:assert (scripts/'yoroji_third_person.gsc').exists();result['edited_old_script_kept']=str(e)
(scripts/'yoroji_third_person.gsc').unlink();path.write_text(CAMERA_SCRIPT+'// mine\n')
try:install_camera(root);raise AssertionError('Overwrote an edited script')
except ValueError as e:assert path.read_text().endswith('// mine\n');result['edited_script_kept']=str(e)
shutil.rmtree(root);Path('work/camera_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=1))
