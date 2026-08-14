# Requires: pip install python-vlc
import json, math, random, ctypes
from pathlib import Path
import numpy as np, pygame, vlc

ROOT = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
LOGS = ROOT / "logs"
SETTINGS_FILE = ROOT / "system_config.json"
W, H = 640, 360
BLUE, WHITE, BLACK, RED, GREEN = (8,34,126), (250,250,245), (0,0,0), (190,10,10), (54,230,112)

def beep(freq=760, seconds=.06):
    count = int(44100 * seconds)
    sound = (np.sign(np.sin(2 * math.pi * freq * np.arange(count) / 44100)) * 5800).astype(np.int16)
    return pygame.sndarray.make_sound(np.column_stack((sound, sound)))

class System:
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 2, 512); pygame.init()
        self.fullscreen = False
        self.win = pygame.display.set_mode((1280,720), pygame.RESIZABLE)
        pygame.display.set_caption("STOP VHS OPERATING SYSTEM")
        self.c = pygame.Surface((W,H)); self.clock = pygame.time.Clock()
        self.big = pygame.font.SysFont("Courier New",26,bold=True)
        self.menu = pygame.font.SysFont("Courier New",20,bold=True)
        self.small = pygame.font.SysFont("Courier New",18,bold=True)
        self.tick, self.warn = beep(), beep(180,.16)
        self.state, self.started, self.running = "ready", pygame.time.get_ticks(), True
        self.home = ["LOGS", "FOLDER CONFIGURATION", "FILE SETTINGS", "SYSTEM SETTINGS"]
        self.folder = ["VERIFY LOGS FOLDER", "CREATE LOGS FOLDER", "RESCAN DIRECTORY", "RETURN"]
        self.actions = ["PLAY", "DELETE", "RETURN"]
        self.confirm = ["CANCEL", "DELETE FILE"]
        self.system = ["DISPLAY MODE", "SCANLINE LEVEL", "SIGNAL STABILITY", "RETURN"]
        self.hi = {"home":0,"folder":0,"settings":0,"system":0,"logs":0,"actions":0,"confirm":0,"missing":0}
        self.prebuffer, self.delete_enabled = True, False
        self.scanline_level, self.signal_unstable = 2, True
        self.logs, self.chosen = [], None
        self.message, self.back = "", "home"

        self.vlc_inst = vlc.Instance("--no-xlib", "--quiet")
        self.player = self.vlc_inst.media_player_new()
        self.videobuffer = (ctypes.c_ubyte * (W * H * 4))()

        @vlc.CallbackDecorators.VideoLockCb
        def lock_cb(opaque, planes):
            planes[0] = ctypes.cast(self.videobuffer, ctypes.c_void_p)
            
        @vlc.CallbackDecorators.VideoUnlockCb
        def unlock_cb(opaque, picture, planes):
            pass
            
        @vlc.CallbackDecorators.VideoDisplayCb
        def display_cb(opaque, picture):
            pass

        self._lock_cb, self._unlock_cb, self._display_cb = lock_cb, unlock_cb, display_cb
        vlc.libvlc_video_set_callbacks(self.player, self._lock_cb, self._unlock_cb, self._display_cb, None)
        vlc.libvlc_video_set_format(self.player, b"RGBA", W, H, W * 4)

        self.load_settings()
        self.apply_display_mode()

    def age(self): return (pygame.time.get_ticks()-self.started)/1000
    def go(self,state): self.state, self.started = state, pygame.time.get_ticks()

    def load_settings(self):
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            self.prebuffer = bool(data.get("prebuffer", self.prebuffer))
            self.delete_enabled = bool(data.get("delete_enabled", self.delete_enabled))
            self.fullscreen = bool(data.get("fullscreen", self.fullscreen))
            self.scanline_level = int(data.get("scanline_level", self.scanline_level))
            self.signal_unstable = bool(data.get("signal_unstable", self.signal_unstable))
        except (OSError, ValueError, TypeError):
            pass

    def save_settings(self):
        data = {"prebuffer": self.prebuffer, "delete_enabled": self.delete_enabled, "fullscreen": self.fullscreen, "scanline_level": self.scanline_level, "signal_unstable": self.signal_unstable}
        try: SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError: pass

    def apply_display_mode(self):
        if self.fullscreen: self.win = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
        else: self.win = pygame.display.set_mode((1280,720), pygame.RESIZABLE)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen; self.apply_display_mode(); self.save_settings()
    def files(self):
        return sorted([p for p in LOGS.iterdir() if p.is_file() and p.suffix.lower()==".mp4"], key=lambda p:p.name.lower()) if LOGS.exists() else []
    def text(self,s,f,x=None,y=None,center=None,color=WHITE):
        im=f.render(s,False,color); self.c.blit(im,im.get_rect(center=center) if center else im.get_rect(topleft=(x,y)))
    def base(self): self.c.fill(BLUE); self.text("STOP",self.big,14,10)
    def header(self,name): self.base(); self.text("=="+name+"==",self.big,center=(W//2,72))
    def choices(self,items,selected,top=130,font=None):
        for n,item in enumerate(items):
            y=top+n*38; self.text(item,font or self.menu,86,y)
            if n==selected: pygame.draw.rect(self.c,BLACK,(67,y-3,506,29),4,border_radius=2)
    def lines(self):
        shade=pygame.Surface((W,H),pygame.SRCALPHA)
        alpha = [0, 12, 23, 38][max(0, min(3, self.scanline_level))]
        for y in range(0,H,3): pygame.draw.line(shade,(0,0,0,alpha),(0,y),(W,y))
        self.c.blit(shade,(0,0))

    def signal_noise(self):
        if not self.signal_unstable: return
        generator = random.Random(pygame.time.get_ticks() // 110)
        overlay = pygame.Surface((W,H),pygame.SRCALPHA)
        for _ in range(8):
            y = generator.randrange(H)
            pygame.draw.line(overlay, (255,255,255,generator.randrange(5,18)), (0,y), (W,y))
        if generator.randrange(12) == 0:
            y = generator.randrange(35,H-15)
            pygame.draw.rect(overlay, (35,0,80,35), (0,y,W,generator.randrange(2,8)))
        self.c.blit(overlay,(0,0))

    def boot(self):
        self.c.fill(BLACK)
        t = self.age()
        self.text("CCTV CONTROL UNIT", self.small, 18, 16, color=(150, 220, 170))
        self.text("SYSTEM ROM 2.04", self.small, 18, 42, color=(150, 220, 170))
        self.text("CHECKING VIDEO BUS... OK", self.small, 18, 82, color=(150, 220, 170))
        self.text("CHECKING MEMORY... OK", self.small, 18, 106, color=(150, 220, 170))
        if t < 1:
            self.text("PLEASE WAIT.", self.menu, 18, 155)
        else:
            self.text("LOADING", self.menu, 18, 155)
            self.text("VIDEO OUTPUT READY", self.small, 18, 188, color=(150, 220, 170))
        if t >= 3:
            self.go("home")
    def ready(self):
        self.c.fill(BLACK)
        self.text("READY.", self.big, center=(W//2,152))
        self.text("PRESS ENTER TO INITIALIZE SYSTEM", self.small, center=(W//2,195), color=(180,190,240))
    def home_screen(self):
        self.header("SYSTEM MENU"); self.choices(self.home,self.hi["home"],135)
        self.text("UP / DOWN / ENTER",self.small,center=(W//2,316),color=(180,190,240))
    def loading(self):
        self.header("SELECT LOG"); t=self.age()
        if t<11:
            dots = [".", "..", "...", "..", ".", ""][int(t * 2) % 6]
            self.text("LOADING" + dots,self.big,center=(W//2,230))
        else:
            self.text("RETRIEVING",self.big,center=(W//2,213)); self.text("DIRECTORY",self.big,center=(W//2,240))
        if t>=15:
            self.logs=self.files(); self.hi["logs"]=0; self.go("missing" if not LOGS.exists() else "logs")
    def missing(self):
        self.header("SELECT LOG"); self.text("LOGS FOLDER NOT FOUND",self.menu,center=(W//2,155)); self.text("CREATE IT NOW?",self.menu,center=(W//2,185))
        self.choices(["CREATE LOGS FOLDER","RETURN"],self.hi["missing"],230,self.small)
    def log_list(self):
        self.header("SELECT LOG")
        if not self.logs:
            self.text("NO MP4 LOGS DETECTED",self.menu,center=(W//2,175)); self.text("PRESS ENTER TO RESCAN",self.small,center=(W//2,210)); return
        start=max(0,min(self.hi["logs"]-3,len(self.logs)-6))
        for row,p in enumerate(self.logs[start:start+6]):
            i=start+row; y=116+row*34; self.text((p.stem.upper()+".log")[:42],self.menu,52,y)
            if i==self.hi["logs"]: pygame.draw.rect(self.c,BLACK,(39,y-3,562,28),4,border_radius=2)
    def action_screen(self):
        self.header("LOG ACTION"); self.text((self.chosen.stem.upper()+".log")[:38],self.menu,center=(W//2,135)); self.choices(self.actions,self.hi["actions"],190)
    def folder_screen(self):
        self.header("FOLDER CONFIGURATION")
        present=LOGS.exists(); self.text("LOGS FOLDER: "+("PRESENT" if present else "MISSING"),self.small,center=(W//2,110),color=GREEN if present else RED)
        self.choices(self.folder,self.hi["folder"],145,self.small)
    def settings_screen(self):
        self.header("FILE SETTINGS")
        items=["FILE PRE-BUFFER: "+("ON" if self.prebuffer else "OFF"),"ENABLE LOGS DELETION: "+("ON" if self.delete_enabled else "OFF"),"RETURN"]
        self.choices(items,self.hi["settings"],145,self.small); self.text("PRE-BUFFER ADDS A SHORT STARTUP DELAY",self.small,center=(W//2,296),color=(180,190,240))
    def system_screen(self):
        self.header("SYSTEM SETTINGS")
        display = "FULL SCREEN" if self.fullscreen else "WINDOWED"
        scanlines = ["OFF", "LOW", "MEDIUM", "HIGH"][max(0,min(3,self.scanline_level))]
        signal = "UNSTABLE" if self.signal_unstable else "STABLE"
        items = ["DISPLAY MODE: " + display, "SCANLINE LEVEL: " + scanlines, "SIGNAL STABILITY: " + signal, "RETURN"]
        self.choices(items,self.hi["system"],145,self.small)
        self.text("F11 TOGGLE: DISPLAY MODE",self.small,center=(W//2,302),color=(180,190,240))
    def prebuffer_screen(self):
        self.c.fill(BLACK); self.text("PLAY",self.big,14,10); self.text("PRE-BUFFERING FILE"+"."*min(3,int(self.age()*3)+1),self.menu,center=(W//2,185))
        if self.age()>=1.3: self.go("flash")
    def flash(self):
        self.header("SELECT LOG"); self.text((self.chosen.stem.upper()+".log")[:42],self.menu,52,182)
        if int(self.age()/.125)%2==0: pygame.draw.rect(self.c,RED,(39,179,562,28),4,border_radius=2)
        if self.age()>=.75:self.go("glitch")
    def glitch(self):
        self.c.fill(BLACK); self.text("PLAY",self.big,14,10); r=random.Random(int(self.age()*1000)); y=275+r.randrange(-8,9)
        for x in range(48,592,3): pygame.draw.rect(self.c,r.choice([(230,30,36),(34,190,50),(31,83,240),(225,222,210),(193,23,182)]),(x,y,r.randrange(1,4),r.randrange(34,76)))
        if self.age()>.55:
            ctypes.memset(self.videobuffer, 0, ctypes.sizeof(self.videobuffer))
            media = self.vlc_inst.media_new(str(self.chosen))
            self.player.set_media(media)
            self.player.play()
            self.go("play")
    def play(self):
        state = self.player.get_state()
        if state in (vlc.State.Ended, vlc.State.Error):
            self.player.stop(); self.logs=self.files(); self.go("logs"); return
        frame = pygame.image.frombuffer(self.videobuffer, (W,H), "RGBA")
        self.c.blit(frame, (0,0)); self.text("PLAY",self.big,14,10)
    def delete_screen(self):
        self.header("DELETE LOG"); self.text("DELETE THIS FILE?",self.menu,center=(W//2,135),color=RED); self.text((self.chosen.stem.upper()+".log")[:38],self.small,center=(W//2,168)); self.choices(self.confirm,self.hi["confirm"],215)
    def status(self):
        self.header("SYSTEM MESSAGE"); bad="DISABLED" in self.message or "FAILED" in self.message
        self.text(self.message,self.menu,center=(W//2,180),color=RED if bad else GREEN); self.text("PRESS ENTER",self.small,center=(W//2,245))
    def report(self,msg,back): self.message,self.back=msg,back; self.go("status")

    def enter(self):
        s=self.state
        if s=="ready": self.go("boot")
        elif s=="home": self.go(["loading","folder","settings","system"][self.hi["home"]])
        elif s=="missing":
            if self.hi["missing"]==0: LOGS.mkdir(exist_ok=True); self.report("LOGS FOLDER CREATED","loading")
            else:self.go("home")
        elif s=="logs":
            if self.logs:self.chosen=self.logs[self.hi["logs"]];self.hi["actions"]=0;self.go("actions")
            else:self.logs=self.files()
        elif s=="actions":
            pick=self.hi["actions"]
            if pick==0:self.go("prebuffer" if self.prebuffer else "flash")
            elif pick==1:
                if self.delete_enabled:self.hi["confirm"]=0;self.go("confirm")
                else:self.warn.play();self.report("DELETE OPTION IS DISABLED","logs")
            else:self.go("logs")
        elif s=="folder":
            pick=self.hi["folder"]
            if pick==0:self.report("LOGS FOLDER PRESENT" if LOGS.exists() else "LOGS FOLDER MISSING","folder")
            elif pick==1:LOGS.mkdir(exist_ok=True);self.report("LOGS FOLDER CREATED","folder")
            elif pick==2:self.logs=self.files();self.report("DIRECTORY RESCANNED","folder")
            else:self.go("home")
        elif s=="settings":
            if self.hi["settings"]==0:self.prebuffer=not self.prebuffer;self.save_settings()
            elif self.hi["settings"]==1:self.delete_enabled=not self.delete_enabled;self.save_settings()
            else:self.go("home")
        elif s=="system":
            pick=self.hi["system"]
            if pick==0:self.toggle_fullscreen()
            elif pick==1:self.scanline_level=(self.scanline_level+1)%4;self.save_settings()
            elif pick==2:self.signal_unstable=not self.signal_unstable;self.save_settings()
            else:self.go("home")
        elif s=="confirm":
            if self.hi["confirm"]==1:
                try:self.chosen.unlink();self.logs=self.files();self.hi["logs"]=min(self.hi["logs"],max(0,len(self.logs)-1));self.report("LOG FILE DELETED","logs")
                except OSError:self.report("DELETE FAILED","logs")
            else:self.go("actions")
        elif s=="status":self.go(self.back)
    def key(self,key):
        if key == pygame.K_F11:
            self.toggle_fullscreen(); return
        if key==pygame.K_ESCAPE:
            if self.state in ("ready","home","boot"):self.running=False
            elif self.state=="play":self.player.stop();self.go("logs")
            else:self.go("home")
            return
        if key in (pygame.K_RETURN,pygame.K_KP_ENTER):self.enter();return
        if key not in (pygame.K_UP,pygame.K_DOWN):return
        data={"home":(len(self.home),"home"),"missing":(2,"missing"),"logs":(len(self.logs),"logs"),"actions":(3,"actions"),"folder":(4,"folder"),"settings":(3,"settings"),"system":(4,"system"),"confirm":(2,"confirm")}
        if self.state in data and data[self.state][0]:
            n,name=data[self.state];self.hi[name]=(self.hi[name]+(-1 if key==pygame.K_UP else 1))%n;self.tick.play()
    def draw(self):
        {"ready":self.ready,"boot":self.boot,"home":self.home_screen,"loading":self.loading,"missing":self.missing,"logs":self.log_list,"actions":self.action_screen,"folder":self.folder_screen,"settings":self.settings_screen,"system":self.system_screen,"prebuffer":self.prebuffer_screen,"flash":self.flash,"glitch":self.glitch,"play":self.play,"confirm":self.delete_screen,"status":self.status}[self.state]()
    def present(self):
        self.lines(); self.signal_noise(); ww,wh=self.win.get_size();scale=max(1,min(ww//W,wh//H));out=pygame.transform.scale(self.c,(W*scale,H*scale));self.win.fill(BLACK);self.win.blit(out,((ww-out.get_width())//2,(wh-out.get_height())//2));pygame.display.flip()
    def run(self):
        while self.running:
            for e in pygame.event.get():
                if e.type==pygame.QUIT:self.running=False
                elif e.type==pygame.KEYDOWN:self.key(e.key)
            self.draw();self.present();self.clock.tick(30)
        self.player.stop()
        pygame.quit()

System().run()