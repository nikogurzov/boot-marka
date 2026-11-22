"""Ядрото на boot-marka: чете как е настроено зареждането (Plymouth, ядро, GRUB) и подготвя промените.
Тук нищо не се пише в системата. Промените ги прави само prilozhi.py като root (през pkexec)."""
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field

VERSION = "0.4.0"
ROOT = os.environ.get("BOOT_MARKA_ROOT", "")            # за тестовете: пясъчник вместо /
THEMES = ROOT + "/usr/share/plymouth/themes"
GRUB_MAIN = ROOT + "/etc/default/grub"
GRUB_DIR = ROOT + "/etc/default/grub.d"
DROPIN = GRUB_DIR + "/99-boot-marka.cfg"
ISTORIA = ROOT + "/var/lib/boot-marka/istoria.json"
PREFIX = "boot-marka-"                                   # собствените теми: boot-marka-<име>
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
THEME = re.compile(r"^[A-Za-z0-9._-]{1,60}$")
GFX = re.compile(r"^(auto|[0-9]{3,4}x[0-9]{3,4}(x[0-9]{2})?)$")

# ---------------------------------------------------------------- режими на текста при зареждане
# Токените, които програмата управлява в реда на ядрото. Всичко друго (напр. amdgpu.dcdebugmask) остава.
MANAGED = re.compile(r"^(quiet|splash|nosplash|loglevel=\S*|udev\.log_level=\S*|rd\.udev\.log_level=\S*|"
                     r"systemd\.show_status=\S*|rd\.systemd\.show_status=\S*|vt\.global_cursor_default=\S*|plymouth\.enable=\S*)$")
MODES = {
    "tih": ("Тих", "Само анимацията. Без съобщения на ядрото и без мигащ курсор. Esc ги показва, ако потрябват.",
            ["quiet", "splash", "loglevel=3", "udev.log_level=3", "rd.udev.log_level=3",
             "systemd.show_status=false", "rd.systemd.show_status=false", "vt.global_cursor_default=0"]),
    "normalen": ("Нормален", "Анимация, но важните съобщения на системата може да се мярнат.", ["quiet", "splash"]),
    "podroben": ("Подробен", "Без анимация, всичко се изписва. За когато нещо не тръгва.", []),
}


def split_cmdline(s):
    return [t for t in (s or "").split() if t]


def keep_tokens(cmdline):
    """Токените, които не са наши (те остават непокътнати)."""
    return [t for t in split_cmdline(cmdline) if not MANAGED.match(t)]


def build_cmdline(base, mode):
    return " ".join(keep_tokens(base) + MODES[mode][2])


def detect_mode(cmdline):
    t = set(split_cmdline(cmdline))
    if "splash" not in t or "quiet" not in t:
        return "podroben"
    if "loglevel=3" in t or "loglevel=0" in t or "vt.global_cursor_default=0" in t:
        return "tih"
    return "normalen"


# ---------------------------------------------------------------- GRUB
GRUB_KEYS = ["GRUB_TIMEOUT", "GRUB_TIMEOUT_STYLE", "GRUB_DEFAULT", "GRUB_SAVEDEFAULT", "GRUB_BACKGROUND", "GRUB_THEME",
             "GRUB_GFXMODE", "GRUB_CMDLINE_LINUX_DEFAULT", "GRUB_HIDDEN_TIMEOUT"]


def read_grub(include_ours=True):
    """Ефективните настройки на GRUB така, както ги вижда update-grub (bash чете основния файл и grub.d/*.cfg)."""
    files = [GRUB_MAIN] + sorted(f for f in glob.glob(GRUB_DIR + "/*.cfg") if include_ours or f != DROPIN)
    src = "".join(f'[ -r {shlex.quote(f)} ] && . {shlex.quote(f)} >/dev/null 2>&1\n' for f in files)
    out = "".join(f'printf "%s\\0" "${k}"\n' for k in GRUB_KEYS)
    try:
        r = subprocess.run(["bash", "-c", src + out], capture_output=True, text=True, timeout=10)
        vals = r.stdout.split("\0")
    except (OSError, subprocess.TimeoutExpired):
        vals = []
    return {k: (vals[i] if i < len(vals) else "") for i, k in enumerate(GRUB_KEYS)}


@dataclass
class GrubPlan:
    timeout: int = 0
    style: str = "hidden"          # hidden / countdown / menu
    remember: bool = False
    background: str = ""           # път до картинка ("" = без, "keep" = остави както е)
    gfx: str = "auto"


def grub_from_settings(g):
    try:
        to = int(g.get("GRUB_TIMEOUT") or 5)
    except ValueError:
        to = 5
    style = g.get("GRUB_TIMEOUT_STYLE") or ("hidden" if g.get("GRUB_HIDDEN_TIMEOUT") not in ("", None) else "menu")
    if style not in ("hidden", "countdown", "menu"):
        style = "menu"
    return GrubPlan(timeout=max(0, min(30, to)), style=style,
                    remember=g.get("GRUB_DEFAULT") == "saved" and g.get("GRUB_SAVEDEFAULT") == "true",
                    background="keep", gfx=g.get("GRUB_GFXMODE") or "auto")


def dropin_text(cmdline, gp, bg_final=None):
    """Съдържанието на /etc/default/grub.d/99-boot-marka.cfg. Основният /etc/default/grub не се пипа."""
    L = ["# boot-marka: настройките на зареждането, направени с програмата „Зареждане (boot-marka)“.",
         "# Основният /etc/default/grub не е пипан. За да се върне старото: изтрий този файл и пусни sudo update-grub",
         "# (или в програмата: ↶ Върни както беше).",
         f"GRUB_CMDLINE_LINUX_DEFAULT={shlex.quote(cmdline)}",
         f"GRUB_TIMEOUT={int(gp.timeout)}",
         f"GRUB_TIMEOUT_STYLE={gp.style}",
         "unset GRUB_HIDDEN_TIMEOUT GRUB_HIDDEN_TIMEOUT_QUIET   # остарели настройки; заменени от GRUB_TIMEOUT_STYLE"]
    if gp.remember:
        L += ["GRUB_DEFAULT=saved", "GRUB_SAVEDEFAULT=true"]
    if gp.gfx and gp.gfx != "auto":
        L.append(f"GRUB_GFXMODE={gp.gfx}")
    if bg_final:
        L.append(f"GRUB_BACKGROUND={shlex.quote(bg_final)}")
    elif gp.background == "":
        L.append("unset GRUB_BACKGROUND")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- Plymouth
@dataclass
class Theme:
    name: str
    title: str
    module: str
    path: str
    ours: bool = False
    frames: list = field(default_factory=list)   # картинки за анимираната миниатюра
    background: str = ""
    bg_color: tuple = (0, 0, 0)


FRAME_PATTERNS = ["frame-*.png", "animation-*.png", "throbber-*.png", "progress-*.png", "spinner*.png", "box*.png"]
BG_PATTERNS = ["background*.png", "plymouth_background*.png", "*background*.png", "bgrt-fallback.png", "watermark.png", "logo*.png", "debian.png"]


def _num(p):
    m = re.findall(r"(\d+)", os.path.basename(p))
    return int(m[-1]) if m else 0


def theme_info(path):
    d = os.path.dirname(path)
    name = os.path.basename(d)
    title, module, lang = name, "", {}
    try:
        for line in open(path, encoding="utf-8", errors="replace"):
            line = line.strip()
            m = re.match(r"^Name(\[([a-zA-Z_]+)\])?\s*=\s*(.+)$", line)
            if m:
                lang[m.group(2) or ""] = m.group(3)
            m = re.match(r"^ModuleName\s*=\s*(\S+)", line)
            if m:
                module = m.group(1)
    except OSError:
        pass
    title = lang.get("bg") or lang.get("") or name
    t = Theme(name=name, title=title, module=module, path=d, ours=name.startswith(PREFIX))
    for pat in FRAME_PATTERNS:
        fr = sorted(glob.glob(os.path.join(d, pat)), key=_num)
        if len(fr) >= 2:
            t.frames = fr[:120]
            break
    for pat in BG_PATTERNS:
        b = glob.glob(os.path.join(d, pat))
        if b:
            t.background = max(b, key=os.path.getsize)
            break
    if not t.frames and not t.background:
        pngs = glob.glob(os.path.join(d, "*.png"))
        if pngs:
            t.background = max(pngs, key=os.path.getsize)
    meta = os.path.join(d, "boot-marka.json")
    if t.ours and os.path.exists(meta):
        try:
            t.bg_color = tuple(json.load(open(meta)).get("bg", [0, 0, 0]))
        except (OSError, ValueError):
            pass
    return t


SKIP = {"text", "details"}     # „текстови“ теми без картинка; показват се отделно като „без анимация“


def themes():
    out, skrij = [], set(os.environ.get("BOOT_MARKA_SKRIJ", "").split(","))   # за снимки: скрива избрани теми
    for p in sorted(glob.glob(THEMES + "/*/*.plymouth")):
        if os.path.basename(os.path.dirname(p)) in skrij:
            continue
        if os.path.basename(p)[:-9] != os.path.basename(os.path.dirname(p)):
            continue
        out.append(theme_info(p))
    out.sort(key=lambda t: (not t.ours, t.name in SKIP, t.title.lower()))
    return out


def current_theme():
    for cmd in (["/usr/sbin/plymouth-set-default-theme"], ["plymouth-set-default-theme"]):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            continue
    return ""


# ---------------------------------------------------------------- проверки
def nvidia_note():
    """Plymouth с NVIDIA иска KMS (nvidia-drm.modeset=1). Връща текст за предупреждение или ""."""
    if not os.path.isdir("/sys/module/nvidia_drm"):
        return ""
    try:
        v = open("/sys/module/nvidia_drm/parameters/modeset").read().strip()
    except OSError:
        v = ""
    if v == "Y":
        return ""
    return ("Видеокартата NVIDIA е без „modeset“. Ако екранът е вързан към нея, анимацията може да не се покаже. "
            "Отметни „Поправка за NVIDIA“, за да добавя nvidia-drm.modeset=1.")


def encrypted():
    try:
        return any(l.strip() and not l.lstrip().startswith("#") for l in open(ROOT + "/etc/crypttab"))
    except OSError:
        return False


@dataclass
class State:
    theme: str
    themes: list
    grub: dict
    grub_base: dict
    cmdline_now: str
    mode: str
    plan: GrubPlan
    ours: bool
    nvidia: str
    crypt: bool


def collect():
    g = read_grub(True)
    gb = read_grub(False)
    try:
        now = open("/proc/cmdline").read().strip()
    except OSError:
        now = ""
    return State(theme=current_theme(), themes=themes(), grub=g, grub_base=gb, cmdline_now=now,
                 mode=detect_mode(g.get("GRUB_CMDLINE_LINUX_DEFAULT", "")), plan=grub_from_settings(g),
                 ours=os.path.exists(DROPIN), nvidia=nvidia_note(), crypt=encrypted())


def history():
    try:
        return json.load(open(ISTORIA))
    except (OSError, ValueError):
        return []


# ---------------------------------------------------------------- собствена анимация (прави се без root, в /tmp)
SCRIPT = """# boot-marka: собствена анимация „{title}“ (направена с програмата „Зареждане (boot-marka)“)
N = {n};
DIV = {div};
Window.SetBackgroundTopColor({r}, {g}, {b});
Window.SetBackgroundBottomColor({r}, {g}, {b});
sw = Window.GetWidth();
sh = Window.GetHeight();
wx = Window.GetX();
wy = Window.GetY();
size = Math.Min(sw, sh) * {scale};
first = Image("frame-1.png");
k = size / first.GetHeight();
if (first.GetWidth() * k > sw * 0.9) k = sw * 0.9 / first.GetWidth();
i = 0;
while (i < N) {{
    img = Image("frame-" + (i + 1) + ".png");
    frames[i] = img.Scale(img.GetWidth() * k, img.GetHeight() * k);
    i = i + 1;
}}
anim = Sprite(frames[0]);
anim.SetPosition(wx + sw / 2 - frames[0].GetWidth() / 2, wy + sh * {ypos} - frames[0].GetHeight() / 2, 10);
bottom = wy + sh * {ypos} + frames[0].GetHeight() / 2;
{label}
{ind_setup}
tick = 0;
fun refresh_callback () {{
    tick = tick + 1;
    idx = Math.Int(tick / DIV);
    idx = idx - Math.Int(idx / N) * N;
    anim.SetImage(frames[idx]);
{ind_tick}
}}
Plymouth.SetRefreshFunction(refresh_callback);
# парола (ако дискът е криптиран) и съобщения
pw = Sprite();
fun display_password_callback (prompt, bullets) {{
    s = prompt + "   ";
    j = 0;
    while (j < bullets) {{
        s = s + "*";
        j = j + 1;
    }}
    t = Image.Text(s, 1, 1, 1);
    pw.SetImage(t);
    pw.SetPosition(wx + sw / 2 - t.GetWidth() / 2, wy + sh * 0.85, 100);
    pw.SetOpacity(1);
}}
fun display_normal_callback () {{
    pw.SetOpacity(0);
}}
Plymouth.SetDisplayPasswordFunction(display_password_callback);
Plymouth.SetDisplayNormalFunction(display_normal_callback);
msg = Sprite();
fun message_callback (text) {{
    t = Image.Text(text, 1, 1, 1);
    msg.SetImage(t);
    msg.SetPosition(wx + sw / 2 - t.GetWidth() / 2, wy + sh * 0.92, 100);
}}
Plymouth.SetMessageFunction(message_callback);
"""

LABEL = """lab = Image("label.png");
lk = (size * 0.9) / lab.GetWidth();
if (lk > 1) lk = 1;
lab = lab.Scale(lab.GetWidth() * lk, lab.GetHeight() * lk);
labs = Sprite(lab);
labs.SetPosition(wx + sw / 2 - lab.GetWidth() / 2, bottom + sh * 0.03, 10);
bottom = bottom + sh * 0.03 + lab.GetHeight();"""

PROGRESS = """bar = Image("bar.png");
barw = Math.Min(sw, sh) * 0.35;
bars = Sprite();
fun progress_callback (duration, progress) {{
    w = barw * progress;
    if (w >= 2) {{
        bars.SetImage(bar.Scale(w, 4));
        bars.SetPosition(wx + sw / 2 - barw / 2, bottom + sh * 0.04, 10);
        bars.SetOpacity(0.85);
    }}
}}
Plymouth.SetBootProgressFunction(progress_callback);"""


# ---------------------------------------------------------------- какво има под анимацията (повтарящо се, не зависи от времето)
INDIKATORI = [("trikolor", "Трикольор: една лента блещука отляво надясно, с искра"),
              ("zname", "Знаме: три ивици се пълнят на място, с искри"),
              ("begashta", "Бягаща светлинка (повтаря се)"), ("tochki", "Три пулсиращи точки"),
              ("nadpis", "Надпис „Зареждане…“, който свети и угасва"), ("lenta", "Лента за напредъка (може да не стигне до края)"),
              ("nyama", "Нищо")]
ZNAME_SETUP = """tb = Image("b-bial.png");
tz = Image("b-zelen.png");
tc = Image("b-cherven.png");
iskra0 = Image("iskra.png");
md = Math.Min(sw, sh);
barw = md * 0.26;
bh = md * 0.006;
if (bh < 3) bh = 3;
gap = bh * 0.7;
barx = wx + sw / 2 - barw / 2;
bary = bottom + sh * 0.05;
iks = md * 0.03;
isk = iskra0.Scale(iks, iks);
big = iskra0.Scale(iks * 2.2, iks * 2.2);
col[0] = tb;
col[1] = tz;
col[2] = tc;
j = 0;
while (j < 3) {
    trk[j] = Sprite(col[j].Scale(barw, bh));
    trk[j].SetPosition(barx, bary + j * (bh + gap), 10);
    trk[j].SetOpacity(0.14);
    segs[j] = Sprite();
    iskri[j] = Sprite(isk);
    iskri[j].SetOpacity(0);
    j = j + 1;
}
fl = Sprite(big);
fl.SetOpacity(0);"""

ZNAME_TICK = """    t = tick / 150;
    t = t - Math.Int(t);
    fade = 1;
    if (t > 0.8) fade = 1 - (t - 0.8) / 0.2;
    j = 0;
    while (j < 3) {
        f = (t - j * 0.1) / 0.45;
        if (f < 0) f = 0;
        if (f > 1) f = 1;
        f = f * f * (3 - 2 * f);
        fw = f * barw;
        y = bary + j * (bh + gap);
        if (fw >= 2) {
            segs[j].SetImage(col[j].Scale(fw, bh));
            segs[j].SetPosition(barx, y, 11);
            segs[j].SetOpacity(0.95 * fade);
            if (f < 1) {
                iskri[j].SetPosition(barx + fw - iks / 2, y + bh / 2 - iks / 2, 20);
                iskri[j].SetOpacity(0.5 + 0.5 * (0.5 + 0.5 * Math.Sin(tick * 0.9 + j * 2)));
            } else {
                iskri[j].SetOpacity(0);
            }
        } else {
            segs[j].SetOpacity(0);
            iskri[j].SetOpacity(0);
        }
        j = j + 1;
    }
    if (t > 0.62 && t < 0.8) {
        fl.SetPosition(barx + barw - iks * 1.1, bary + bh + gap + bh / 2 - iks * 1.1, 21);
        fl.SetOpacity(Math.Sin((t - 0.62) / 0.18 * 3.14159));
    } else {
        fl.SetOpacity(0);
    }"""

TRIKOLOR_SETUP = """tb = Image("b-bial.png");
tz = Image("b-zelen.png");
tc = Image("b-cherven.png");
iskra0 = Image("iskra.png");
md = Math.Min(sw, sh);
barw = md * 0.30;
bh = md * 0.008;
if (bh < 4) bh = 4;
NC = 24;
cw = barw / NC;
barx = wx + sw / 2 - barw / 2;
bary = bottom + sh * 0.05;
iks = md * 0.05;
isk = iskra0.Scale(iks, iks);
c = 0;
while (c < NC) {
    im = tc;
    if (c < NC * 2 / 3) im = tz;
    if (c < NC / 3) im = tb;
    cell[c] = Sprite(im.Scale(cw - 2, bh));
    cell[c].SetPosition(barx + c * cw + 1, bary, 10);
    cell[c].SetOpacity(0.3);
    c = c + 1;
}
ride = Sprite(isk);
ride.SetOpacity(0);"""

TRIKOLOR_TICK = """    t = tick / 100;
    t = t - Math.Int(t);
    wave = t * 1.4 - 0.2;
    c = 0;
    while (c < NC) {
        x = (c + 0.5) / NC;
        g = 1 - Math.Abs(x - wave) / 0.22;
        if (g < 0) g = 0;
        g = g * g;
        tw = 0.12 * (0.5 + 0.5 * Math.Sin(tick * 0.37 + c * 1.7));
        cell[c].SetOpacity(0.32 + tw + 0.68 * g);
        c = c + 1;
    }
    if (wave > 0 && wave < 1) {
        ride.SetPosition(barx + wave * barw - iks / 2, bary + bh / 2 - iks / 2, 20);
        ride.SetOpacity(0.55 + 0.45 * (0.5 + 0.5 * Math.Sin(tick * 1.1)));
    } else {
        ride.SetOpacity(0);
    }"""

IND = {
    "trikolor": (TRIKOLOR_SETUP, TRIKOLOR_TICK),
    "zname": (ZNAME_SETUP, ZNAME_TICK),
    "begashta": ("""bar = Image("bar.png");
barw = Math.Min(sw, sh) * 0.28;
bary = bottom + sh * 0.05;
barx = wx + sw / 2 - barw / 2;
track = Sprite(bar.Scale(barw, 2));
track.SetPosition(barx, bary + 1, 10);
track.SetOpacity(0.22);
seg = Sprite();""", """    p = tick / 90;
    p = p - Math.Int(p);
    a = p * 1.4 - 0.4;
    b = p * 1.4;
    if (a < 0) a = 0;
    if (b > 1) b = 1;
    segw = (b - a) * barw;
    if (segw >= 2) {
        seg.SetImage(bar.Scale(segw, 4));
        seg.SetPosition(barx + a * barw, bary, 11);
        seg.SetOpacity(0.9);
    } else {
        seg.SetOpacity(0);
    }"""),
    "tochki": ("""dot = Image("dot.png");
ds = Math.Min(sw, sh) * 0.014;
dot = dot.Scale(ds, ds);
dy = bottom + sh * 0.05;
d0 = Sprite(dot);
d1 = Sprite(dot);
d2 = Sprite(dot);
d0.SetPosition(wx + sw / 2 - ds * 2.5, dy, 10);
d1.SetPosition(wx + sw / 2 - ds * 0.5, dy, 10);
d2.SetPosition(wx + sw / 2 + ds * 1.5, dy, 10);""", """    ph = tick * 0.11;
    d0.SetOpacity(0.25 + 0.75 * (0.5 + 0.5 * Math.Sin(ph)));
    d1.SetOpacity(0.25 + 0.75 * (0.5 + 0.5 * Math.Sin(ph - 0.9)));
    d2.SetOpacity(0.25 + 0.75 * (0.5 + 0.5 * Math.Sin(ph - 1.8)));"""),
    "nadpis": ("""zt = Image("zarezhdane.png");
zk = (Math.Min(sw, sh) * 0.22) / zt.GetWidth();
if (zk > 1) zk = 1;
zt = zt.Scale(zt.GetWidth() * zk, zt.GetHeight() * zk);
zs = Sprite(zt);
zs.SetPosition(wx + sw / 2 - zt.GetWidth() / 2, bottom + sh * 0.04, 10);""",
               """    zs.SetOpacity(0.3 + 0.7 * (0.5 + 0.5 * Math.Sin(tick * 0.06)));"""),
}


def ImageChops_lighter(a, b):
    from PIL import ImageChops
    return ImageChops.lighter(a, b)


def slugify(s):
    tr = str.maketrans({"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ж": "zh", "з": "z", "и": "i", "й": "y",
                        "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
                        "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sht", "ъ": "a", "ь": "y", "ю": "yu", "я": "ya"})
    s = re.sub(r"[^a-z0-9]+", "-", s.lower().translate(tr)).strip("-")
    return (s or "moya")[:40]


@dataclass
class Custom:
    title: str
    src: str
    bg: tuple = (0, 0, 0)        # 0..255
    scale: float = 0.30          # дял от по-малката страна на екрана
    ypos: float = 0.45           # къде е центърът по височина
    fps: float = 20.0
    max_frames: int = 90
    label: str = ""
    label_color: tuple = (255, 255, 255)
    indicator: str = "trikolor"   # виж INDIKATORI


def make_custom(c, workdir=None, log=print):
    """Прави файловете на темата в папка в /tmp (без root). Връща (папка, slug, брой кадри, размер в байтове)."""
    slug = slugify(c.title)
    name = PREFIX + slug
    d = workdir or tempfile.mkdtemp(prefix="boot-marka-")
    os.makedirs(d, exist_ok=True)
    for f in glob.glob(os.path.join(d, "*")):
        os.remove(f)
    px = 420                                    # кадрите се смаляват предварително (малък initramfs, бързо зареждане)
    vf = f"fps={c.fps},scale=-2:{px}:flags=lanczos" if not c.src.lower().endswith((".png", ".jpg", ".jpeg", ".webp")) \
        else f"scale=-2:{px}:flags=lanczos"
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", c.src, "-vf", vf, "-frames:v", str(int(c.max_frames)),
           "-start_number", "1", os.path.join(d, "frame-%d.png")]
    log("Правя кадрите…")
    r = subprocess.run(cmd, capture_output=True, text=True)
    frames = sorted(glob.glob(os.path.join(d, "frame-*.png")), key=_num)
    if r.returncode != 0 or not frames:
        raise RuntimeError("Не можах да извадя кадри от файла. " + (r.stderr.strip()[-300:] if r.stderr else ""))
    n = len(frames)
    if n == 1:                                  # снимка или лого: „диша“ — същият кадър, без анимация
        pass
    from PIL import Image, ImageDraw, ImageFont
    Image.new("RGB", (1, 1), (255, 255, 255)).save(os.path.join(d, "bar.png"))

    def shrift(sz):
        for fp in ("/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf", "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
            if os.path.exists(fp):
                return ImageFont.truetype(fp, sz)
        return ImageFont.load_default()

    if c.indicator in ("trikolor", "zname"):
        for fn, rgb in (("b-bial.png", (255, 255, 255)), ("b-zelen.png", (0, 150, 110)), ("b-cherven.png", (214, 38, 18))):
            Image.new("RGB", (1, 1), rgb).save(os.path.join(d, fn))
        from PIL import ImageFilter
        S_ = 128
        m = Image.new("L", (S_, S_), 0); md = ImageDraw.Draw(m)
        c0 = S_ // 2
        md.ellipse((c0 - 10, c0 - 10, c0 + 10, c0 + 10), fill=255)                      # ядро
        md.line((c0, 6, c0, S_ - 6), fill=200, width=4); md.line((6, c0, S_ - 6, c0), fill=200, width=4)   # лъчите на искрата
        m = Image.composite(m, m.filter(ImageFilter.GaussianBlur(6)), m)
        halo = Image.new("L", (S_, S_), 0); ImageDraw.Draw(halo).ellipse((c0 - 30, c0 - 30, c0 + 30, c0 + 30), fill=120)
        m = ImageChops_lighter(m, halo.filter(ImageFilter.GaussianBlur(14)))
        iskra = Image.new("RGBA", (S_, S_), (255, 255, 240, 0)); iskra.putalpha(m)
        iskra.resize((64, 64), Image.LANCZOS).save(os.path.join(d, "iskra.png"))
    if c.indicator == "tochki":
        big = Image.new("L", (256, 256), 0)
        ImageDraw.Draw(big).ellipse((8, 8, 248, 248), fill=255)
        dot = Image.new("RGBA", (64, 64), (*c.label_color, 0))
        dot.putalpha(big.resize((64, 64), Image.LANCZOS))
        dot.save(os.path.join(d, "dot.png"))
    if c.indicator == "nadpis":
        f2 = shrift(44)
        tw = int(ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength("Зареждане…", font=f2)) + 20
        z = Image.new("RGBA", (tw, 66), (0, 0, 0, 0))
        ImageDraw.Draw(z).text((10, 6), "Зареждане…", font=f2, fill=(*c.label_color, 255))
        z.save(os.path.join(d, "zarezhdane.png"))
    label = ""
    if c.label.strip():
        fnt = shrift(56)
        txt = c.label.strip()[:40]
        w = int(ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(txt, font=fnt)) + 20
        im = Image.new("RGBA", (max(w, 10), 80), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((10, 10), txt, font=fnt, fill=(*c.label_color, 255))
        im.save(os.path.join(d, "label.png"))
        label = LABEL
    div = max(1, round(50.0 / max(1.0, c.fps)))        # Plymouth вика refresh ~50 пъти в секунда
    r_, g_, b_ = (x / 255 for x in c.bg)
    script = SCRIPT.format(title=c.title.replace('"', "'"), n=n, div=div, r=f"{r_:.3f}", g=f"{g_:.3f}", b=f"{b_:.3f}",
                           scale=f"{c.scale:.3f}", ypos=f"{c.ypos:.3f}", label=label,
                           ind_setup=(PROGRESS.replace("{{", "{").replace("}}", "}") if c.indicator == "lenta" else IND.get(c.indicator, ("", ""))[0]),
                           ind_tick=IND.get(c.indicator, ("", ""))[1])
    open(os.path.join(d, name + ".script"), "w", encoding="utf-8").write(script)
    final = f"/usr/share/plymouth/themes/{name}"
    open(os.path.join(d, name + ".plymouth"), "w", encoding="utf-8").write(
        "[Plymouth Theme]\n"
        f"Name=boot-marka: {c.title}\n"
        "Description=Собствена анимация, направена с boot-marka\n"
        "ModuleName=script\n\n[script]\n"
        f"ImageDir={final}\nScriptFile={final}/{name}.script\n")
    json.dump({"title": c.title, "bg": list(c.bg), "src": os.path.basename(c.src), "frames": n},
              open(os.path.join(d, "boot-marka.json"), "w"), ensure_ascii=False)
    size = sum(os.path.getsize(f) for f in glob.glob(os.path.join(d, "*")))
    return d, slug, n, size


# ---------------------------------------------------------------- команда за помощника
def apply_command(helper, theme=None, mode=None, gp=None, bg_src=None, new_theme_dir=None, new_slug=None, nvidia=False):
    cmd = ["pkexec", "/usr/bin/python3", "-I", helper]
    if new_theme_dir:
        cmd += ["--nova-tema", new_theme_dir, new_slug]
    if theme:
        cmd += ["--tema", theme]
    if mode:
        cmd += ["--rezhim", mode]
    if gp:
        cmd += ["--grub-vreme", str(int(gp.timeout)), "--grub-stil", gp.style, "--grub-gfx", gp.gfx or "auto",
                "--grub-pomni", "1" if gp.remember else "0"]
        if bg_src:
            cmd += ["--grub-fon", bg_src]
        elif gp.background == "":
            cmd += ["--grub-fon", "-"]
    if nvidia:
        cmd.append("--nvidia")
    return cmd


def reset_command(helper):
    return ["pkexec", "/usr/bin/python3", "-I", helper, "--varni"]


def as_text(s):
    L = [f"boot-marka {VERSION}",
         f"Анимация (Plymouth): {s.theme or 'няма'}",
         f"Текст при зареждане: {MODES[s.mode][0]}",
         f"GRUB: {s.plan.timeout} с, меню: {s.plan.style}, помни последния избор: {'да' if s.plan.remember else 'не'}, "
         f"разделителна способност: {s.plan.gfx}",
         f"Ред на ядрото (настроен): {s.grub.get('GRUB_CMDLINE_LINUX_DEFAULT', '')}",
         f"Ред на ядрото (сега): {s.cmdline_now}",
         f"Настройки от boot-marka: {'да' if s.ours else 'не'}"]
    if s.nvidia:
        L.append("⚠ " + s.nvidia)
    L.append("Теми: " + ", ".join(t.name for t in s.themes))
    return "\n".join(L) + "\n"
