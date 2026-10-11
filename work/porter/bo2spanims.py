"""BO2SPAnims: CoD4 / MW2 / BO2 SP / Zombies animations in BO2 Redacted MP — Qt front end (GPL-3.0-or-later).

The window is a retro-terminal theme built from one HSL accent color (Settings tab).
All behavior lives in core.Core; this module only draws it and forwards user input.
"""
import ctypes,sys
from pathlib import Path
from ctypes import wintypes
from PySide6 import QtCore,QtGui,QtWidgets
from PySide6.QtCore import Qt
from core import Core,GAMES,THEME_PRESETS,DEFAULT_THEME,k

APP_NAME='BO2SPANIMS'
CHANNEL_URL='' # Placeholder: the watermark links to the creator's channel once the URL is known.
ASSETS=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/'assets'
FONT='Consolas'

def hsl(h,s,l,alpha=255):
    color=QtGui.QColor.fromHslF((h%360)/360,max(0,min(s,100))/100,max(0,min(l,100))/100);color.setAlpha(alpha);return color
def palette(theme):
    h,s,l=theme['h'],theme['s'],theme['l']
    return {'acc':hsl(h,s,l),'mid':hsl(h,s*0.7,l*0.75),'dim':hsl(h,s*0.6,l*0.38),'bg':hsl(h,s*0.35,5),'panel':hsl(h,s*0.35,8),'sel':hsl(h,s*0.5,14),'ink':hsl(h,s*0.5,7)}
def stylesheet(c):
    n={key:value.name() for key,value in c.items()}
    return f"""
QWidget{{background:{n['bg']};color:{n['acc']};font-family:{FONT};font-size:13px}}
QTabWidget::pane{{border:none;border-top:1px solid {n['dim']}}}
QLabel#muted,QHeaderView::section{{color:{n['mid']}}}
QLabel#title{{font-size:20px;font-weight:bold;letter-spacing:3px;background:transparent}}
QLabel#section{{font-weight:bold;letter-spacing:1px;padding-top:6px}}
QLabel#chip{{border:1px solid {n['dim']};border-radius:3px;padding:2px 8px}}
QPushButton{{background:transparent;border:1px solid {n['dim']};border-radius:3px;padding:4px 10px}}
QPushButton:hover{{border-color:{n['acc']}}}
QPushButton:pressed{{background:{n['sel']}}}
QPushButton:disabled{{color:{n['dim']}}}
QPushButton:checked{{background:{n['acc']};color:{n['ink']};border-color:{n['acc']}}}
QLineEdit,QComboBox,QDoubleSpinBox,QPlainTextEdit{{background:{n['panel']};border:1px solid {n['dim']};border-radius:3px;padding:3px 6px;selection-background-color:{n['acc']};selection-color:{n['ink']}}}
QLineEdit:focus,QComboBox:focus{{border-color:{n['acc']}}}
QComboBox QAbstractItemView{{background:{n['panel']};border:1px solid {n['dim']};selection-background-color:{n['acc']};selection-color:{n['ink']}}}
QTableView{{background:{n['bg']};border:1px solid {n['dim']};border-radius:3px;gridline-color:transparent;selection-background-color:{n['sel']};selection-color:{n['acc']};outline:0}}
QTableView::item:selected{{border:1px solid {n['acc']}}}
QHeaderView::section{{background:{n['bg']};border:none;border-bottom:1px solid {n['dim']};padding:4px 6px}}
QTabBar::tab{{background:transparent;border:1px solid {n['dim']};border-radius:3px;padding:4px 9px;margin:0 5px 6px 0}}
QTabBar::tab:selected{{background:{n['acc']};color:{n['ink']};border-color:{n['acc']}}}
QTabBar::tab:hover{{border-color:{n['acc']}}}
QCheckBox{{spacing:8px}}
QCheckBox::indicator{{width:12px;height:12px;border:1px solid {n['acc']};background:transparent}}
QCheckBox::indicator:checked{{background:{n['acc']}}}
QSlider::groove:horizontal{{height:4px;background:{n['dim']}}}
QSlider::handle:horizontal{{background:{n['acc']};width:12px;margin:-5px 0;border-radius:2px}}
QScrollBar:vertical{{background:{n['bg']};width:10px;margin:0}}
QScrollBar::handle:vertical{{background:{n['dim']};min-height:24px;border-radius:3px}}
QScrollBar::add-line,QScrollBar::sub-line{{height:0}}
QScrollArea{{border:none}}
QFrame#rule{{background:{n['dim']};max-height:1px;min-height:1px}}
QFrame#card{{background:{n['acc']};border-radius:4px}}
QFrame#card QLabel,QFrame#card QCheckBox{{color:{n['ink']};background:transparent}}
QFrame#card QPushButton{{color:{n['ink']};border:1px solid {n['ink']}}}
QFrame#card QPushButton:checked{{background:{n['ink']};color:{n['acc']}}}
QFrame#card QFrame#rule{{background:{n['ink']}}}
QFrame#card QCheckBox::indicator{{border-color:{n['ink']}}}
QFrame#card QCheckBox::indicator:checked{{background:{n['ink']}}}
QMenu{{background:{n['panel']};border:1px solid {n['dim']}}}
QMenu::item{{padding:4px 18px}}
QMenu::item:selected{{background:{n['acc']};color:{n['ink']}}}
QToolTip{{background:{n['panel']};color:{n['acc']};border:1px solid {n['dim']}}}
"""

def rule():
    line=QtWidgets.QFrame();line.setObjectName('rule');return line
def label(text='',name=None):
    widget=QtWidgets.QLabel(text)
    if name:widget.setObjectName(name)
    return widget
def row(*widgets,stretch_at=None,spacing=8):
    box=QtWidgets.QHBoxLayout();box.setContentsMargins(0,0,0,0);box.setSpacing(spacing)
    for i,widget in enumerate(widgets):
        if i==stretch_at:box.addStretch(1)
        box.addLayout(widget) if isinstance(widget,QtWidgets.QLayout) else box.addWidget(widget)
    if stretch_at==len(widgets):box.addStretch(1)
    return box

class Poster(QtCore.QObject):
    """Runs callables on the UI thread; emit() is safe from worker threads."""
    run=QtCore.Signal(object)
    def __init__(self):super().__init__();self.run.connect(lambda fn:fn(),Qt.QueuedConnection)

class ClipModel(QtCore.QAbstractTableModel):
    HEADERS=('★','Source animation','Scene / zone','Sec','Loop','Bones')
    def __init__(self,core,game):super().__init__();self.core=core;self.game=game;self.rows=[]
    def set_rows(self,rows):self.beginResetModel();self.rows=rows;self.endResetModel()
    def rowCount(self,parent=QtCore.QModelIndex()):return 0 if parent.isValid() else len(self.rows)
    def columnCount(self,parent=QtCore.QModelIndex()):return 0 if parent.isValid() else 6
    def headerData(self,section,orientation,role=Qt.DisplayRole):
        if role==Qt.DisplayRole and orientation==Qt.Horizontal:return ('★','Source animation','Game · zone' if self.game=='Favorites' else 'Scene / zone','Sec','Loop','Bones')[section]
    def data(self,index,role=Qt.DisplayRole):
        if role!=Qt.DisplayRole or not index.isValid():return None
        item=self.core.catalog[self.rows[index.row()]];column=index.column()
        if column==0:return '★' if self.core.clip_key(item) in self.core.favorites else ''
        if column==1:return item['name']
        if column==2:return f"{item['game']} · {item['zone']}" if self.game=='Favorites' else item['zone']
        if column==3:return f"{item['frames']/item['fps']:.2f}"
        if column==4:return 'yes' if item['loop'] else 'no'
        return item['bones']
    def refresh_stars(self):
        if self.rows:self.dataChanged.emit(self.index(0,0),self.index(len(self.rows)-1,0))

class Watermark(QtWidgets.QLabel):
    def __init__(self,window):
        super().__init__();self.window=window;self.source=QtGui.QPixmap(str(ASSETS/'watermark.png'))
        self.setCursor(Qt.PointingHandCursor);self.setToolTip('Visit the creator’s channel');self.setStyleSheet('background:transparent')
    def tint(self,color):
        if self.source.isNull():return
        ratio=self.devicePixelRatioF();source=self.source.scaledToHeight(int(30*ratio),Qt.SmoothTransformation)
        tinted=QtGui.QPixmap(source.size());tinted.fill(Qt.transparent);painter=QtGui.QPainter(tinted)
        painter.drawPixmap(0,0,source);painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn);painter.fillRect(tinted.rect(),QtGui.QColor(color.red(),color.green(),color.blue(),215));painter.end()
        tinted.setDevicePixelRatio(ratio);self.setPixmap(tinted)
    def mousePressEvent(self,event):
        if CHANNEL_URL:QtGui.QDesktopServices.openUrl(QtCore.QUrl(CHANNEL_URL))
        else:self.window.core.set_status('Channel link coming soon.')

class LibraryTab(QtWidgets.QWidget):
    def __init__(self,window,game):
        super().__init__();self.window=window;self.core=window.core;self.game=game
        self.query=QtWidgets.QLineEdit();self.query.setPlaceholderText('> search');self.query.textChanged.connect(self.render)
        self.zone=QtWidgets.QComboBox();self.zone.setMinimumWidth(220);self.zone.currentTextChanged.connect(self.render)
        self.count=label('',name='muted')
        self.model=ClipModel(self.core,game);self.table=QtWidgets.QTableView();self.table.setModel(self.model)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows);self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.verticalHeader().hide();self.table.setShowGrid(False);self.table.setWordWrap(False);self.table.verticalHeader().setDefaultSectionSize(22)
        header=self.table.horizontalHeader();header.setSectionResizeMode(1,QtWidgets.QHeaderView.Stretch);header.setHighlightSections(False);header.setDefaultAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        for column,width in ((0,28),(2,230),(3,60),(4,50),(5,56)):self.table.setColumnWidth(column,width)
        self.table.selectionModel().currentRowChanged.connect(lambda current,previous:self.core.choose_clip(self.selected()))
        self.table.doubleClicked.connect(lambda index:self.core.use_clip(self.selected()))
        self.slot=window.slot_box()
        use=window.plain_button('Use selected clip',lambda:self.core.use_clip(self.selected()))
        favorite=window.action_button('favorite:'+game,'Remove favorite' if game=='Favorites' else '★ Favorite',lambda:self.core.toggle_favorite(self.selected()))
        layout=QtWidgets.QVBoxLayout(self);layout.setContentsMargins(0,6,0,0)
        layout.addLayout(row(self.query,label('Game' if game=='Favorites' else 'Scene / zone',name='muted'),self.zone));layout.addWidget(self.count);layout.addWidget(self.table,1)
        layout.addLayout(row(label('BO2 slot',name='muted'),self.slot,use,favorite,stretch_at=4))
    def selected(self):
        index=self.table.currentIndex();return self.model.rows[index.row()] if index.isValid() and index.row()<len(self.model.rows) else None
    def reload_zones(self):
        current=self.zone.currentText() or 'All';self.zone.blockSignals(True);self.zone.clear();self.zone.addItems(['All',*self.core.zones(self.game)])
        self.zone.setCurrentText(current if current in ['All',*self.core.zones(self.game)] else 'All');self.zone.blockSignals(False);self.render()
    def render(self):
        rows=self.core.clips(self.game,self.query.text(),self.zone.currentText() or 'All');self.model.set_rows(rows)
        self.count.setText(f'{len(rows):,} favorite clips • ★ Favorite in any library tab adds a clip here' if self.game=='Favorites' else f'{len(rows):,} character clips • choose a looping slot for movement or a death slot for a death clip')

class Window(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__();self.poster=Poster();self.buttons={};self.slots=[];self.glow_targets=[];self.closing=False;self.built=False
        self.setWindowTitle(APP_NAME);self.resize(1180,900);self.setMinimumSize(980,760)
        self.core=Core(self);self.build();self.built=True
        self.save_timer=QtCore.QTimer(self);self.save_timer.setSingleShot(True);self.save_timer.timeout.connect(self.core.save)
        self.timer=QtCore.QTimer(self);self.timer.timeout.connect(self.core.tick);self.timer.start(20)
        self.apply_theme();self.changed('catalog','mapping','sets','hotkeys','target','targets','snapshot','status','live','busy','replay_note','folders')
    # ui interface used by core.Core
    def post(self,fn):self.poster.run.emit(fn)
    def append_log(self,text):self.log.appendPlainText(text)
    def confirm(self,title,text):return QtWidgets.QMessageBox.question(self,title,text)==QtWidgets.QMessageBox.Yes
    def ask_text(self,title,prompt,initial):
        text,ok=QtWidgets.QInputDialog.getText(self,title,prompt,text=initial or '');return text if ok else None
    def message(self,kind,title,text):(QtWidgets.QMessageBox.critical if kind=='error' else QtWidgets.QMessageBox.information)(self,title,text)
    def ask_file(self,title):return QtWidgets.QFileDialog.getOpenFileName(self,title)[0] or None
    def focus_neutral(self):self.setFocus()

    # Widgets
    def plain_button(self,text,callback,checkable=False):
        button=QtWidgets.QPushButton(text);button.setFocusPolicy(Qt.NoFocus);button.setCheckable(checkable);button.clicked.connect(callback);return button
    def action_button(self,action,text,callback):
        """Button that can be given a hotkey by right-click; its label shows the key as [KEY]."""
        button=self.plain_button(text,callback);button.setProperty('base',text);self.buttons[action]=button
        button.setContextMenuPolicy(Qt.CustomContextMenu);button.customContextMenuRequested.connect(lambda pos:self.hotkey_menu(button,action))
        self.core.register_action(action,text.replace('&&','&'),button.click,button.isEnabled);return button
    def hotkey_menu(self,button,action):
        menu=QtWidgets.QMenu(self);name=self.core.key_for(action)
        menu.addAction(f'Change hotkey ({name})…' if name else 'Set hotkey…',lambda:self.core.begin_capture(action))
        if name:menu.addAction('Clear hotkey',lambda:self.core.clear_hotkey(action))
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))
    def slot_box(self):
        box=QtWidgets.QComboBox();box.setEditable(True);box.setMinimumWidth(300);box.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        box.activated.connect(lambda i,b=box:self.core.manual_target(b.currentText()));box.lineEdit().editingFinished.connect(lambda b=box:b.currentText()!=self.core.target and self.core.manual_target(b.currentText()))
        self.slots.append(box);return box
    def glow(self,widget):self.glow_targets.append(widget);return widget

    def build(self):
        central=QtWidgets.QWidget();self.setCentralWidget(central);central.setFocusPolicy(Qt.StrongFocus);self.setFocusPolicy(Qt.StrongFocus)
        layout=QtWidgets.QVBoxLayout(central);layout.setContentsMargins(16,12,16,10);layout.setSpacing(10)
        title=self.glow(label(APP_NAME,name='title'))
        self.bo2_chip=label('BO2 ○ waiting',name='chip');self.import_chip=label('imports ○ off',name='chip')
        self.launch=self.action_button('launch_apply','▶ Launch BO2 && apply',self.core.start);self.stopbutton=self.action_button('stop_restore','■ Stop && restore',self.core.stop)
        layout.addLayout(row(title,label('CoD4 / MW2 / BO2 SP / Zombies → BO2 Redacted',name='muted'),self.bo2_chip,self.import_chip,self.launch,self.stopbutton,stretch_at=2))
        self.card=QtWidgets.QFrame();self.card.setObjectName('card');self.glow(self.card);card=QtWidgets.QVBoxLayout(self.card);card.setContentsMargins(14,10,14,10);card.setSpacing(6)
        self.follow_label=label();self.detected=label();self.replay_note=label()
        heading=label('LIVE TARGET');heading.setStyleSheet('font-weight:bold;letter-spacing:1px')
        card.addLayout(row(heading,self.follow_label,stretch_at=1));card.addWidget(self.detected);card.addWidget(self.replay_note);card.addWidget(rule())
        self.apply_button=self.plain_button('',self.core.request_replay);self.apply_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.apply_button.customContextMenuRequested.connect(lambda pos:self.hotkey_menu(self.apply_button,'apply_anim'))
        self.lock=QtWidgets.QCheckBox('Lock target');self.lock.setFocusPolicy(Qt.NoFocus);self.lock.toggled.connect(self.core.set_locked)
        self.freelook_button=self.plain_button('',lambda checked:self.core.set_hotkey_options(freelook_enabled=checked),checkable=True)
        self.freelook_button.setContextMenuPolicy(Qt.CustomContextMenu);self.freelook_button.customContextMenuRequested.connect(lambda pos:self.hotkey_menu(self.freelook_button,'freelook'))
        self.freelook_button.setToolTip('Hold the key in BO2 to orbit the third-person camera. Click to turn on or off; right-click to change the key.')
        card.addLayout(row(self.apply_button,self.lock,self.freelook_button,stretch_at=3,spacing=10));layout.addWidget(self.card)
        self.tabs=QtWidgets.QTabWidget();self.tabs.setDocumentMode(True);layout.addWidget(self.tabs,1)
        self.libraries={}
        for game in ('Favorites',*GAMES):
            tab=LibraryTab(self,game);self.libraries[game]=tab;self.tabs.addTab(tab,'★ Favorites' if game=='Favorites' else game)
        self.tabs.addTab(self.build_replacements(),'Replacements');self.tabs.addTab(self.build_debug(),'Debug');self.tabs.addTab(self.build_settings(),'Settings')
        layout.addWidget(rule())
        self.status=label();self.status.setWordWrap(True);self.hints=label('',name='muted');self.watermark=Watermark(self)
        footer=row(self.status,self.hints,self.watermark,spacing=16);footer.setStretch(0,1);layout.addLayout(footer)
    def build_replacements(self):
        page=QtWidgets.QWidget();layout=QtWidgets.QVBoxLayout(page);layout.setContentsMargins(0,6,0,0)
        self.mapping_table=QtWidgets.QTableWidget(0,2);self.mapping_table.setHorizontalHeaderLabels(['BO2 animation slot','Source clip'])
        self.mapping_table.horizontalHeader().setSectionResizeMode(1,QtWidgets.QHeaderView.Stretch);self.mapping_table.setColumnWidth(0,360)
        self.mapping_table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft|Qt.AlignVCenter);self.mapping_table.verticalHeader().hide();self.mapping_table.setShowGrid(False);self.mapping_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.mapping_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows);self.mapping_table.verticalHeader().setDefaultSectionSize(22)
        layout.addWidget(self.mapping_table,1)
        remove=self.action_button('remove_selected','Remove selected',lambda:self.core.remove({item.text() for item in self.mapping_table.selectedItems() if item.column()==0}))
        clear=self.action_button('clear_selection','Clear selection',self.core.clear)
        self.set_box=QtWidgets.QComboBox();self.set_box.setMinimumWidth(240)
        save=self.action_button('save_set','Save set…',lambda:(lambda name:name and self.set_box.setCurrentText(name))(self.core.save_set(self.set_box.currentText())))
        load=self.action_button('load_set','Load set',lambda:self.core.load_set(self.set_box.currentText()))
        delete=self.action_button('delete_set','Delete set',lambda:self.core.delete_set(self.set_box.currentText()))
        separator=QtWidgets.QFrame();separator.setObjectName('rule');separator.setFixedWidth(1);separator.setMinimumHeight(24);separator.setMaximumHeight(9999)
        layout.addLayout(row(remove,clear,separator,save,self.set_box,load,delete,stretch_at=7));return page
    def build_debug(self):
        page=QtWidgets.QWidget();layout=QtWidgets.QVBoxLayout(page);layout.setContentsMargins(0,6,0,0)
        self.live_label=label();layout.addWidget(label('Animation layers contributing to your character right now.',name='muted'))
        self.layers=QtWidgets.QTableWidget(0,5);self.layers.setHorizontalHeaderLabels(['Active BO2 animation','Layer','Blend','Action','Your replacement'])
        self.layers.horizontalHeader().setDefaultAlignment(Qt.AlignLeft|Qt.AlignVCenter);self.layers.verticalHeader().hide();self.layers.setShowGrid(False);self.layers.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.layers.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows);self.layers.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.layers.horizontalHeader().setSectionResizeMode(4,QtWidgets.QHeaderView.Stretch);self.layers.setColumnWidth(0,320);self.layers.verticalHeader().setDefaultSectionSize(22)
        layout.addWidget(self.layers,2)
        use=self.action_button('use_highlighted','Use highlighted target',self.use_highlighted)
        layout.addLayout(row(use,label('Choose a Body layer for a full-character animation.',name='muted'),self.live_label,stretch_at=2))
        layout.addWidget(label('LOG',name='section'));self.log=QtWidgets.QPlainTextEdit();self.log.setReadOnly(True);layout.addWidget(self.log,1);return page
    def build_settings(self):
        scroll=QtWidgets.QScrollArea();scroll.setWidgetResizable(True);page=QtWidgets.QWidget();scroll.setWidget(page)
        layout=QtWidgets.QVBoxLayout(page);layout.setContentsMargins(0,6,12,0);layout.setSpacing(8)
        layout.addWidget(label('APPEARANCE › ACCENT COLOR',name='section'))
        grid=QtWidgets.QGridLayout();grid.setHorizontalSpacing(10);self.sliders={};self.slider_values={}
        for i,(key,name,low,high) in enumerate((('h','Hue',0,360),('s','Saturation',0,100),('l','Lightness',20,85))):
            slider=QtWidgets.QSlider(Qt.Horizontal);slider.setRange(low,high);slider.setFocusPolicy(Qt.NoFocus);value=label();value.setMinimumWidth(48)
            slider.valueChanged.connect(lambda v,key=key:(self.core.set_theme(save=False,**{key:v}),self.save_timer.start(400)));self.sliders[key]=slider;self.slider_values[key]=value
            grid.addWidget(label(name,name='muted'),i,0);grid.addWidget(slider,i,1);grid.addWidget(value,i,2)
        layout.addLayout(grid)
        presets=[self.plain_button(name,lambda checked=False,v=values:self.core.set_theme(h=v[0],s=v[1],l=v[2])) for name,values in THEME_PRESETS.items()]
        self.glow_box=QtWidgets.QCheckBox('Text glow');self.glow_box.setFocusPolicy(Qt.NoFocus);self.glow_box.toggled.connect(lambda on:self.core.set_theme(glow=on))
        reset=self.plain_button('Reset',lambda:self.core.set_theme(**DEFAULT_THEME))
        layout.addLayout(row(label('Presets',name='muted'),*presets,self.glow_box,reset,stretch_at=len(presets)+1))
        layout.addWidget(rule());layout.addWidget(label('HOTKEYS',name='section'))
        self.apply_enabled=QtWidgets.QCheckBox('Apply anim hotkey');self.apply_enabled.toggled.connect(lambda on:self.core.set_hotkey_options(replay_enabled=on))
        self.apply_key=self.plain_button('',lambda:self.core.begin_capture('apply_anim'))
        self.freelook_enabled=QtWidgets.QCheckBox('Third-person freelook (hold)');self.freelook_enabled.toggled.connect(lambda on:self.core.set_hotkey_options(freelook_enabled=on))
        self.freelook_key=self.plain_button('',lambda:self.core.begin_capture('freelook'))
        self.speed=QtWidgets.QDoubleSpinBox();self.speed.setRange(0.01,2.0);self.speed.setSingleStep(0.05);self.speed.setDecimals(2);self.speed.valueChanged.connect(lambda v:self.core.set_hotkey_options(freelook_speed=v))
        for box in (self.apply_enabled,self.freelook_enabled):box.setFocusPolicy(Qt.NoFocus)
        layout.addLayout(row(self.apply_enabled,self.apply_key,stretch_at=2))
        layout.addLayout(row(self.freelook_enabled,self.freelook_key,label('Speed',name='muted'),self.speed,label('° per mouse pixel; wheel zooms, release to snap back',name='muted'),stretch_at=5))
        layout.addWidget(label('Click a key button, then press any key (Esc cancels). Right-click most other buttons to give them a hotkey; it works while BO2 is focused.',name='muted'))
        layout.addWidget(rule());layout.addWidget(label('GAME FOLDERS',name='section'))
        self.folder_edits={}
        for key,name in (('bo2','BO2 Redacted'),('cod4','CoD4'),('mw2','MW2')):
            edit=QtWidgets.QLineEdit();browse=self.plain_button('Browse',lambda checked=False,e=edit:self.browse(e));self.folder_edits[key]=edit
            name_label=label(name,name='muted');name_label.setMinimumWidth(110);layout.addLayout(row(name_label,edit,browse))
        layout.addLayout(row(self.plain_button('Save folders',self.save_folders),stretch_at=1))
        layout.addWidget(rule());layout.addWidget(label('LIBRARY AND GAME',name='section'))
        self.basics=self.action_button('load_basics','Load CoD4 basics',self.core.load_basics)
        importer=self.action_button('import_file','Import animation file…',self.core.import_clip)
        self.reindex_button=self.action_button('refresh_libraries','Refresh source libraries',self.core.reindex)
        camera=self.action_button('enable_camera','Install third person plugin',self.core.enable_camera)
        layout.addLayout(row(self.basics,importer,self.reindex_button,camera,stretch_at=4))
        layout.addWidget(label('Closing BO2SPAnims restores BO2’s original animations.',name='muted'));layout.addStretch(1);return scroll

    # Actions needing widget state
    def use_highlighted(self):
        selected=self.layers.selectedItems()
        if selected and self.core.lock_highlighted(self.layers.item(selected[0].row(),0).text()):self.tabs.setCurrentIndex(0)
    def browse(self,edit):
        path=QtWidgets.QFileDialog.getExistingDirectory(self,'Choose folder',edit.text())
        if path:edit.setText(str(Path(path)))
    def save_folders(self):self.core.set_folders(self.folder_edits['cod4'].text(),self.folder_edits['mw2'].text(),self.folder_edits['bo2'].text());self.core.set_status('Game folders saved.')

    # Refresh from core
    def changed(self,*fields):
        if not self.built:return # The core reports its initial state before the widgets exist.
        core=self.core
        for field in fields:
            if field=='status':self.status.setText(core.status)
            elif field=='live':
                running=bool(core.worker and core.worker.is_alive());session=core.session
                self.import_chip.setText(f'imports ● {len(session.imported)} live' if running and session else 'imports ● starting' if running else 'imports ○ off');self.live_label.setText(core.live)
            elif field=='catalog':
                for tab in self.libraries.values():tab.reload_zones()
            elif field=='favorites':
                for game,tab in self.libraries.items():
                    if game=='Favorites':tab.render()
                    else:tab.model.refresh_stars()
            elif field=='mapping':self.render_mapping();self.render_card()
            elif field=='sets':
                current=self.set_box.currentText();self.set_box.clear();self.set_box.addItems(sorted(core.saved_sets));self.set_box.setCurrentText(current if current in core.saved_sets else '')
            elif field=='hotkeys':self.render_hotkeys()
            elif field in ('target','targets'):self.render_slots();self.render_card()
            elif field=='replay_note':self.replay_note.setText(core.replay_note)
            elif field=='snapshot':self.render_snapshot()
            elif field=='busy':
                idle=core.idle();self.launch.setEnabled(idle);self.basics.setEnabled(idle);self.reindex_button.setEnabled(idle);self.changed('live')
            elif field=='folders':
                for key,edit in self.folder_edits.items():edit.setText(getattr(core,key))
            elif field=='theme':self.apply_theme()
    def render_slots(self):
        for box in self.slots:
            box.blockSignals(True)
            if box.count()!=len(self.core.targets):box.clear();box.addItems(self.core.targets)
            box.setCurrentText(self.core.target);box.blockSignals(False)
    def render_card(self):
        core=self.core;self.follow_label.setText('Following' if core.follow_live else 'Locked')
        self.lock.blockSignals(True);self.lock.setChecked(not core.follow_live);self.lock.blockSignals(False)
        mapped=core.mapping.get(core.target);self.detected.setText(f'{core.detected}   →   {core.describe(mapped) if mapped else "Original BO2"}' if core.last_snapshot.get('ready') else core.detected)
    def render_snapshot(self):
        core=self.core;snapshot=core.last_snapshot;self.render_card()
        self.bo2_chip.setText(f"BO2 ● {snapshot['pid']}" if snapshot.get('pid') else 'BO2 ○ waiting')
        items=snapshot.get('animations',[]);table=self.layers;selected={i.text() for i in table.selectedItems() if i.column()==0}
        table.setRowCount(len(items))
        for r,item in enumerate(items):
            values=(item['target'],item['layer'],f"{item['weight']:.0%}",item['action'],core.describe(core.mapping[item['target']]) if item['target'] in core.mapping else 'Original BO2')
            for c,value in enumerate(values):
                cell=table.item(r,c)
                if cell is None:cell=QtWidgets.QTableWidgetItem();table.setItem(r,c,cell)
                if cell.text()!=value:cell.setText(value)
                cell.setForeground(self.colors['acc'] if item['selectable'] else self.colors['mid'])
            if item['target'] in selected and not table.item(r,0).isSelected():table.selectRow(r)
    def render_mapping(self):
        core=self.core;table=self.mapping_table;rows=sorted(core.mapping.items());table.setRowCount(len(rows))
        for r,(name,path) in enumerate(rows):table.setItem(r,0,QtWidgets.QTableWidgetItem(name));table.setItem(r,1,QtWidgets.QTableWidgetItem(core.describe(path)))
        self.tabs.setTabText(self.tabs.indexOf(table.parentWidget()),f'Replacements {len(rows)}' if rows else 'Replacements')
    def render_hotkeys(self):
        core=self.core
        for action,button in self.buttons.items():
            name=core.key_for(action);base=button.property('base');button.setText(f'[{name}] {base}' if name else base)
        self.apply_button.setText(f'[{core.apply_name}] Apply anim' if core.apply_vk else 'Apply anim')
        self.freelook_button.blockSignals(True);self.freelook_button.setChecked(core.freelook_enabled);self.freelook_button.blockSignals(False)
        self.freelook_button.setText(f"[{core.freelook_name if core.freelook_vk else '—'}] Freelook")
        self.apply_key.setText(core.apply_name);self.freelook_key.setText(core.freelook_name)
        for box,value in ((self.apply_enabled,core.replay_enabled),(self.freelook_enabled,core.freelook_enabled)):box.blockSignals(True);box.setChecked(value);box.blockSignals(False)
        self.speed.blockSignals(True);self.speed.setValue(core.freelook_speed);self.speed.blockSignals(False)
        hints=[]
        if core.apply_vk and core.replay_enabled:hints.append(f'[{core.apply_name}] Apply')
        if core.freelook_vk and core.freelook_enabled:hints.append(f'[{core.freelook_name}] Freelook')
        self.hints.setText('   '.join(hints+['[Right-click] Set hotkey']))
    def apply_theme(self):
        theme=self.core.theme;self.colors=palette(theme);self.setStyleSheet(stylesheet(self.colors));self.watermark.tint(self.colors['acc'])
        for key,slider in self.sliders.items():
            slider.blockSignals(True);slider.setValue(int(theme[key]));slider.blockSignals(False);self.slider_values[key].setText(f"{int(theme[key])}{'°' if key=='h' else '%'}")
        self.glow_box.blockSignals(True);self.glow_box.setChecked(bool(theme['glow']));self.glow_box.blockSignals(False)
        for widget in self.glow_targets:
            if theme['glow']:
                effect=QtWidgets.QGraphicsDropShadowEffect(widget);effect.setOffset(0,0);effect.setBlurRadius(18);glow=QtGui.QColor(self.colors['acc']);glow.setAlpha(170);effect.setColor(glow);widget.setGraphicsEffect(effect)
            else:widget.setGraphicsEffect(None)
        self.render_snapshot()

    def closeEvent(self,event):
        if not self.closing:self.closing=True;self.core.close();self.timer.stop();self.status.setText('Restoring original animations and closing…')
        if self.core.finished():event.accept()
        else:event.ignore();QtCore.QTimer.singleShot(100,self.close)

def main():
    k.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR];k.CreateMutexW.restype=wintypes.HANDLE
    handle=k.CreateMutexW(None,False,r'Local\CoD4_BO2_Redacted_Animation_Importer')
    if not handle:raise OSError(ctypes.get_last_error(),'Cannot initialize importer')
    duplicate=ctypes.get_last_error()==183
    try:
        app=QtWidgets.QApplication(sys.argv);app.setApplicationName(APP_NAME)
        if duplicate:QtWidgets.QMessageBox.information(None,'Already open','BO2SPAnims is already running. Use the existing window.');return
        window=Window();window.show();app.exec()
    finally:k.CloseHandle(handle)

if __name__=='__main__':main()
