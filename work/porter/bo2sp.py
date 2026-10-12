"""BO2SP: COD4 / MW2 / MW3 / BO2 SP / BO2 ZM animations in BO2 Redacted MP — Qt front end (GPL-3.0-or-later).

The window is a retro-terminal theme built from one HSL accent color (Settings tab).
All behavior lives in core.Core; this module only draws it and forwards user input.
"""
import ctypes,os,sys,threading,time
from pathlib import Path
from ctypes import wintypes
from PySide6 import QtCore,QtGui,QtWidgets
from PySide6.QtCore import Qt
from core import Core,GAMES,SHORT,THEME_PRESETS,DEFAULT_THEME,k
LONG={short:game for game,short in SHORT.items()}
from movement import LIMITS as MOVEMENT_LIMITS
from logfile import install_crash_hooks

APP_NAME='BO2SP'
CHANNEL_URL='https://www.youtube.com/@Yorojiii' # The watermark opens the creator's channel.
ASSETS=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/'assets'
ARROW_UP,ARROW_DOWN=((ASSETS/name).as_posix() for name in ('arrow_up.png','arrow_down.png')) # iOS spin-box arrows (stylesheet urls want forward slashes).
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
QFrame#window{{border:1px solid {n['dim']}}}
QFrame#rule{{background:{n['dim']};max-height:1px;min-height:1px}}
QFrame#card{{background:{n['acc']};border-radius:4px}}
QFrame#card QLabel,QFrame#card QCheckBox{{color:{n['ink']};background:transparent}}
QFrame#card QPushButton{{color:{n['ink']};border:1px solid {n['ink']}}}
QFrame#card QPushButton:checked{{background:{n['ink']};color:{n['acc']}}}
QFrame#card QFrame#rule{{background:{n['ink']}}}
QFrame#card QWidget#cardrow,QFrame#card QSlider{{background:transparent}}
QFrame#card QSlider::groove:horizontal{{height:2px;background:{n['ink']}}}
QFrame#card QSlider::handle:horizontal{{background:{n['ink']};width:12px;margin:-6px 0;border-radius:2px}}
QFrame#card QCheckBox::indicator{{border-color:{n['ink']}}}
QFrame#card QCheckBox::indicator:checked{{background:{n['ink']}}}
QMenu{{background:{n['panel']};border:1px solid {n['dim']}}}
QMenu::item{{padding:4px 18px}}
QMenu::item:selected{{background:{n['acc']};color:{n['ink']}}}
QToolTip{{background:{n['panel']};color:{n['acc']};border:1px solid {n['dim']}}}
"""

GLASS_FONT='Segoe UI Variable Text'
GLASS_RADIUS=22 # iOS window corner radius.
def glass_palette(theme):
    """iOS (liquid glass): white text on see-through glass; the accent follows the hue."""
    h=theme['h'];white=lambda a:QtGui.QColor(255,255,255,int(255*a))
    return {'acc':hsl(h,85,55,235),'acclight':hsl(h,85,70,235),'accsoft':hsl(h,85,55,80),'text':white(1),'mid':white(0.78),'dim':white(0.28),
            'edge':white(0.18),'sel':white(0.18),'solid':QtGui.QColor(24,28,40),'ink':white(1)}
def rgba(color):return f'rgba({color.red()},{color.green()},{color.blue()},{color.alpha()})'
def gloss(top,middle,bottom,colour=(255,255,255)):
    """Vertical gloss: a bright top fading to a faint body, like a light catching curved glass."""
    r,g,b=colour;a=lambda x:int(255*x)
    return f'qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 rgba({r},{g},{b},{a(top)}),stop:0.48 rgba({r},{g},{b},{a(middle)}),stop:1 rgba({r},{g},{b},{a(bottom)}))'
def glass_stylesheet(c):
    n={key:rgba(value) for key,value in c.items()};acc=c['acc'];light=c['acclight']
    accent=f"qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {rgba(light)},stop:0.5 {rgba(acc)},stop:1 {rgba(acc)})"
    button=gloss(0.30,0.10,0.06);hover=gloss(0.40,0.16,0.10);field=gloss(0.12,0.05,0.04);panel=gloss(0.12,0.04,0.03)
    return f"""
QWidget{{background:transparent;color:{n['text']};font-family:'{GLASS_FONT}','Segoe UI';font-size:13px}}
QFrame#window{{background:transparent;border:1px solid rgba(255,255,255,70);border-top-color:rgba(255,255,255,150);border-radius:{GLASS_RADIUS}px}}
QLabel#muted,QHeaderView::section{{color:{n['mid']}}}
QLabel#title{{font-size:19px;font-weight:600;letter-spacing:0.5px}}
QLabel#section{{color:{n['mid']};font-size:11px;font-weight:600;letter-spacing:1.5px;padding-top:6px}}
QLabel#chip{{background:{button};border:1px solid {n['edge']};border-top-color:rgba(255,255,255,150);border-radius:12px;padding:3px 11px}}
QPushButton{{background:{button};border:1px solid {n['edge']};border-top-color:rgba(255,255,255,165);border-radius:13px;padding:5px 14px}}
QPushButton:hover{{background:{hover}}}
QPushButton:pressed{{background:{gloss(0.10,0.06,0.10)}}}
QPushButton:disabled{{color:{n['mid']}}}
QPushButton:checked{{background:{accent};border-color:rgba(255,255,255,120);border-top-color:rgba(255,255,255,200);color:white}}
QLineEdit,QComboBox,QDoubleSpinBox{{background:{field};border:1px solid {n['edge']};border-top-color:rgba(255,255,255,110);border-radius:13px;padding:4px 12px;selection-background-color:{n['acc']};selection-color:white}}
QPlainTextEdit{{background:{panel};border:1px solid {n['edge']};border-top-color:rgba(255,255,255,110);border-radius:18px;padding:8px}}
QDoubleSpinBox{{padding-right:30px;min-width:56px}}
QDoubleSpinBox::up-button,QDoubleSpinBox::down-button{{subcontrol-origin:border;width:24px;border:none;background:transparent;margin-right:8px}}
QDoubleSpinBox::up-button{{subcontrol-position:top right;margin-top:4px}}
QDoubleSpinBox::down-button{{subcontrol-position:bottom right;margin-bottom:4px}}
QDoubleSpinBox::up-arrow{{image:url({ARROW_UP});width:9px;height:5px}}
QDoubleSpinBox::down-arrow{{image:url({ARROW_DOWN});width:9px;height:5px}}
QDoubleSpinBox::up-arrow:hover,QDoubleSpinBox::down-arrow:hover{{width:11px;height:6px}}
QLineEdit:focus,QComboBox:focus{{border-color:{n['acc']}}}
QComboBox QAbstractItemView,QMenu,QToolTip,QDialog,QMessageBox,QInputDialog{{background:{n['solid']};color:{n['text']};border:1px solid {n['dim']}}}
QComboBox QAbstractItemView{{selection-background-color:{n['acc']};selection-color:white}}
QTableView,QTableWidget{{background:{panel};border:1px solid {n['edge']};border-top-color:rgba(255,255,255,120);border-radius:22px;gridline-color:transparent;selection-background-color:{n['sel']};selection-color:white;outline:0}}
QTableView::item{{padding:0 4px}}
QHeaderView,QHeaderView::section{{background:transparent;border:none;padding:6px 8px}}
QTabWidget::pane{{border:none}}
QTabBar{{background:transparent;qproperty-drawBase:0}}
QTabBar::tab{{background:transparent;border:1px solid transparent;border-radius:13px;padding:5px 14px;margin:0 3px 8px 0;color:{n['mid']}}}
QTabBar::tab:selected{{background:{accent};color:white;border-color:rgba(255,255,255,120);border-top-color:rgba(255,255,255,200)}}
QTabBar::tab:hover:!selected{{background:{button};color:white}}
QCheckBox{{spacing:8px}}
QCheckBox::indicator{{width:14px;height:14px;border:1px solid rgba(255,255,255,140);border-radius:4px;background:{field}}}
QCheckBox::indicator:checked{{background:{accent};border-color:rgba(255,255,255,180)}}
QSlider::groove:horizontal{{height:4px;border-radius:2px;background:rgba(255,255,255,50)}}
QSlider::sub-page:horizontal{{border-radius:2px;background:{n['acc']}}}
QSlider::handle:horizontal{{background:{gloss(1,0.92,0.82)};width:16px;height:16px;margin:-6px 0;border-radius:8px}}
QScrollBar:vertical{{background:transparent;width:10px;margin:2px}}
QScrollBar::handle:vertical{{background:rgba(255,255,255,70);min-height:24px;border-radius:4px}}
QScrollBar::add-line,QScrollBar::sub-line{{height:0}}
QScrollArea{{border:none}}
QFrame#rule{{background:{n['dim']};max-height:1px;min-height:1px}}
QFrame#card{{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 rgba(255,255,255,70),stop:0.35 {n['accsoft']},stop:1 rgba(255,255,255,12));border:1px solid rgba(255,255,255,80);border-top-color:rgba(255,255,255,210);border-radius:24px}}
QFrame#card QLabel,QFrame#card QCheckBox{{background:transparent;color:white}}
QFrame#card QPushButton{{color:white}}
QFrame#card QPushButton:checked{{background:{gloss(1,0.9,0.82)};color:{rgba(c['solid'])}}}
QFrame#card QFrame#rule{{background:rgba(255,255,255,70)}}
"""

def android_palette(theme):
    """The joke style: posterized accent (hue snapped to 45° steps), harsh contrast, no smoothing anywhere."""
    h,s=146,69 # Always Android green (#3DDC84-ish), whatever accent the other styles use.
    return {'acc':hsl(h,s,55),'mid':hsl(h,s,75),'dim':hsl(h,s,28),'bg':QtGui.QColor(16,16,16),'panel':QtGui.QColor(40,40,40),'sel':hsl(h,s,25),'ink':QtGui.QColor(0,0,0),'text':QtGui.QColor(255,255,255)}
def android_stylesheet(c):
    n={key:value.name() for key,value in c.items()}
    return f"""
QWidget{{background:{n['bg']};color:{n['text']};font-family:'Fixedsys','Terminal','Courier New';font-size:14px;font-weight:bold}}
QFrame#window{{border:3px solid {n['acc']}}}
QLabel#muted,QHeaderView::section{{color:{n['mid']}}}
QLabel#title{{font-size:20px;color:{n['acc']}}}
QLabel#section{{color:{n['acc']};padding-top:6px}}
QLabel#chip{{border:2px solid {n['acc']};padding:2px 6px}}
QPushButton{{background:{n['panel']};border:2px outset {n['mid']};padding:3px 8px}}
QPushButton:hover{{background:{n['sel']}}}
QPushButton:pressed{{border-style:inset}}
QPushButton:disabled{{color:#777777}}
QPushButton:checked{{background:{n['acc']};color:#000000;border-style:inset}}
QLineEdit,QComboBox,QDoubleSpinBox,QPlainTextEdit{{background:#000000;border:2px inset {n['mid']};padding:2px 4px;selection-background-color:{n['acc']};selection-color:#000000}}
QComboBox QAbstractItemView,QMenu,QToolTip{{background:{n['panel']};border:2px solid {n['acc']};selection-background-color:{n['acc']};selection-color:#000000}}
QTableView,QTableWidget{{background:#000000;border:2px solid {n['dim']};gridline-color:{n['dim']};selection-background-color:{n['acc']};selection-color:#000000;outline:0}}
QHeaderView::section{{background:{n['panel']};border:1px solid {n['dim']};padding:3px}}
QTabWidget::pane{{border:none;border-top:3px solid {n['acc']}}}
QTabBar::tab{{background:{n['panel']};border:2px outset {n['mid']};padding:3px 8px;margin:0 2px 0 0}}
QTabBar::tab:selected{{background:{n['acc']};color:#000000;border-style:inset}}
QCheckBox::indicator{{width:12px;height:12px;border:2px solid {n['mid']};background:#000000}}
QCheckBox::indicator:checked{{background:{n['acc']}}}
QSlider::groove:horizontal{{height:6px;background:{n['dim']}}}
QSlider::handle:horizontal{{background:{n['acc']};width:10px;margin:-6px 0}}
QScrollBar:vertical{{background:{n['panel']};width:14px}}
QScrollBar::handle:vertical{{background:{n['mid']};min-height:20px}}
QScrollBar::add-line,QScrollBar::sub-line{{height:0}}
QScrollArea{{border:none}}
QFrame#rule{{background:{n['acc']};max-height:2px;min-height:2px}}
QFrame#card{{background:{n['acc']};border:3px outset {n['mid']}}}
QFrame#card QLabel,QFrame#card QCheckBox{{color:#000000;background:transparent}}
QFrame#card QPushButton{{color:#000000;background:{n['mid']};border:2px outset #ffffff}}
QFrame#card QPushButton:checked{{background:#000000;color:{n['acc']}}}
QFrame#card QFrame#rule{{background:#000000}}
QFrame#card QWidget#cardrow,QFrame#card QSlider{{background:transparent}}
QFrame#card QSlider::groove:horizontal{{height:6px;background:#000000}}
QFrame#card QSlider::handle:horizontal{{background:{n['mid']};border:2px outset #ffffff;width:10px;margin:-6px 0}}
"""
class PixelEffect(QtWidgets.QGraphicsEffect):
    """Draws the window at 1/factor resolution and scales it back up unsmoothed: the android joke style."""
    def __init__(self,factor=2):super().__init__();self.factor=factor
    def draw(self,painter):
        try:
            pixmap=self.sourcePixmap(Qt.LogicalCoordinates,mode=QtWidgets.QGraphicsEffect.NoPad) # PySide returns only the pixmap.
            if pixmap.isNull():return self.drawSource(painter)
            small=pixmap.scaled(max(1,pixmap.width()//self.factor),max(1,pixmap.height()//self.factor),Qt.IgnoreAspectRatio,Qt.FastTransformation)
            painter.save();painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform,False)
            painter.drawPixmap(QtCore.QRectF(self.sourceBoundingRect(Qt.LogicalCoordinates).topLeft(),pixmap.deviceIndependentSize()),small,QtCore.QRectF(small.rect()));painter.restore()
        except Exception:self.drawSource(painter) # Never let the joke style break painting.

def pixelate(pixmap,factor=4):
    """Scale down and back up without smoothing, for the android style."""
    if pixmap.isNull():return pixmap
    small=pixmap.scaled(max(1,pixmap.width()//factor),max(1,pixmap.height()//factor),Qt.IgnoreAspectRatio,Qt.FastTransformation)
    return small.scaled(pixmap.width(),pixmap.height(),Qt.IgnoreAspectRatio,Qt.FastTransformation)

def transparency_enabled():
    """Windows Settings > Personalization > Colors > Transparency effects."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as key:return bool(winreg.QueryValueEx(key,'EnableTransparency')[0])
    except (OSError,ImportError):return True

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
    def __init__(self,core,game):super().__init__();self.core=core;self.game=game;self.rows=[];self.hover=-1;self.order=None
    def set_rows(self,rows):self.beginResetModel();self.rows=self.sorted(rows);self.hover=-1;self.endResetModel()
    def sort_key(self,column):
        """Clicking a header sorts: ★ favorites first, text columns alphabetically, Sec and Bones by value."""
        catalog=self.core.catalog
        def key(row):
            item=catalog[row]
            if column==0:return (self.core.clip_key(item) not in self.core.favorites,item['name'].casefold())
            if column==1:return item['name'].casefold()
            if column==2:return (SHORT.get(item['game'],item['game']).casefold() if self.game=='Favorites' else '',item['zone'].casefold(),item['name'].casefold())
            if column==3:return item['frames']/item['fps'] if item['fps'] else 0.0
            if column==4:return ('yes' if item['loop'] else 'no',item['name'].casefold())
            return item['bones']
        return key
    def sorted(self,rows):
        if not self.order:return list(rows) # Library order until a header is clicked.
        column,descending=self.order;return sorted(rows,key=self.sort_key(column),reverse=descending)
    def sort(self,column,order=Qt.AscendingOrder):
        self.order=(column,order==Qt.DescendingOrder);self.set_rows(self.rows) # A reset, so a stale selection can't point at another clip.
    def set_hover(self,row):
        """The row under the mouse shows an outlined star to click."""
        if row==self.hover:return
        old,self.hover=self.hover,row
        for changed in (old,row):
            if 0<=changed<len(self.rows):self.dataChanged.emit(self.index(changed,0),self.index(changed,0))
    def rowCount(self,parent=QtCore.QModelIndex()):return 0 if parent.isValid() else len(self.rows)
    def columnCount(self,parent=QtCore.QModelIndex()):return 0 if parent.isValid() else 6
    def headerData(self,section,orientation,role=Qt.DisplayRole):
        if role==Qt.DisplayRole and orientation==Qt.Horizontal:return ('★','Source animation','Game · zone' if self.game=='Favorites' else 'Scene / zone','Sec','Loop','Bones')[section]
    def data(self,index,role=Qt.DisplayRole):
        if not index.isValid():return None
        item=self.core.catalog[self.rows[index.row()]];column=index.column();starred=self.core.clip_key(item) in self.core.favorites
        if column==0 and role==Qt.ToolTipRole:return 'Remove from favorites' if starred else 'Add to favorites'
        if column==0 and role==Qt.TextAlignmentRole:return int(Qt.AlignCenter)
        if role!=Qt.DisplayRole:return None
        if column==0:return '★' if starred else '☆' if index.row()==self.hover else ''
        if column==1:return item['name']
        if column==2:return f"{SHORT.get(item['game'],item['game'])} · {item['zone']}" if self.game=='Favorites' else item['zone']
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
        if self.window.core.theme.get('style')=='android':tinted=pixelate(tinted,5)
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
        header=self.table.horizontalHeader();header.setSectionsClickable(True);header.setSortIndicatorShown(True);header.setSortIndicator(-1,Qt.AscendingOrder)
        header.sortIndicatorChanged.connect(lambda column,order:column>=0 and self.model.sort(column,order)) # Click a header to sort; click again to reverse.
        header.setSectionResizeMode(1,QtWidgets.QHeaderView.Stretch);header.setHighlightSections(False);header.setDefaultAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        for column,width in ((0,28),(2,340 if game=='Favorites' else 230),(3,60),(4,50),(5,56)):self.table.setColumnWidth(column,width)
        self.table.selectionModel().currentRowChanged.connect(lambda current,previous:self.core.choose_clip(self.selected()))
        self.table.doubleClicked.connect(lambda index:index.column()!=0 and self.core.use_clip(self.selected()))
        self.table.setMouseTracking(True);self.table.viewport().installEventFilter(self) # Hover and click the star column to favorite.
        self.slot=window.slot_box()
        use=window.plain_button('Use selected clip',lambda:self.core.use_clip(self.selected()))
        layout=QtWidgets.QVBoxLayout(self);layout.setContentsMargins(0,6,0,0)
        layout.addLayout(row(self.query,label('Game' if game=='Favorites' else 'Scene / zone',name='muted'),self.zone));layout.addWidget(self.count);layout.addWidget(self.table,1)
        layout.addLayout(row(label('BO2 slot',name='muted'),self.slot,use,stretch_at=3))
    def eventFilter(self,watched,event):
        kind=event.type()
        if kind==QtCore.QEvent.MouseMove:
            index=self.table.indexAt(event.position().toPoint());self.model.set_hover(index.row() if index.isValid() else -1)
            self.table.viewport().setCursor(Qt.PointingHandCursor if index.isValid() and index.column()==0 else Qt.ArrowCursor)
        elif kind==QtCore.QEvent.Leave:self.model.set_hover(-1);self.table.viewport().unsetCursor()
        elif kind in (QtCore.QEvent.MouseButtonPress,QtCore.QEvent.MouseButtonDblClick) and event.button()==Qt.LeftButton:
            index=self.table.indexAt(event.position().toPoint())
            if index.isValid() and index.column()==0:
                if kind==QtCore.QEvent.MouseButtonPress:self.toggle_star(index.row())
                return True # The star click doesn't change the selection or apply the clip.
        return False
    def toggle_star(self,row):
        if 0<=row<len(self.model.rows):self.core.toggle_favorite(self.model.rows[row])
    def selected(self):
        index=self.table.currentIndex();return self.model.rows[index.row()] if index.isValid() and index.row()<len(self.model.rows) else None
    def reload_zones(self):
        zones=self.core.zones(self.game);names=[SHORT[g] for g in GAMES if g in zones] if self.game=='Favorites' else zones # Favorites filters by game, in tab order.
        current=self.zone.currentText() or 'All';self.zone.blockSignals(True);self.zone.clear();self.zone.addItems(['All',*names])
        self.zone.setCurrentText(current if current in ['All',*names] else 'All');self.zone.blockSignals(False);self.render()
    def render(self):
        zone=self.zone.currentText() or 'All';zone=LONG.get(zone,zone) if self.game=='Favorites' else zone
        rows=self.core.clips(self.game,self.query.text(),zone);self.model.set_rows(rows)
        self.count.setText(f'{len(rows):,} favorite clips • click the ★ beside a clip to remove it; hover the ☆ column in any library to add one' if self.game=='Favorites' else f'{len(rows):,} character clips • hover the first column and click ☆ to favorite • looping slots for movement, death slots for deaths')

class TrafficLight(QtWidgets.QAbstractButton):
    """macOS-style window button: a colored dot that shows its glyph while the group is hovered."""
    COLORS={'close':('#FF5F57','#E0443E'),'minimize':('#FEBC2E','#DEA123'),'maximize':('#28C840','#1AAB29')}
    def __init__(self,kind,group):
        super().__init__();self.kind=kind;self.group=group;self.setFixedSize(16,16);self.setFocusPolicy(Qt.NoFocus) # Even sizes stay on whole pixels at 125/150/200% scaling.
        self.setToolTip({'close':'Close','minimize':'Minimize','maximize':'Maximize'}[kind])
    def paintEvent(self,event):
        fill,edge=self.COLORS[self.kind];painter=QtGui.QPainter(self);android=self.window().core.theme.get('style')=='android'
        if not android:painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtGui.QPen(QtGui.QColor(edge),0.8));painter.setBrush(QtGui.QColor(edge if self.isDown() else fill))
        painter.drawRect(QtCore.QRect(2,2,11,11)) if android else painter.drawEllipse(QtCore.QRectF(2,2,12,12))
        if self.group.hovered:
            painter.setPen(QtGui.QPen(QtGui.QColor(0,0,0,150),1.3,Qt.SolidLine,Qt.RoundCap));c=8.0
            if self.kind=='close':painter.drawLine(QtCore.QPointF(c-2.6,c-2.6),QtCore.QPointF(c+2.6,c+2.6));painter.drawLine(QtCore.QPointF(c-2.6,c+2.6),QtCore.QPointF(c+2.6,c-2.6))
            elif self.kind=='minimize':painter.drawLine(QtCore.QPointF(c-3,c),QtCore.QPointF(c+3,c))
            else:painter.drawLine(QtCore.QPointF(c-3,c),QtCore.QPointF(c+3,c));painter.drawLine(QtCore.QPointF(c,c-3),QtCore.QPointF(c,c+3))
        painter.end()

class TrafficLights(QtWidgets.QWidget):
    def __init__(self,window):
        super().__init__();self.hovered=False;self.setStyleSheet('background:transparent')
        box=QtWidgets.QHBoxLayout(self);box.setContentsMargins(10,0,0,0);box.setSpacing(6);box.setAlignment(Qt.AlignVCenter);self.lights={}
        for kind,action in (('maximize',window.toggle_maximized),('minimize',window.showMinimized),('close',window.close)): # Reversed: close sits at the far right.
            light=TrafficLight(kind,self);light.clicked.connect(action);box.addWidget(light);self.lights[kind]=light
    def enterEvent(self,event):self.hovered=True;self.update_lights()
    def leaveEvent(self,event):self.hovered=False;self.update_lights()
    def update_lights(self):
        for light in self.lights.values():light.update()

class TitleBar(QtWidgets.QWidget):
    """The app's own top bar replacing the Windows title bar: drag to move, double-click to maximize."""
    def __init__(self,window):super().__init__();self.window_=window;self.setStyleSheet('background:transparent')
    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton and self.window_.windowHandle():self.window_.windowHandle().startSystemMove()
    def mouseDoubleClickEvent(self,event):
        if event.button()==Qt.LeftButton:self.window_.toggle_maximized()

class BackdropGrabber(QtCore.QObject):
    """Background thread that copies the screen behind the iOS window as often as the monitor refreshes (GDI's screen
    copy alone is ~6.5 ms, so ~150 fps at most), shrinks it to a quarter, and hands the newest frame to the UI thread. Unchanged
    frames are dropped, and frames the UI hasn't picked up yet are replaced rather than queued."""
    frame=QtCore.Signal()
    def __init__(self,hwnd):
        super().__init__();self.hwnd=hwnd;self.interval=1/60;self.latest=None;self.pending=False;self.key=None
        self.lock=threading.Lock();self.stop_event=threading.Event()
        self.thread=threading.Thread(target=self.run,name='backdrop',daemon=True);self.thread.start()
    def stop(self):self.stop_event.set()
    def take(self):
        with self.lock:image,self.latest,self.pending=self.latest,None,False
        return image
    def run(self):
        u,g=ctypes.windll.user32,ctypes.windll.gdi32
        u.GetDC.restype=g.CreateCompatibleDC.restype=g.CreateCompatibleBitmap.restype=g.SelectObject.restype=ctypes.c_void_p
        class Header(ctypes.Structure):_fields_=[('size',ctypes.c_uint32),('width',ctypes.c_int32),('height',ctypes.c_int32),('planes',ctypes.c_uint16),('bits',ctypes.c_uint16),
                                                 ('compression',ctypes.c_uint32),('image_size',ctypes.c_uint32),('xppm',ctypes.c_int32),('yppm',ctypes.c_int32),('used',ctypes.c_uint32),('important',ctypes.c_uint32)]
        hwnd=ctypes.c_void_p(self.hwnd);rect=wintypes.RECT();V=ctypes.c_void_p;size=None;screen=memory=bitmap=old=None
        def release():
            if memory:g.SelectObject(V(memory),V(old));g.DeleteObject(V(bitmap));g.DeleteDC(V(memory))
            if screen:u.ReleaseDC(None,V(screen))
        try:
            while not self.stop_event.is_set():
                start=time.perf_counter()
                if u.IsIconic(hwnd) or not u.IsWindowVisible(hwnd) or not u.GetWindowRect(hwnd,ctypes.byref(rect)):self.stop_event.wait(0.1);continue
                width,height=rect.right-rect.left,rect.bottom-rect.top;full=(width,height)
                if width>0 and height>0:
                    if full!=size: # Reuse the DCs and bitmap until the window size changes.
                        release();size=full;screen=u.GetDC(None);memory=g.CreateCompatibleDC(V(screen));bitmap=g.CreateCompatibleBitmap(V(screen),width,height)
                        old=g.SelectObject(V(memory),V(bitmap))
                        header=Header(ctypes.sizeof(Header),width,-height,1,32,0,0,0,0,0,0);pixels=ctypes.create_string_buffer(width*height*4)
                    # Full-resolution copy of the screen behind (our window is excluded from capture), smooth-scaled below.
                    g.BitBlt(V(memory),0,0,width,height,V(screen),rect.left,rect.top,0x00CC0020)
                    if g.GetDIBits(V(memory),V(bitmap),0,height,pixels,ctypes.byref(header),0):
                        shot=QtGui.QImage(pixels,width,height,width*4,QtGui.QImage.Format_RGB32)
                        small=shot.scaled(max(1,width//4),max(1,height//4),Qt.IgnoreAspectRatio,Qt.SmoothTransformation) # A copy, so pixels can be reused.
                        key=bytes(small.scaled(max(1,width//24),max(1,height//24)).constBits())
                        if key!=self.key:
                            self.key=key
                            with self.lock:self.latest=small;send=not self.pending;self.pending=True
                            if send:self.frame.emit()
                self.stop_event.wait(max(0.001,self.interval-(time.perf_counter()-start)))
        finally:release()

def gaussian_blur(image,radius):
    """A real Gaussian blur of a QImage (via QGraphicsBlurEffect), as a QPixmap. Edges are padded so they don't darken."""
    pad=radius*2;source=QtGui.QImage(image.width()+pad*2,image.height()+pad*2,QtGui.QImage.Format_ARGB32_Premultiplied)
    painter=QtGui.QPainter(source);painter.drawImage(QtCore.QRectF(source.rect()),image) # Stretched edges stand in for what's past them.
    painter.drawImage(pad,pad,image);painter.end()
    scene=QtWidgets.QGraphicsScene();item=scene.addPixmap(QtGui.QPixmap.fromImage(source))
    effect=QtWidgets.QGraphicsBlurEffect();effect.setBlurRadius(radius);effect.setBlurHints(QtWidgets.QGraphicsBlurEffect.QualityHint);item.setGraphicsEffect(effect)
    result=QtGui.QImage(image.size(),QtGui.QImage.Format_ARGB32_Premultiplied);result.fill(0)
    painter=QtGui.QPainter(result);scene.render(painter,QtCore.QRectF(result.rect()),QtCore.QRectF(pad,pad,image.width(),image.height()));painter.end()
    return QtGui.QPixmap.fromImage(result)

class WindowFrame(QtWidgets.QFrame):
    """Body of the frameless window: the 1px themed border, and for iOS the see-through glass backdrop."""
    def __init__(self):super().__init__();self.setObjectName('window')
    def paintEvent(self,event):
        window=self.window();theme=getattr(getattr(window,'core',None),'theme',{})
        if theme.get('style')=='glass':
            painter=QtGui.QPainter(self);painter.setRenderHint(QtGui.QPainter.Antialiasing);area=QtCore.QRectF(self.rect())
            outline=QtGui.QPainterPath();outline.addRect(area) if window.isMaximized() else outline.addRoundedRect(area,GLASS_RADIUS,GLASS_RADIUS);painter.setClipPath(outline)
            backdrop=getattr(window,'backdrop',None)
            if getattr(window,'glass_active',False):pass # Windows' blur shows through the transparent window.
            elif backdrop is not None:painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform);painter.drawPixmap(area,backdrop,QtCore.QRectF(backdrop.rect())) # Our own blurred view of what's behind.
            else:painter.fillRect(area,QtGui.QColor(20,24,34,235))
            tint=max(0,min(60,theme.get('glass',10)))/100;painter.fillRect(area,QtGui.QColor(8,10,16,int(255*tint)))
            sheen=QtGui.QLinearGradient(0,0,0,area.height()*0.4);sheen.setColorAt(0,QtGui.QColor(255,255,255,34));sheen.setColorAt(1,QtGui.QColor(255,255,255,0))
            painter.fillRect(area,sheen);painter.end()
        super().paintEvent(event)

class Window(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__();self.poster=Poster();self.buttons={};self.slots=[];self.glow_targets=[];self.closing=False;self.built=False
        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(Qt.Window|Qt.FramelessWindowHint) # The app draws its own themed top bar.
        self.setAttribute(Qt.WA_TranslucentBackground) # Lets the glass theme show the system backdrop; terminal paints opaque.
        self.core=Core(self);self.build();self.built=True
        # One fixed size that fits everything (no edge resizing); smaller screens get 92% of the work area. Green maximizes.
        screen=QtGui.QGuiApplication.primaryScreen().availableGeometry()
        self.resize(min(1240,int(screen.width()*0.92)),min(860,int(screen.height()*0.92)));self.move(screen.center()-self.rect().center())
        self.save_timer=QtCore.QTimer(self);self.save_timer.setSingleShot(True);self.save_timer.timeout.connect(self.core.save)
        self.timer=QtCore.QTimer(self);self.timer.timeout.connect(self.core.tick);self.timer.start(20)
        self.apply_theme();self.changed('catalog','mapping','sets','hotkeys','movement','target','targets','snapshot','status','live','busy','replay_note','folders')
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
    def show_game_tabs(self):
        """A game's tab shows only once the library has clips from that game."""
        present={x['game'] for x in self.core.catalog}
        for game in GAMES:self.tabs.setTabVisible(self.tabs.indexOf(self.libraries[game]),game in present)
    def render_build(self):
        for game,found,count,ticked in self.core.build_choices():
            box=self.build_boxes[game];box.blockSignals(True);box.setChecked(ticked);box.setEnabled(found and not self.core.building);box.blockSignals(False)
            name=SHORT[game];box.setText(f"{name} ({count:,})" if count else name if found else f'{name} (not found)')
            box.setToolTip('Already in your library: tick to rebuild it.' if count and found else 'Folder not found: set it under Game folders.' if not found else 'Not in your library yet.')
    def render_movement(self):
        custom=[key for key in MOVEMENT_LIMITS if self.core.movement[key]!=100]
        for key,(slider,value) in self.movement_sliders.items():
            slider.blockSignals(True);slider.setValue(self.core.movement[key]);slider.blockSignals(False);value.setText(f'{self.core.movement[key]}%')
        self.movement_button.setText('Movement •' if custom else 'Movement') # A dot shows when anything isn't at 100%.
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
        central=WindowFrame();self.setCentralWidget(central);central.setFocusPolicy(Qt.StrongFocus);self.setFocusPolicy(Qt.StrongFocus)
        layout=QtWidgets.QVBoxLayout(central);layout.setContentsMargins(16,12,16,10);layout.setSpacing(10)
        title=self.glow(label(APP_NAME,name='title'));self.title_label=title
        self.bo2_chip=label('BO2 ○ waiting',name='chip');self.import_chip=label('imports ○ off',name='chip')
        self.launch=self.action_button('launch_apply','▶ Launch BO2 && apply',self.core.start);self.stopbutton=self.action_button('stop_restore','■ Stop && restore',self.core.stop)
        self.lights=TrafficLights(self);self.titlebar=TitleBar(self)
        self.subtitle=label('COD4 / MW2 / MW3 / BO2 SP / BO2 ZM → BO2 Redacted',name='muted')
        self.titlebar.setLayout(row(title,self.subtitle,self.bo2_chip,self.import_chip,self.launch,self.stopbutton,self.lights,stretch_at=2))
        self.titlebar.layout().setAlignment(self.lights,Qt.AlignVCenter);layout.addWidget(self.titlebar)
        self.card=QtWidgets.QFrame();self.card.setObjectName('card');self.glow(self.card);card=QtWidgets.QVBoxLayout(self.card);card.setContentsMargins(14,10,14,10);card.setSpacing(6)
        self.follow_label=label();self.detected=label();self.replay_note=label()
        heading=label('LIVE TARGET');heading.setStyleSheet('font-weight:bold;letter-spacing:1px')
        card.addLayout(row(heading,self.follow_label,stretch_at=1));card.addWidget(self.detected);card.addWidget(self.replay_note);card.addWidget(rule())
        self.apply_button=self.plain_button('',self.core.request_replay);self.apply_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.apply_button.customContextMenuRequested.connect(lambda pos:self.hotkey_menu(self.apply_button,'apply_anim'))
        self.lock=QtWidgets.QCheckBox('Lock target');self.lock.setFocusPolicy(Qt.NoFocus);self.lock.toggled.connect(self.core.set_locked)
        self.freelook_button=QtWidgets.QCheckBox('Freelook');self.freelook_button.setFocusPolicy(Qt.NoFocus) # A checkbox like Lock target.
        self.freelook_button.toggled.connect(lambda checked:self.core.set_hotkey_options(freelook_enabled=checked))
        self.freelook_button.setContextMenuPolicy(Qt.CustomContextMenu);self.freelook_button.customContextMenuRequested.connect(lambda pos:self.hotkey_menu(self.freelook_button,'freelook'))
        self.freelook_button.setToolTip('Hold the key in BO2 to orbit the third-person camera. Tick to turn on or off; right-click to change the key.')
        self.movement_button=self.plain_button('Movement',lambda checked:self.movement_panel.setVisible(checked),checkable=True)
        self.movement_button.setToolTip('Movement speed in matches you host. Not timescale: animations play at normal speed.')
        card.addLayout(row(self.apply_button,self.lock,self.freelook_button,self.movement_button,stretch_at=4,spacing=10))
        self.movement_panel=QtWidgets.QWidget();self.movement_panel.setObjectName('cardrow');panel=QtWidgets.QHBoxLayout(self.movement_panel);panel.setContentsMargins(0,4,0,0);panel.setSpacing(10)
        self.movement_sliders={}
        for key,name in (('speed','Speed'),):
            low,high=MOVEMENT_LIMITS[key];slider=QtWidgets.QSlider(Qt.Horizontal);slider.setRange(low,high);slider.setSingleStep(5);slider.setPageStep(25)
            slider.setFocusPolicy(Qt.NoFocus);slider.setMinimumWidth(170);value=label();value.setMinimumWidth(44)
            slider.valueChanged.connect(lambda v,key=key:(self.core.set_movement(save=False,**{key:v}),self.save_timer.start(400)))
            slider.setToolTip('Walk, run and sprint speed (g_speed). 100% is the game default.')
            self.movement_sliders[key]=(slider,value);panel.addWidget(label(name));panel.addWidget(slider);panel.addWidget(value)
        panel.addWidget(self.plain_button('Reset',self.core.reset_movement));panel.addStretch(1)
        self.movement_panel.hide();card.addWidget(self.movement_panel);layout.addWidget(self.card)
        self.tabs=QtWidgets.QTabWidget();self.tabs.setDocumentMode(True);layout.addWidget(self.tabs,1)
        self.libraries={}
        for game in ('Favorites',*GAMES):
            tab=LibraryTab(self,game);self.libraries[game]=tab;self.tabs.addTab(tab,'★ Favorites' if game=='Favorites' else SHORT[game])
        self.tabs.addTab(self.build_replacements(),'Replacements');self.tabs.addTab(self.build_debug(),'Debug');self.tabs.addTab(self.build_settings(),'Settings');self.tabs.addTab(self.build_about(),'About')
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
        layout.addLayout(row(remove,clear,separator,save,self.set_box,load,delete,stretch_at=7))
        share=self.action_button('share_set','Copy share code',lambda:self.copy_code(self.core.share_set_code(self.set_box.currentText())))
        paste=self.action_button('paste_code','Paste share code',self.paste_code)
        layout.addLayout(row(share,paste,label('Shares the set picked above, or your current replacements. Paste a code from a friend to save it as a set.',name='muted'),stretch_at=3));return page
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
        copy=self.plain_button('Copy log for support',self.copy_support_log);folder=self.plain_button('Open log folder',lambda:os.startfile(str(self.core.logfile.folder)))
        copy.setToolTip('Copies your setup and the recent log, with your Windows username hidden, to paste when asking for help.')
        layout.addLayout(row(label('LOG',name='section'),label('Also saved to logs/bo2sp.log (the previous session is bo2sp.old.log).',name='muted'),copy,folder,stretch_at=2))
        self.log=QtWidgets.QPlainTextEdit();self.log.setReadOnly(True);layout.addWidget(self.log,1);return page
    def copy_support_log(self):
        QtGui.QGuiApplication.clipboard().setText(self.core.support_text());self.core.set_status('Support log copied. Paste it wherever you’re asking for help.')
    def build_about(self):
        scroll=QtWidgets.QScrollArea();scroll.setWidgetResizable(True);page=QtWidgets.QWidget();scroll.setWidget(page)
        layout=QtWidgets.QVBoxLayout(page);layout.setContentsMargins(0,6,12,0);layout.setSpacing(8)
        def text(words,name=None):
            widget=label(words,name=name);widget.setWordWrap(True);layout.addWidget(widget);return widget
        layout.addWidget(label('BO2SP',name='title'))
        text('Animations from other Call of Duty games in Black Ops II Redacted multiplayer, applied live while you play.',name='muted')
        layout.addWidget(label('WHAT IT DOES',name='section'))
        text('Pick a clip from COD4, MW2, MW3 (single-player actors), BO2 SP or BO2 ZM, choose the BO2 body animation it replaces, '
             'and your character plays it straight away. Live target follows the animation you’re playing right now, Apply anim restarts it '
             'on demand, and Freelook orbits the third-person camera. Built for staging scenes in custom matches and filming them in Theater '
             'with t6mvm.')
        layout.addWidget(label('HOW IT WORKS',name='section'))
        text('Clips are extracted from your own game installs and converted to BO2’s format, then swapped into the running game’s memory. '
             'Nothing on disk changes: Stop & restore, closing the tool, or restarting BO2 brings the original animations back. '
             'A replacement applies to every character using that slot, and shows in Theater while the tool is open.')
        layout.addWidget(label('CREDITS',name='section'))
        text('Made by Yoroji.')
        text('OpenAssetTools (asset extraction), Greyhound and T6SDK (format and engine references).',name='muted')
        layout.addLayout(row(self.plain_button('Yoroji on YouTube',lambda:QtGui.QDesktopServices.openUrl(QtCore.QUrl(CHANNEL_URL))),stretch_at=1))
        layout.addWidget(label('LICENSE',name='section'))
        text('Free software under the GNU GPL-3.0. Animation data comes from games you own and stays on your machine.',name='muted')
        layout.addStretch(1);return scroll
    def build_settings(self):
        scroll=QtWidgets.QScrollArea();scroll.setWidgetResizable(True);page=QtWidgets.QWidget();scroll.setWidget(page)
        layout=QtWidgets.QVBoxLayout(page);layout.setContentsMargins(0,6,12,0);layout.setSpacing(8)
        layout.addWidget(label('APPEARANCE',name='section'))
        self.style_buttons={key:self.plain_button(name,lambda checked=False,key=key:self.core.set_theme(style=key),checkable=True) for key,name in (('terminal','Terminal'),('glass','iOS'),('android','Android'))}
        self.glass_slider=QtWidgets.QSlider(Qt.Horizontal);self.glass_slider.setRange(0,60);self.glass_slider.setFocusPolicy(Qt.NoFocus);self.glass_slider.setMinimumWidth(220)
        self.glass_slider.valueChanged.connect(lambda v:(self.core.set_theme(save=False,glass=v),self.save_timer.start(400)));self.glass_value=label('',name='muted')
        self.glass_label=label('Tint',name='muted')
        self.glass_hint=label('iOS blurs the screen behind the window itself, so screenshots and recordings leave this window out while iOS is on.',name='muted');self.glass_hint.setWordWrap(True)
        layout.addLayout(row(label('Style',name='muted'),*self.style_buttons.values(),self.glass_label,self.glass_slider,self.glass_value,stretch_at=6))
        layout.addWidget(self.glass_hint)
        layout.addLayout(row(self.plain_button('Copy appearance code',lambda:self.copy_code(self.core.share_theme_code())),self.plain_button('Paste share code',self.paste_code),label('Style, accent, glow and glass tint as text you can send.',name='muted'),stretch_at=3))
        layout.addWidget(label('ACCENT COLOR',name='section'))
        grid=QtWidgets.QGridLayout();grid.setHorizontalSpacing(10);self.sliders={};self.slider_values={}
        for i,(key,name,low,high) in enumerate((('h','Hue',0,360),('s','Saturation',0,100),('l','Lightness',20,85))):
            slider=QtWidgets.QSlider(Qt.Horizontal);slider.setRange(low,high);slider.setFocusPolicy(Qt.NoFocus);value=label();value.setMinimumWidth(48)
            slider.valueChanged.connect(lambda v,key=key:(self.core.set_theme(save=False,**{key:v}),self.save_timer.start(400)));self.sliders[key]=slider;self.slider_values[key]=value
            grid.addWidget(label(name,name='muted'),i,0);grid.addWidget(slider,i,1);grid.addWidget(value,i,2)
        layout.addLayout(grid)
        presets=[self.plain_button(name,lambda checked=False,v=values:self.core.set_theme(h=v[0],s=v[1],l=v[2])) for name,values in THEME_PRESETS.items()]
        self.glow_box=QtWidgets.QCheckBox('Text glow');self.glow_box.setFocusPolicy(Qt.NoFocus);self.glow_box.toggled.connect(lambda on:self.core.set_theme(glow=on))
        reset=self.plain_button('Reset',lambda:self.core.set_theme(**{key:DEFAULT_THEME[key] for key in ('h','s','l','glow')}))
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
        for key,name in (('bo2','BO2 Redacted'),('cod4','COD4'),('mw2','MW2'),('mw3','MW3')):
            edit=QtWidgets.QLineEdit();browse=self.plain_button('Browse',lambda checked=False,e=edit:self.browse(e));self.folder_edits[key]=edit
            name_label=label(name,name='muted');name_label.setMinimumWidth(110);layout.addLayout(row(name_label,edit,browse))
        layout.addLayout(row(self.plain_button('Save folders',self.save_folders),self.plain_button('Detect game folders',self.detect_folders),label('Finds a running BO2, Steam libraries and common install folders.',name='muted'),stretch_at=3))
        layout.addWidget(rule());layout.addWidget(label('LIBRARY AND GAME',name='section'))
        self.basics=self.action_button('load_basics','Load COD4 basics',self.core.load_basics)
        importer=self.action_button('import_file','Import animation file…',self.core.import_clip)
        self.reindex_button=self.action_button('refresh_libraries','Build libraries',self.core.reindex)
        camera=self.action_button('enable_camera','Install Third Person Camera',self.core.enable_camera)
        camera.setToolTip('Adds a small script to BO2 so you start custom matches you host in third person. In game, hold Use (F) and press\n'
                          'action slot 1 (1) to switch between third and first person. Click again to update it; it replaces the old Yoroji camera script.')
        layout.addLayout(row(self.basics,importer,camera,stretch_at=3))
        self.build_boxes={}
        for game in GAMES:
            box=QtWidgets.QCheckBox(game);box.setFocusPolicy(Qt.NoFocus);box.toggled.connect(lambda on,game=game:self.core.pick_build(game,on));self.build_boxes[game]=box
        layout.addLayout(row(self.reindex_button,*self.build_boxes.values(),stretch_at=len(GAMES)+1,spacing=14))
        build_help=label('Ticked games are extracted when you click Build libraries. Games already in your library start unticked, so they’re skipped; tick one to rebuild it. Games whose folder wasn’t found can’t be ticked. Click again to cancel; building again resumes.',name='muted');build_help.setWordWrap(True);layout.addWidget(build_help)
        layout.addWidget(label('Closing BO2SP restores BO2’s original animations.',name='muted'));layout.addStretch(1);return scroll

    # Actions needing widget state
    def use_highlighted(self):
        selected=self.layers.selectedItems()
        if selected and self.core.lock_highlighted(self.layers.item(selected[0].row(),0).text()):self.tabs.setCurrentIndex(0)
    def browse(self,edit):
        path=QtWidgets.QFileDialog.getExistingDirectory(self,'Choose folder',edit.text())
        if path:edit.setText(str(Path(path)))
    def detect_folders(self):
        found=self.core.detect_folders();self.core.set_status('Game folders: '+', '.join(f"{name} {'found' if found[key] else 'not found'}" for key,name in (('bo2','BO2'),('cod4','COD4'),('mw2','MW2'),('mw3','MW3'))))
    def copy_code(self,code):
        if code:QtWidgets.QApplication.clipboard().setText(code)
    def paste_code(self):
        text=QtWidgets.QApplication.clipboard().text()
        if not text.strip():self.core.set_status('Copy a BO2SP share code first, then click Paste share code.');return
        result=self.core.import_share_code(text)
        if result and result[0]=='set':self.set_box.setCurrentText(result[1])
    def save_folders(self):self.core.set_folders(self.folder_edits['cod4'].text(),self.folder_edits['mw2'].text(),self.folder_edits['bo2'].text(),self.folder_edits['mw3'].text());self.core.set_status('Game folders saved.')

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
                self.render_build();self.show_game_tabs()
            elif field=='favorites':
                for game,tab in self.libraries.items():
                    if game=='Favorites':tab.render()
                    else:tab.model.refresh_stars()
            elif field=='mapping':self.render_mapping();self.render_card()
            elif field=='sets':
                current=self.set_box.currentText();self.set_box.clear();self.set_box.addItems(sorted(core.saved_sets));self.set_box.setCurrentText(current if current in core.saved_sets else '')
            elif field=='hotkeys':self.render_hotkeys()
            elif field=='movement':self.render_movement()
            elif field in ('target','targets'):self.render_slots();self.render_card()
            elif field=='replay_note':self.replay_note.setText(core.replay_note)
            elif field=='snapshot':self.render_snapshot()
            elif field=='busy':
                idle=core.idle();self.launch.setEnabled(idle);self.basics.setEnabled(idle);self.reindex_button.setEnabled(idle or core.building)
                self.reindex_button.setProperty('base','Cancel build' if core.building else 'Build libraries');self.render_hotkeys();self.render_build();self.changed('live')
            elif field=='build':self.render_build()
            elif field=='folders':
                for key,edit in self.folder_edits.items():edit.setText(getattr(core,key))
                self.render_build()
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
        self.freelook_button.setText(f"Freelook ({core.freelook_name if core.freelook_vk else 'no key'})")
        self.apply_key.setText(core.apply_name);self.freelook_key.setText(core.freelook_name)
        for box,value in ((self.apply_enabled,core.replay_enabled),(self.freelook_enabled,core.freelook_enabled)):box.blockSignals(True);box.setChecked(value);box.blockSignals(False)
        self.speed.blockSignals(True);self.speed.setValue(core.freelook_speed);self.speed.blockSignals(False)
        hints=[]
        if core.apply_vk and core.replay_enabled:hints.append(f'[{core.apply_name}] Apply')
        if core.freelook_vk and core.freelook_enabled:hints.append(f'[{core.freelook_name}] Freelook')
        self.hints.setText('   '.join(hints+['[Right-click] Set hotkey']))
    def apply_theme(self):
        theme=self.core.theme;glass=theme.get('style')=='glass'
        # Windows' blur ignores the window's shape (it's cut at its own ~8px corners, which showed as a second corner
        # around the 22px one), so iOS always paints its own blurred snapshot of the screen behind, clipped to 22px.
        if self.isVisible():self.apply_backdrop(False)
        self.glass_active=False;self.set_self_blur(glass and self.isVisible())
        android=theme.get('style')=='android';font=QtGui.QFont(self.font());font.setStyleStrategy(QtGui.QFont.PreferDefault);self.setFont(font)
        self.pixel_effect=PixelEffect(2) if android else None # Held here: PySide would otherwise free it at once.
        self.centralWidget().setGraphicsEffect(self.pixel_effect)
        if android:self.colors=android_palette(theme);self.setStyleSheet(android_stylesheet(self.colors));self.watermark.tint(self.colors['acc'])
        elif glass:
            self.colors=glass_palette(theme);self.setStyleSheet(glass_stylesheet(self.colors));self.watermark.tint(QtGui.QColor(255,255,255))
        else:self.colors=palette(theme);self.setStyleSheet(stylesheet(self.colors));self.watermark.tint(self.colors['acc'])
        self.title_label.setText('BO2SP' if glass else 'bo2sp.apk' if android else APP_NAME)
        self.lights.update_lights();self.subtitle.setVisible(not android) # The bigger pixel font needs the room.
        for key,button in self.style_buttons.items():button.blockSignals(True);button.setChecked(theme.get('style','terminal')==key);button.blockSignals(False)
        for widget in (self.glass_label,self.glass_slider,self.glass_value):widget.setVisible(glass)
        self.glass_hint.setVisible(glass and self.self_blur)
        tint=max(0,min(60,int(self.core.theme.get('glass',10))))
        self.update_shape()
        self.glass_slider.blockSignals(True);self.glass_slider.setValue(tint);self.glass_slider.blockSignals(False);self.glass_value.setText(f'{tint}%')
        self.centralWidget().update() # Repaint the backdrop for the new hue.
        self.glow_box.setEnabled(not glass and not android)
        for key,slider in self.sliders.items():
            slider.blockSignals(True);slider.setValue(int(theme[key]));slider.blockSignals(False);self.slider_values[key].setText(f"{int(theme[key])}{'°' if key=='h' else '%'}")
        self.glow_box.blockSignals(True);self.glow_box.setChecked(bool(theme['glow']));self.glow_box.blockSignals(False)
        for widget in self.glow_targets:
            if theme['glow'] and not glass and not android:
                effect=QtWidgets.QGraphicsDropShadowEffect(widget);effect.setOffset(0,0);effect.setBlurRadius(18);glow=QtGui.QColor(self.colors['acc']);glow.setAlpha(170);effect.setColor(glow);widget.setGraphicsEffect(effect)
            else:widget.setGraphicsEffect(None)
        self.render_snapshot()

    def update_shape(self):
        """iOS: cut the window to its rounded outline so the blur behind doesn't show past the corners."""
        if self.core.theme.get('style')=='glass' and not self.isMaximized():
            outline=QtGui.QPainterPath();outline.addRoundedRect(QtCore.QRectF(self.rect()),GLASS_RADIUS,GLASS_RADIUS)
            self.setMask(QtGui.QRegion(outline.toFillPolygon().toPolygon()))
        else:self.clearMask()
    def resizeEvent(self,event):super().resizeEvent(event);self.built and self.update_shape()
    def moveEvent(self,event):super().moveEvent(event);getattr(self,'grabber',None) and self.set_grab_rate() # It may now be on another monitor.
    def set_self_blur(self,on):
        """iOS snapshots and blurs what's behind the window itself, at the monitor's refresh rate (BackdropGrabber).
        The window is excluded from screen capture meanwhile, or it would see itself."""
        if getattr(self,'self_blur',None)==on:return
        self.self_blur=on
        if sys.platform=='win32' and self.isVisible():
            ctypes.windll.user32.SetWindowDisplayAffinity(ctypes.c_void_p(int(self.winId())),0x11 if on else 0) # WDA_EXCLUDEFROMCAPTURE / WDA_NONE
        if getattr(self,'grabber',None):self.grabber.stop();self.grabber=None
        if not on:self.backdrop=None;return
        if sys.platform=='win32':self.grabber=BackdropGrabber(int(self.winId()));self.grabber.frame.connect(self.show_backdrop);self.set_grab_rate()
    def set_grab_rate(self):
        screen=self.screen() or QtGui.QGuiApplication.primaryScreen();self.grabber.interval=1/max(30.0,min(240.0,screen.refreshRate() or 60.0))
    def show_backdrop(self):
        grabber=getattr(self,'grabber',None);image=grabber.take() if grabber else None
        if image is None or not self.self_blur:return
        self.backdrop=gaussian_blur(image,10);self.centralWidget().update()
    def apply_backdrop(self,glass):
        """Windows blur behind the (layered, translucent) window for the iOS style; returns whether it's on.
        Qt makes translucent frameless windows layered, which the documented DWM system backdrop ignores, so this
        uses the window-composition accent, which does work on layered windows. Plain blur-behind (3) with no tint rather than
        acrylic (4): acrylic adds its own dark luminosity layer, and it ignores the window's rounded mask, leaving dark corners."""
        if sys.platform!='win32':return False
        glass=glass and transparency_enabled() # With Windows transparency effects off, the blur is drawn solid.
        try:
            hwnd=ctypes.c_void_p(int(self.winId()))
            class Accent(ctypes.Structure):_fields_=[('state',ctypes.c_int),('flags',ctypes.c_int),('color',ctypes.c_uint),('animation',ctypes.c_int)]
            class Data(ctypes.Structure):_fields_=[('attribute',ctypes.c_int),('data',ctypes.c_void_p),('size',ctypes.c_size_t)]
            accent=Accent(3 if glass else 0,0,0,0) # 3 = blur behind, untinted; the Tint slider paints the darkening.
            data=Data(19,ctypes.cast(ctypes.byref(accent),ctypes.c_void_p),ctypes.sizeof(accent)) # 19 = WCA_ACCENT_POLICY
            ok=bool(ctypes.windll.user32.SetWindowCompositionAttribute(hwnd,ctypes.byref(data)))
            corner=ctypes.c_int(2 if glass else 1);ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd,33,ctypes.byref(corner),4) # Rounded corners for glass.
            return ok and glass
        except (OSError,AttributeError):return False
    def toggle_maximized(self):self.showNormal() if self.isMaximized() else self.showMaximized()
    def showEvent(self,event):
        super().showEvent(event)
        if sys.platform=='win32' and not getattr(self,'styled',False): # Frameless windows still minimize and maximize from the taskbar.
            self.styled=True;hwnd=int(self.winId());user=ctypes.windll.user32;style=user.GetWindowLongW(hwnd,-16)
            user.SetWindowLongW(hwnd,-16,style|0x00020000|0x00010000|0x00080000) # WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU, no caption.
            self.set_native_icons(hwnd)
        self.apply_theme() # The backdrop needs the native window, which exists only once shown.
    def set_native_icons(self,hwnd):
        """Put the logo on the window and its window class too; frameless windows can show the class icon on the taskbar."""
        user=ctypes.windll.user32;user.LoadImageW.restype=ctypes.c_void_p;user.LoadImageW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint,ctypes.c_int,ctypes.c_int,ctypes.c_uint]
        user.SetClassLongPtrW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p];user.SendMessageW.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_void_p]
        path=str(ASSETS/'app.ico')
        big=user.LoadImageW(None,path,1,user.GetSystemMetrics(11),user.GetSystemMetrics(12),0x10) # IMAGE_ICON, SM_CXICON/SM_CYICON, LR_LOADFROMFILE
        small=user.LoadImageW(None,path,1,user.GetSystemMetrics(49),user.GetSystemMetrics(50),0x10) # SM_CXSMICON/SM_CYSMICON
        if big:user.SetClassLongPtrW(hwnd,-14,big);user.SendMessageW(hwnd,0x80,1,big) # GCLP_HICON, WM_SETICON ICON_BIG
        if small:user.SetClassLongPtrW(hwnd,-34,small);user.SendMessageW(hwnd,0x80,0,small) # GCLP_HICONSM, ICON_SMALL
    def closeEvent(self,event):
        if getattr(self,'grabber',None):self.grabber.stop()
        if not self.closing:self.closing=True;self.core.close();self.timer.stop();self.status.setText('Restoring original animations and closing…')
        if self.core.finished():event.accept()
        else:event.ignore();QtCore.QTimer.singleShot(100,self.close)

def main():
    k.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR];k.CreateMutexW.restype=wintypes.HANDLE
    handle=k.CreateMutexW(None,False,r'Local\CoD4_BO2_Redacted_Animation_Importer')
    if not handle:raise OSError(ctypes.get_last_error(),'Cannot initialize importer')
    duplicate=ctypes.get_last_error()==183
    try:
        if sys.platform=='win32' and not getattr(sys,'frozen',False): # From source, group under our icon instead of python.exe's.
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Yoroji.BO2SP')
        install_crash_hooks()
        app=QtWidgets.QApplication(sys.argv);app.setApplicationName(APP_NAME);app.setWindowIcon(QtGui.QIcon(str(ASSETS/'app.ico')))
        if duplicate:QtWidgets.QMessageBox.information(None,'Already open','BO2SP is already running. Use the existing window.');return
        window=Window();window.show();app.exec()
    finally:k.CloseHandle(handle)

if __name__=='__main__':main()
