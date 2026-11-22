#!/usr/bin/env python3
"""Помощникът на boot-marka, който единствен пипа системата. Пуска се като root през pkexec:
   pkexec /usr/bin/python3 -I prilozhi.py [--nova-tema ПАПКА ИМЕ] [--tema ТЕМА] [--rezhim tih|normalen|podroben]
          [--grub-vreme N] [--grub-stil hidden|countdown|menu] [--grub-gfx auto|1920x1080] [--grub-pomni 0|1]
          [--grub-fon КАРТИНКА.png|-] [--nvidia]
   pkexec /usr/bin/python3 -I prilozhi.py --varni          връща всичко както е било преди програмата
Пише само: /etc/default/grub.d/99-boot-marka.cfg, темите /usr/share/plymouth/themes/boot-marka-*,
/boot/grub/boot-marka-fon.png и избраната тема на Plymouth. После пуска update-initramfs и update-grub.
Основният /etc/default/grub не се пипа. Историята е в /var/lib/boot-marka/istoria.json."""
import glob
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import jezgro as J

TEST = os.environ.get("BOOT_MARKA_TEST") == "1" and bool(J.ROOT)     # пясъчник за тестовете: не пуска системни команди
BACKUPS = J.ROOT + "/var/backups/boot-marka"
BG_FINAL = "/boot/grub/boot-marka-fon.png"
PLY_CONF = J.ROOT + "/etc/plymouth/plymouthd.conf"
ENV = dict(os.environ, LC_ALL="C.UTF-8")
ALLOWED = re.compile(r"^(frame-[0-9]{1,4}\.png|bar\.png|label\.png|dot\.png|zarezhdane\.png|boot-marka\.json|boot-marka-[a-z0-9-]{1,40}\.(script|plymouth))$")
MAX_THEME = 60 * 1024 * 1024


def say(s):
    print(s, flush=True)


def die(s):
    say("ГРЕШКА: " + s)
    sys.exit(2)


def run(cmd):
    say("$ " + " ".join(cmd))
    if TEST:
        return 0
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace", env=ENV)
    for line in p.stdout:
        say("  " + line.rstrip())
    return p.wait()


def args(argv):
    a, i = {}, 0
    one = {"--tema", "--rezhim", "--grub-vreme", "--grub-stil", "--grub-gfx", "--grub-pomni", "--grub-fon"}
    while i < len(argv):
        k = argv[i]
        if k == "--nova-tema" and i + 2 < len(argv):
            a[k] = (argv[i + 1], argv[i + 2]); i += 3
        elif k in one and i + 1 < len(argv):
            a[k] = argv[i + 1]; i += 2
        elif k in ("--nvidia", "--varni"):
            a[k] = True; i += 1
        else:
            die(f"непознат аргумент: {k}")
    if "--tema" in a and not J.THEME.match(a["--tema"]):
        die("неправилно име на тема")
    if "--rezhim" in a and a["--rezhim"] not in J.MODES:
        die("неправилен режим")
    if "--grub-vreme" in a and not (a["--grub-vreme"].isdigit() and 0 <= int(a["--grub-vreme"]) <= 30):
        die("времето на GRUB трябва да е от 0 до 30 секунди")
    if "--grub-stil" in a and a["--grub-stil"] not in ("hidden", "countdown", "menu"):
        die("неправилен вид на менюто")
    if "--grub-gfx" in a and not J.GFX.match(a["--grub-gfx"]):
        die("неправилна разделителна способност")
    if "--grub-pomni" in a and a["--grub-pomni"] not in ("0", "1"):
        die("--grub-pomni е 0 или 1")
    if "--nova-tema" in a and not J.SLUG.match(a["--nova-tema"][1]):
        die("неправилно име на новата тема")
    return a


# ---------------------------------------------------------------- Plymouth
def cur_theme():
    if TEST:
        try:
            m = re.search(r"^Theme=(\S+)", open(PLY_CONF).read(), re.M)
            return m.group(1) if m else ""
        except OSError:
            return ""
    return J.current_theme()


def set_theme(name):
    if not os.path.exists(f"{J.THEMES}/{name}/{name}.plymouth"):
        die(f"няма такава тема: {name}")
    if TEST:
        os.makedirs(os.path.dirname(PLY_CONF), exist_ok=True)
        open(PLY_CONF, "w").write(f"[Daemon]\nTheme={name}\n")
        return 0
    return run(["/usr/sbin/plymouth-set-default-theme", name])


def png_ok(path, max_side=8192):
    try:
        with open(path, "rb") as f:
            h = f.read(24)
        if h[:8] != b"\x89PNG\r\n\x1a\n" or h[12:16] != b"IHDR":
            return False
        w, hh = struct.unpack(">II", h[16:24])
        return 0 < w <= max_side and 0 < hh <= max_side
    except OSError:
        return False


def install_theme(src, slug):
    """Копира готовата тема от потребителската папка след проверка на всеки файл."""
    name = J.PREFIX + slug
    if not os.path.isdir(src) or os.path.islink(src):
        die("папката с новата тема липсва")
    files = os.listdir(src)
    bad = [f for f in files if not ALLOWED.match(f) or os.path.islink(os.path.join(src, f)) or not os.path.isfile(os.path.join(src, f))]
    if bad:
        die("непознати файлове в темата: " + ", ".join(bad[:5]))
    for need in (f"{name}.plymouth", f"{name}.script", "frame-1.png"):
        if need not in files:
            die(f"липсва {need}")
    if any(f.endswith((".script", ".plymouth")) and not f.startswith(name + ".") for f in files):
        die("файловете на темата са за друго име")
    pl = open(os.path.join(src, name + ".plymouth"), encoding="utf-8").read()
    final = f"/usr/share/plymouth/themes/{name}"
    if f"ImageDir={final}\n" not in pl or f"ScriptFile={final}/{name}.script" not in pl or "ModuleName=script" not in pl:
        die("файлът .plymouth не е направен от програмата")
    for f in files:
        if f.endswith(".png") and not png_ok(os.path.join(src, f)):
            die(f"{f} не е правилна PNG картинка")
    size = sum(os.path.getsize(os.path.join(src, f)) for f in files)
    if size > MAX_THEME:
        die(f"темата е твърде голяма ({size // 1048576} MB, най-много {MAX_THEME // 1048576} MB)")
    dst = f"{J.THEMES}/{name}"
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(dst, mode=0o755)
    for f in files:
        shutil.copyfile(os.path.join(src, f), os.path.join(dst, f))
        os.chmod(os.path.join(dst, f), 0o644)
    say(f"Темата е сложена: {dst} ({len(files)} файла, {size // 1024} KB)")
    return name


# ---------------------------------------------------------------- история
def load_hist():
    try:
        return json.load(open(J.ISTORIA))
    except (OSError, ValueError):
        return []


def save_hist(h):
    os.makedirs(os.path.dirname(J.ISTORIA), exist_ok=True)
    tmp = J.ISTORIA + ".tmp"
    json.dump(h, open(tmp, "w"), ensure_ascii=False, indent=1)
    os.replace(tmp, J.ISTORIA)


def first_backup(h):
    """При първото пускане пази как е било всичко ПРЕДИ програмата (за „Върни както беше“)."""
    if h:
        return
    os.makedirs(BACKUPS, exist_ok=True)
    d = os.path.join(BACKUPS, "predi")
    os.makedirs(d, exist_ok=True)
    if os.path.exists(J.DROPIN):
        shutil.copy2(J.DROPIN, os.path.join(d, os.path.basename(J.DROPIN)))
    h.append({"koga": time.strftime("%F %T"), "vid": "predi", "tema": cur_theme(), "dropin": os.path.exists(J.DROPIN),
              "fon": os.path.exists(J.ROOT + BG_FINAL)})
    say("Пазя как е било преди програмата: " + d)


# ---------------------------------------------------------------- прилагане
def apply(a):
    h = load_hist()
    first_backup(h)
    entry = {"koga": time.strftime("%F %T"), "vid": "promyana", "teme_novi": []}
    initramfs = grub = False

    if "--nova-tema" in a:
        name = install_theme(*a["--nova-tema"])
        entry["teme_novi"].append(name)
        if cur_theme() == name:
            initramfs = True
    if "--tema" in a:
        old = cur_theme()
        if a["--tema"] != old:
            entry["tema_predi"] = old
            say(f"Анимация: {old or '—'} → {a['--tema']}")
            if set_theme(a["--tema"]) != 0:
                die("plymouth-set-default-theme не успя")
            initramfs = True
        elif entry["teme_novi"] and a["--tema"] in entry["teme_novi"]:
            initramfs = True

    if any(k.startswith("--grub") for k in a) or "--rezhim" in a or "--nvidia" in a:
        base = J.read_grub(include_ours=False)
        now = J.read_grub(include_ours=True)
        mode = a.get("--rezhim") or J.detect_mode(now.get("GRUB_CMDLINE_LINUX_DEFAULT", ""))
        cmdline = J.build_cmdline(base.get("GRUB_CMDLINE_LINUX_DEFAULT", ""), mode)
        if "--nvidia" in a and "nvidia-drm.modeset=1" not in cmdline.split():
            cmdline += " nvidia-drm.modeset=1"
        gp = J.grub_from_settings(now)
        if "--grub-vreme" in a: gp.timeout = int(a["--grub-vreme"])
        if "--grub-stil" in a: gp.style = a["--grub-stil"]
        if "--grub-gfx" in a: gp.gfx = a["--grub-gfx"]
        if "--grub-pomni" in a: gp.remember = a["--grub-pomni"] == "1"
        bg_final = None
        if "--grub-fon" in a:
            if a["--grub-fon"] == "-":
                gp.background = ""
                if os.path.exists(J.ROOT + BG_FINAL):
                    os.remove(J.ROOT + BG_FINAL)
            else:
                src = a["--grub-fon"]
                if os.path.islink(src) or not png_ok(src, 4096) or os.path.getsize(src) > 20 * 1048576:
                    die("фонът на GRUB трябва да е PNG до 4096 px и 20 MB")
                os.makedirs(os.path.dirname(J.ROOT + BG_FINAL), exist_ok=True)
                shutil.copyfile(src, J.ROOT + BG_FINAL)
                os.chmod(J.ROOT + BG_FINAL, 0o644)
                bg_final = BG_FINAL
        elif os.path.exists(J.ROOT + BG_FINAL) and gp.background == "keep":
            bg_final = BG_FINAL
        if now.get("GRUB_THEME") and bg_final:
            say("Внимание: в GRUB има тема (GRUB_THEME) и тя покрива фона.")
        txt = J.dropin_text(cmdline, gp, bg_final)
        old_txt = open(J.DROPIN).read() if os.path.exists(J.DROPIN) else None
        if txt != old_txt:
            os.makedirs(J.GRUB_DIR, exist_ok=True)
            open(J.DROPIN + ".tmp", "w").write(txt)
            os.chmod(J.DROPIN + ".tmp", 0o644)
            os.replace(J.DROPIN + ".tmp", J.DROPIN)
            entry["dropin"] = True
            say("Записах " + J.DROPIN + ":\n" + "\n".join("  " + l for l in txt.splitlines() if not l.startswith("#")))
            grub = True
        else:
            say("GRUB: няма промяна.")

    if initramfs:
        say("Обновявам initramfs (анимацията се зарежда оттам). Това отнема минута-две…")
        if run(["update-initramfs", "-u", "-k", "all"]) != 0:
            die("update-initramfs не успя. Старото зареждане е непокътнато, анимацията просто няма да се смени.")
    if grub:
        say("Обновявам GRUB…")
        if run(["update-grub"]) != 0:
            die("update-grub не успя. Изтрий " + J.DROPIN + " и пусни update-grub, или натисни „Върни както беше“.")
    h.append(entry)
    save_hist(h)
    say("\nГотово. Промените се виждат при следващото рестартиране.")


def reset():
    h = load_hist()
    if not h:
        say("Програмата не е променяла нищо. Няма какво да връщам.")
        return
    predi = h[0]
    if os.path.exists(J.DROPIN):
        os.remove(J.DROPIN)
        say("Махнах " + J.DROPIN)
    keep = os.path.join(BACKUPS, "predi", os.path.basename(J.DROPIN))
    if predi.get("dropin") and os.path.exists(keep):
        shutil.copy2(keep, J.DROPIN)
        say("Върнах стария " + J.DROPIN)
    if not predi.get("fon") and os.path.exists(J.ROOT + BG_FINAL):
        os.remove(J.ROOT + BG_FINAL)
    tema = predi.get("tema") or ""
    if tema and tema != cur_theme() and os.path.exists(f"{J.THEMES}/{tema}/{tema}.plymouth"):
        say(f"Анимация: връщам {tema}")
        set_theme(tema)
    for d in glob.glob(J.THEMES + "/" + J.PREFIX + "*"):
        if os.path.basename(d) != tema and os.path.isdir(d) and not os.path.islink(d):
            shutil.rmtree(d)
            say("Махнах темата " + os.path.basename(d))
    run(["update-initramfs", "-u", "-k", "all"])
    run(["update-grub"])
    os.makedirs(BACKUPS, exist_ok=True)
    os.replace(J.ISTORIA, os.path.join(BACKUPS, f"istoria-{time.strftime('%Y%m%d-%H%M%S')}.json"))
    say("\nВсичко е както преди програмата. Вижда се при следващото рестартиране.")


def main():
    if os.geteuid() != 0 and not TEST:
        die("пуска се като root (през pkexec от програмата)")
    a = args(sys.argv[1:])
    if a.get("--varni"):
        reset()
    else:
        apply(a)


if __name__ == "__main__":
    main()
