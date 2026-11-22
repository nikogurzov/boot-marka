#!/usr/bin/env python3
"""Зареждане (boot-marka): анимация при зареждане (Plymouth), тих старт без текст по екрана и GRUB — с картинки, не с файлове.
   boot-marka              прозорец
   boot-marka --text       как е настроено сега (само чете)
   boot-marka --reset      връща всичко както е било преди програмата
Нищо не се променя, докато не натиснеш „Приложи“ и не въведеш паролата (pkexec). Основният /etc/default/grub не се пипа."""
import os
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import jezgro as J

HELPER = os.path.join(HERE, "prilozhi.py")
STYLES = [("hidden", "Скрито (влиза направо)"), ("countdown", "Обратно броене"), ("menu", "Меню")]
GFXS = ["auto", "1920x1080", "1366x768", "1280x720", "1600x900", "2560x1440"]


def main_text():
    print(J.as_text(J.collect()), end="")


def main_reset():
    if not J.history():
        print("Програмата не е променяла нищо. Няма какво да връщам.")
        return
    if input("Да върна ли зареждането както беше преди програмата? [д/Н] ").strip().lower() in ("д", "да", "y", "yes"):
        sys.exit(subprocess.run(J.reset_command(HELPER)).returncode)


def main_gui():
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        gi.require_version("Gdk", "4.0")
        from gi.repository import Adw, Gdk, Gio, GLib, Gtk
    except (ImportError, ValueError):
        print("Липсва GTK 4 / libadwaita за прозореца:\n  sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1\n")
        main_text()
        return

    CSS = b"""
    .card-tema { border-radius: 14px; padding: 8px; }
    .card-tema.izbrana { box-shadow: 0 0 0 3px @accent_bg_color; }
    .ekran { background: #0b0d12; border-radius: 10px; }
    .tema-ime { font-weight: bold; }
    .sega { background: alpha(@success_color, .18); color: @success_color; border-radius: 99px; padding: 1px 8px; font-size: 85%; font-weight: bold; }
    .nova { background: alpha(@accent_bg_color, .18); color: @accent_color; border-radius: 99px; padding: 1px 8px; font-size: 85%; font-weight: bold; }
    .red-iadro { font-family: monospace; font-size: 92%; padding: 10px 12px; border-radius: 8px; background: alpha(currentColor, .06); }
    .log { font-family: monospace; font-size: 90%; }
    .plus { font-size: 34pt; opacity: .7; }
    """

    def tex(path):
        try:
            return Gdk.Texture.new_from_filename(path)
        except GLib.Error:
            return None

    from gi.repository import GdkPixbuf

    def pix(path, w, h):
        try:
            return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, w, h, True)
        except GLib.Error:
            return None

    class Ekran(Gtk.DrawingArea):
        """Малък „екран“ с точен размер: цвят на фона, картинка за фон и анимираните кадри в средата (рисува се с cairo)."""
        def __init__(self, w=220, h=132, note="", plus=False):
            super().__init__(content_width=w, content_height=h, halign=Gtk.Align.CENTER)
            self.W, self.H, self.note, self.plus = w, h, note, plus
            self.rgb = (11, 13, 18)
            self.bgp, self.frames, self.i = None, [], 0
            self.set_draw_func(self.draw)

        def set_color(self, rgb):
            self.rgb = tuple(rgb)
            self.queue_draw()

        def load(self, frames, background=""):
            step = max(1, len(frames) // 40)
            fw, fh = int(self.W * 0.62), int(self.H * 0.6)
            self.frames = [p for p in (pix(f, fw, fh) for f in frames[::step]) if p]
            self.i = 0
            name = os.path.basename(background or "").lower()
            if background and "background" in name:
                try:
                    self.bgp = GdkPixbuf.Pixbuf.new_from_file(background)
                except GLib.Error:
                    self.bgp = None
            elif background and not self.frames:
                self.frames = [p for p in [pix(background, fw, fh)] if p]
            self.queue_draw()

        def tick(self):
            if len(self.frames) > 1 and self.get_mapped():
                self.i = (self.i + 1) % len(self.frames)
                self.queue_draw()

        def draw(self, area, cr, w, h):
            import math
            r = 10
            cr.new_sub_path()
            cr.arc(w - r, r, r, -math.pi / 2, 0); cr.arc(w - r, h - r, r, 0, math.pi / 2)
            cr.arc(r, h - r, r, math.pi / 2, math.pi); cr.arc(r, r, r, math.pi, 3 * math.pi / 2)
            cr.close_path(); cr.clip()
            cr.set_source_rgb(*(c / 255 for c in self.rgb)); cr.paint()
            if self.bgp:
                k = max(w / self.bgp.get_width(), h / self.bgp.get_height())
                cr.save(); cr.translate((w - self.bgp.get_width() * k) / 2, (h - self.bgp.get_height() * k) / 2); cr.scale(k, k)
                Gdk.cairo_set_source_pixbuf(cr, self.bgp, 0, 0); cr.paint(); cr.restore()
            if self.frames:
                p = self.frames[self.i % len(self.frames)]
                Gdk.cairo_set_source_pixbuf(cr, p, (w - p.get_width()) / 2, (h - p.get_height()) / 2); cr.paint()
            cr.set_source_rgba(1, 1, 1, .8)
            if self.plus:
                cr.set_font_size(54); ext = cr.text_extents("+")
                cr.move_to((w - ext.width) / 2 - ext.x_bearing, (h - ext.height) / 2 - ext.y_bearing); cr.show_text("+")
            if self.note:
                cr.set_source_rgba(1, 1, 1, .55); cr.set_font_size(11); ext = cr.text_extents(self.note)
                cr.move_to((w - ext.width) / 2, h - 10); cr.show_text(self.note)

    class LogWin(Adw.Window):
        def __init__(self, parent, cmd, title, on_done):
            super().__init__(transient_for=parent, modal=True, title=title, default_width=720, default_height=520)
            tv = Adw.ToolbarView()
            tv.add_top_bar(Adw.HeaderBar())
            self.buf = Gtk.TextBuffer()
            self.view = Gtk.TextView(buffer=self.buf, editable=False, monospace=True, css_classes=["log"],
                                     wrap_mode=Gtk.WrapMode.WORD_CHAR, top_margin=10, left_margin=10, right_margin=10)
            tv.set_content(Gtk.ScrolledWindow(child=self.view, vexpand=True))
            self.close_b = Gtk.Button(label="Затвори", sensitive=False, halign=Gtk.Align.END, margin_end=12, margin_bottom=12, margin_top=6)
            self.close_b.connect("clicked", lambda *_: self.close())
            tv.add_bottom_bar(self.close_b)
            self.set_content(tv)
            self.connect("close-request", lambda *_: (on_done(), False)[1])

            def work():
                try:
                    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace", bufsize=1)
                    for line in p.stdout:
                        GLib.idle_add(self.add, line)
                    code = p.wait()
                except OSError as e:
                    GLib.idle_add(self.add, f"{e}\n")
                    code = 1
                msg = {0: "", 126: "\nОтказано: паролата не беше въведена.\n", 127: "\nОтказано: паролата не беше въведена.\n"}.get(
                    code, f"\nСпря с грешка (код {code}). Старите настройки са непокътнати или се връщат с „↶ Върни както беше“.\n")
                GLib.idle_add(self.add, msg)
                GLib.idle_add(self.close_b.set_sensitive, True)
            threading.Thread(target=work, daemon=True).start()

        def add(self, s):
            self.buf.insert(self.buf.get_end_iter(), s)
            self.view.scroll_to_mark(self.buf.get_insert(), 0, False, 0, 1)
            return False

    class CustomDlg(Adw.Window):
        """„Моя анимация“: GIF, видео или картинка -> тема за Plymouth (готовите файлове са в /tmp, root не трябва)."""
        def __init__(self, parent, on_ok):
            super().__init__(transient_for=parent, modal=True, title="Моя анимация", default_width=620, default_height=720)
            self.on_ok, self.src, self.result = on_ok, "", None
            tv = Adw.ToolbarView()
            hb = Adw.HeaderBar()
            self.ok = Gtk.Button(label="Добави", css_classes=["suggested-action"], sensitive=False)
            self.ok.connect("clicked", self.add)
            hb.pack_end(self.ok)
            tv.add_top_bar(hb)
            page = Adw.PreferencesPage()
            self.ekran = Ekran(520, 292)
            g0 = Adw.PreferencesGroup(title="Как ще изглежда", description="Избери файл. Прегледът се прави на компютъра ти, нищо не се пипа.")
            g0.add(self.ekran)
            self.status = Gtk.Label(xalign=0, wrap=True, css_classes=["dim-label"], margin_top=6)
            g0.add(self.status)
            page.add(g0)
            g = Adw.PreferencesGroup(title="Анимация")
            self.file_row = Adw.ActionRow(title="Файл", subtitle="GIF, видео (MP4, WebM) или картинка/лого (PNG, JPG)")
            b = Gtk.Button(label="Избери…", valign=Gtk.Align.CENTER)
            b.connect("clicked", self.pick)
            self.file_row.add_suffix(b)
            g.add(self.file_row)
            self.title = Adw.EntryRow(title="Име на темата", text="Моята анимация")
            g.add(self.title)
            self.label = Adw.EntryRow(title="Надпис под анимацията (по желание)", text="")
            g.add(self.label)
            cr = Adw.ActionRow(title="Цвят на фона")
            self.color = Gtk.ColorDialogButton(dialog=Gtk.ColorDialog(), valign=Gtk.Align.CENTER)
            c = Gdk.RGBA(); c.parse("#000000"); self.color.set_rgba(c)
            cr.add_suffix(self.color)
            g.add(cr)
            self.size = Adw.SpinRow.new_with_range(10, 70, 5); self.size.set_title("Големина, % от екрана"); self.size.set_value(30)
            g.add(self.size)
            self.fps = Adw.SpinRow.new_with_range(5, 30, 1); self.fps.set_title("Скорост, кадъра в секунда"); self.fps.set_value(20)
            g.add(self.fps)
            self.ind = Adw.ComboRow(title="Отдолу", subtitle="Повтарящите се не зависят от това колко бързо зарежда компютърът",
                                    model=Gtk.StringList.new([x[1] for x in J.INDIKATORI]))
            g.add(self.ind)
            page.add(g)
            g2 = Adw.PreferencesGroup()
            self.make_b = Gtk.Button(label="Направи прегледа", css_classes=["pill"], halign=Gtk.Align.CENTER, sensitive=False)
            self.make_b.connect("clicked", self.make)
            g2.add(self.make_b)
            page.add(g2)
            tv.set_content(page)
            self.set_content(tv)
            self.timer = GLib.timeout_add(1000 // 20, lambda: (self.ekran.tick(), True)[1])
            self.connect("close-request", lambda *_: (GLib.source_remove(self.timer), False)[1])

        def pick(self, *_):
            d = Gtk.FileDialog(title="Избери анимация")
            f = Gtk.FileFilter(); f.set_name("Анимации и картинки")
            for p in ("*.gif", "*.mp4", "*.webm", "*.mkv", "*.mov", "*.png", "*.jpg", "*.jpeg", "*.webp", "*.GIF", "*.MP4", "*.PNG", "*.JPG"):
                f.add_pattern(p)
            fl = Gio.ListStore.new(Gtk.FileFilter); fl.append(f)
            d.set_filters(fl)

            def done(dd, res):
                try:
                    gf = dd.open_finish(res)
                except GLib.Error:
                    return
                self.src = gf.get_path()
                self.file_row.set_subtitle(os.path.basename(self.src))
                try:                                   # цветът на фона: от ъгъла на първия кадър, за да се слее с екрана
                    from PIL import Image
                    px = Image.open(self.src).convert("RGB").getpixel((2, 2))
                    c = Gdk.RGBA(); c.parse("#%02x%02x%02x" % px); self.color.set_rgba(c)
                except Exception:
                    pass
                base = os.path.splitext(os.path.basename(self.src))[0]
                if self.title.get_text() in ("", "Моята анимация"):
                    self.title.set_text(base[:30])
                self.make_b.set_sensitive(True)
                self.make()
            d.open(self.get_root(), None, done)

        def custom(self):
            c = self.color.get_rgba()
            return J.Custom(title=self.title.get_text().strip() or "Моята анимация", src=self.src,
                            bg=(int(c.red * 255), int(c.green * 255), int(c.blue * 255)), scale=self.size.get_value() / 100,
                            fps=self.fps.get_value(), label=self.label.get_text(), indicator=J.INDIKATORI[self.ind.get_selected()][0])

        def make(self, *_):
            if not self.src:
                return
            c = self.custom()
            self.make_b.set_sensitive(False); self.ok.set_sensitive(False)
            self.status.set_label("Правя кадрите…")

            def work():
                try:
                    res = J.make_custom(c, log=lambda s: None)
                    GLib.idle_add(self.made, c, res, None)
                except Exception as e:      # ffmpeg/PIL: показваме грешката в прозореца
                    GLib.idle_add(self.made, c, None, str(e))
            threading.Thread(target=work, daemon=True).start()

        def made(self, c, res, err):
            self.make_b.set_sensitive(True)
            if err:
                self.status.set_label("⚠ " + err)
                return False
            d, slug, n, size = res
            self.result = (d, slug, c)
            import glob as _g
            self.ekran.set_color(c.bg)
            self.ekran.load(sorted(_g.glob(d + "/frame-*.png"), key=J._num))
            self.status.set_label(f"{n} кадъра, {size // 1024} KB. Темата ще се казва „boot-marka-{slug}“."
                                  + (" Внимание: голяма е, зареждането може да стане по-бавно." if size > 15 * 1048576 else ""))
            self.ok.set_sensitive(True)
            return False

        def add(self, *_):
            if self.result:
                self.on_ok(*self.result)
            self.close()

    class Win(Adw.ApplicationWindow):
        def __init__(self, app):
            super().__init__(application=app, title="Зареждане (boot-marka)", default_width=980, default_height=760)
            self.toasts = Adw.ToastOverlay()
            tv = Adw.ToolbarView()
            hb = Adw.HeaderBar()
            self.stack = Adw.ViewStack()
            sw = Adw.ViewSwitcher(stack=self.stack, policy=Adw.ViewSwitcherPolicy.WIDE)
            hb.set_title_widget(sw)
            self.apply_b = Gtk.Button(label="Приложи", css_classes=["suggested-action"], sensitive=False,
                                      tooltip_text="Записва избраното. Ще поиска паролата ти.")
            self.apply_b.connect("clicked", self.apply)
            hb.pack_end(self.apply_b)
            self.undo_b = Gtk.Button(icon_name="edit-undo-symbolic", tooltip_text="↶ Върни както беше преди програмата")
            self.undo_b.connect("clicked", self.undo)
            hb.pack_start(self.undo_b)
            tv.add_top_bar(hb)
            self.summary = Gtk.Label(xalign=0, wrap=True, css_classes=["dim-label"], margin_start=16, margin_end=16, margin_top=6, margin_bottom=8)
            tv.add_bottom_bar(self.summary)
            self.toasts.set_child(self.stack)
            tv.set_content(self.toasts)
            self.set_content(tv)
            self.ekrani = []
            GLib.timeout_add(1000 // 12, self.tick)
            self.load()

        def tick(self):
            for e in self.ekrani:
                e.tick()
            return True

        # ---------------------------------------------------------------- данни
        def load(self):
            self.s = J.collect()
            self.sel_theme = self.s.theme
            self.sel_mode = self.s.mode
            self.gp = J.GrubPlan(**vars(self.s.plan))
            self.bg_src, self.new_theme, self.nvidia = None, None, False
            for name in ("anim", "tekst", "grub"):
                ch = self.stack.get_child_by_name(name)
                if ch:
                    self.stack.remove(ch)
            self.ekrani = []
            self.stack.add_titled_with_icon(self.page_anim(), "anim", "Анимация", "applications-graphics-symbolic")
            self.stack.add_titled_with_icon(self.page_tekst(), "tekst", "Текст при зареждане", "utilities-terminal-symbolic")
            self.stack.add_titled_with_icon(self.page_grub(), "grub", "GRUB", "system-run-symbolic")
            self.undo_b.set_sensitive(bool(J.history()))
            self.changed()

        def changed(self, *_):
            ch = []
            if self.new_theme:
                ch.append(f"нова тема „{self.new_theme[2].title}“")
            if self.sel_theme != self.s.theme:
                ch.append(f"анимация: {self.s.theme or '—'} → {self.sel_theme}")
            if self.sel_mode != self.s.mode:
                ch.append(f"текст: {J.MODES[self.s.mode][0]} → {J.MODES[self.sel_mode][0]}")
            if self.grub_changed():
                ch.append("GRUB")
            if self.nvidia:
                ch.append("поправка за NVIDIA")
            self.apply_b.set_sensitive(bool(ch))
            self.summary.set_label(("Ще се промени: " + "; ".join(ch) + ". Вижда се при следващото рестартиране.") if ch else
                                   "Избери как да изглежда зареждането и натисни „Приложи“. Нищо не се записва преди това.")
            if hasattr(self, "line_l"):
                self.line_l.set_label(J.build_cmdline(self.s.grub_base.get("GRUB_CMDLINE_LINUX_DEFAULT", ""), self.sel_mode)
                                      + (" nvidia-drm.modeset=1" if self.nvidia else ""))

        def grub_changed(self):
            p = self.s.plan
            return (self.gp.timeout, self.gp.style, self.gp.remember, self.gp.gfx) != (p.timeout, p.style, p.remember, p.gfx) \
                or bool(self.bg_src) or self.gp.background == ""

        # ---------------------------------------------------------------- страница „Анимация“
        def page_anim(self):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=12, margin_bottom=12, margin_start=16, margin_end=16)
            if self.s.nvidia:
                box.append(Adw.Banner(title=self.s.nvidia, revealed=True))
            box.append(Gtk.Label(label="Избери анимацията, която се вижда, докато Linux зарежда. Миниатюрите са живи.", xalign=0, wrap=True, css_classes=["dim-label"]))
            self.flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, homogeneous=True, max_children_per_line=8, min_children_per_line=1,
                                    row_spacing=12, column_spacing=12, valign=Gtk.Align.START)
            self.cards = {}
            plus = Gtk.Button(css_classes=["card", "card-tema"], tooltip_text="Направи тема от свой GIF, видео или лого")
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            e = Ekran(plus=True)
            v.append(e)
            v.append(Gtk.Label(label="Моя анимация", css_classes=["tema-ime"]))
            v.append(Gtk.Label(label="от GIF, видео или лого", css_classes=["dim-label", "caption"]))
            plus.set_child(v)
            plus.connect("clicked", lambda *_: CustomDlg(self, self.custom_added).present())
            self.flow.append(plus)
            for t in self.s.themes:
                self.flow.append(self.card(t))
            box.append(Gtk.ScrolledWindow(child=self.flow, vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER))
            return box

        def card(self, t, new=False):
            b = Gtk.Button(css_classes=["card", "card-tema"])
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            e = Ekran(note="логото на производителя" if t.name == "bgrt" else "")
            if t.ours or new:
                e.set_color(t.bg_color)
            e.load(t.frames, t.background)
            self.ekrani.append(e)
            v.append(e)
            h = Gtk.Box(spacing=6, halign=Gtk.Align.CENTER)
            nice = t.title if t.ours else t.name.replace("-", " ").replace("_", " ").title()
            h.append(Gtk.Label(label=nice + (" (само текст)" if t.name in J.SKIP else ""), css_classes=["tema-ime"], ellipsize=3, max_width_chars=20))
            if t.name == self.s.theme:
                h.append(Gtk.Label(label="сега", css_classes=["sega"]))
            if new:
                h.append(Gtk.Label(label="нова", css_classes=["nova"]))
            v.append(h)
            v.append(Gtk.Label(label=(t.name if t.ours else t.title), css_classes=["dim-label", "caption"], ellipsize=3, max_width_chars=30,
                               tooltip_text=f"{t.title}\n{t.name}"))
            b.set_child(v)
            b.connect("clicked", lambda *_: self.pick_theme(t.name))
            self.cards[t.name] = b
            if t.name == self.sel_theme:
                b.add_css_class("izbrana")
            return b

        def pick_theme(self, name):
            self.sel_theme = name
            for n, b in self.cards.items():
                (b.add_css_class if n == name else b.remove_css_class)("izbrana")
            if self.sel_mode == "podroben" and name not in J.SKIP:
                self.toasts.add_toast(Adw.Toast(title="Анимацията се вижда само в режим „Тих“ или „Нормален“ (страница „Текст при зареждане“)."))
            self.changed()

        def custom_added(self, d, slug, c):
            import glob as _g
            name = J.PREFIX + slug
            self.new_theme = (d, slug, c)
            t = J.Theme(name=name, title=c.title, module="script", path=d, ours=True,
                        frames=sorted(_g.glob(d + "/frame-*.png"), key=J._num), bg_color=c.bg)
            if name in self.cards:
                self.flow.remove(self.cards[name].get_parent())
            self.flow.insert(self.card(t, new=True), 1)
            self.pick_theme(name)
            if self.sel_mode == "podroben":
                self.mode_checks["tih"].set_active(True)

        # ---------------------------------------------------------------- страница „Текст при зареждане“
        def page_tekst(self):
            page = Adw.PreferencesPage()
            g = Adw.PreferencesGroup(title="Какво се вижда, докато Linux зарежда",
                                     description="Сега е: " + J.MODES[self.s.mode][0] + ". Основният файл на GRUB не се пипа.")
            self.mode_checks, first = {}, None
            for key, (title, sub, _) in J.MODES.items():
                r = Adw.ActionRow(title=title, subtitle=sub)
                c = Gtk.CheckButton(active=key == self.sel_mode, valign=Gtk.Align.CENTER)
                if first:
                    c.set_group(first)
                first = first or c
                c.connect("toggled", lambda cb, k=key: cb.get_active() and self.set_mode(k))
                r.add_prefix(c)
                r.set_activatable_widget(c)
                g.add(r)
                self.mode_checks[key] = c
            page.add(g)
            if self.s.nvidia:
                g2 = Adw.PreferencesGroup(title="NVIDIA")
                sw = Adw.SwitchRow(title="Поправка за NVIDIA", subtitle="Добавя nvidia-drm.modeset=1, за да се вижда анимацията")
                sw.connect("notify::active", lambda r, *_: (setattr(self, "nvidia", r.get_active()), self.changed()))
                g2.add(sw)
                page.add(g2)
            g3 = Adw.PreferencesGroup(title="Редът на ядрото след „Приложи“",
                                      description="Нашите настройки се сменят, всичко друго (напр. за видеокартата) остава.")
            self.line_l = Gtk.Label(xalign=0, wrap=True, selectable=True, css_classes=["red-iadro"])
            g3.add(self.line_l)
            if self.s.crypt:
                g3.add(Gtk.Label(label="Дискът е криптиран: паролата се пита върху анимацията.", xalign=0, css_classes=["dim-label"], margin_top=6))
            page.add(g3)
            return page

        def set_mode(self, k):
            self.sel_mode = k
            self.changed()

        # ---------------------------------------------------------------- страница „GRUB“
        def page_grub(self):
            page = Adw.PreferencesPage()
            g = Adw.PreferencesGroup(title="Менюто при включване (GRUB)")
            st = Adw.ComboRow(title="Меню", model=Gtk.StringList.new([s[1] for s in STYLES]))
            st.set_selected([s[0] for s in STYLES].index(self.gp.style))
            st.connect("notify::selected", lambda r, *_: (setattr(self.gp, "style", STYLES[r.get_selected()][0]), self.changed()))
            g.add(st)
            to = Adw.SpinRow.new_with_range(0, 30, 1)
            to.set_title("Колко секунди да чака")
            to.set_subtitle("0 = направо, без чакане")
            to.set_value(self.gp.timeout)
            to.connect("notify::value", lambda r, *_: (setattr(self.gp, "timeout", int(r.get_value())), self.changed()))
            g.add(to)
            rem = Adw.SwitchRow(title="Помни последния избор", subtitle="Ако имаш и друга система (напр. Windows), стартира последно избраната", active=self.gp.remember)
            rem.connect("notify::active", lambda r, *_: (setattr(self.gp, "remember", r.get_active()), self.changed()))
            g.add(rem)
            gfx = Adw.ComboRow(title="Разделителна способност на менюто", model=Gtk.StringList.new(["автоматично" if x == "auto" else x for x in GFXS]))
            gfx.set_selected(GFXS.index(self.gp.gfx) if self.gp.gfx in GFXS else 0)
            gfx.connect("notify::selected", lambda r, *_: (setattr(self.gp, "gfx", GFXS[r.get_selected()]), self.changed()))
            g.add(gfx)
            page.add(g)
            g2 = Adw.PreferencesGroup(title="Фон на менюто",
                                      description=("⚠ В GRUB има тема (GRUB_THEME) и тя покрива фона." if self.s.grub.get("GRUB_THEME") else
                                                   "Картинка зад менюто на GRUB. Вижда се, ако менюто не е скрито."))
            self.bg_row = Adw.ActionRow(title="Картинка", subtitle=os.path.basename(self.s.grub.get("GRUB_BACKGROUND", "")) or "няма")
            pick = Gtk.Button(label="Избери…", valign=Gtk.Align.CENTER)
            pick.connect("clicked", self.pick_bg)
            rm = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER, tooltip_text="Без картинка")
            rm.connect("clicked", self.no_bg)
            self.bg_row.add_suffix(pick)
            self.bg_row.add_suffix(rm)
            g2.add(self.bg_row)
            page.add(g2)
            return page

        def pick_bg(self, *_):
            d = Gtk.FileDialog(title="Картинка за фона на GRUB")
            f = Gtk.FileFilter(); f.set_name("Картинки"); f.add_mime_type("image/*")
            fl = Gio.ListStore.new(Gtk.FileFilter); fl.append(f); d.set_filters(fl)

            def done(dd, res):
                try:
                    path = dd.open_finish(res).get_path()
                    from PIL import Image
                    im = Image.open(path).convert("RGB")
                    im.thumbnail((1920, 1080))
                    out = os.path.join(tempfile.mkdtemp(prefix="boot-marka-fon-"), "fon.png")
                    im.save(out)
                except Exception as e:
                    self.toasts.add_toast(Adw.Toast(title=f"Не мога да отворя картинката: {e}"))
                    return
                self.bg_src, self.gp.background = out, out
                self.bg_row.set_subtitle(os.path.basename(path))
                self.changed()
            d.open(self, None, done)

        def no_bg(self, *_):
            self.bg_src, self.gp.background = None, ""
            self.bg_row.set_subtitle("няма (ще се махне)")
            self.changed()

        # ---------------------------------------------------------------- прилагане
        def apply(self, *_):
            nt = self.new_theme
            theme = self.sel_theme if (self.sel_theme != self.s.theme or (nt and self.sel_theme == J.PREFIX + nt[1])) else None
            mode = self.sel_mode if self.sel_mode != self.s.mode else None
            gp = self.gp if (self.grub_changed() or mode or self.nvidia) else None
            cmd = J.apply_command(HELPER, theme=theme, mode=mode, gp=gp, bg_src=self.bg_src,
                                  new_theme_dir=nt[0] if nt else None, new_slug=nt[1] if nt else None, nvidia=self.nvidia)
            LogWin(self, cmd, "Прилагам", self.load).present()

        def undo(self, *_):
            d = Adw.AlertDialog(heading="Да върна ли всичко както беше?",
                                body="Маха настройките и темите, сложени от програмата, и връща старата анимация. Ще поиска паролата ти.")
            d.add_response("ne", "Не")
            d.add_response("da", "Върни")
            d.set_response_appearance("da", Adw.ResponseAppearance.DESTRUCTIVE)
            d.connect("response", lambda _d, r: r == "da" and LogWin(self, J.reset_command(HELPER), "Връщам както беше", self.load).present())
            d.present(self)

    class App(Adw.Application):
        def __init__(self):
            super().__init__(application_id="com.palamarka.bootmarka", flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

        def do_activate(self):
            p = Gtk.CssProvider()
            p.load_from_data(CSS)
            Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            w = self.props.active_window or Win(self)
            w.present()
            if SNIMKA:                     # --snimka папка: снима трите страници и излиза (за README и проверка)
                def snap(names=["anim", "tekst", "grub"]):
                    if not names:
                        self.quit(); return False
                    n = names.pop(0)
                    w.stack.set_visible_child_name(n)

                    def save():
                        pt = Gtk.WidgetPaintable.new(w)
                        wd, ht = w.get_width(), w.get_height()
                        snap_ = Gtk.Snapshot(); pt.snapshot(snap_, wd, ht)
                        node = snap_.to_node()
                        if node:
                            tx = w.get_renderer().render_texture(node, None)
                            tx.save_to_png(os.path.join(SNIMKA, f"{n}.png"))
                        GLib.timeout_add(300, snap, names)
                        return False
                    GLib.timeout_add(1500, save)
                    return False
                GLib.timeout_add(1500, snap)

    App().run([sys.argv[0]])


SNIMKA = sys.argv[sys.argv.index("--snimka") + 1] if "--snimka" in sys.argv else None

if __name__ == "__main__":
    if "--text" in sys.argv:
        main_text()
    elif "--reset" in sys.argv:
        main_reset()
    else:
        main_gui()
