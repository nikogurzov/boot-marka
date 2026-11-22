"""Език на boot-marka: български, ако системата е на български, иначе английски.
   BOOT_MARKA_EZIK=bg|en го задава ръчно. _("текст") превежда; шаблоните с {} хващат и f-низовете."""
import os
import re

_EZIK = [None]


def ezik():
    if _EZIK[0] is None:
        e = os.environ.get("BOOT_MARKA_EZIK", "")
        if not e:
            loc = os.environ.get("LANGUAGE") or os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or ""
            e = "bg" if loc.lower().startswith("bg") else "en"
        _EZIK[0] = "bg" if e.startswith("bg") else "en"
    return _EZIK[0]


def set_ezik(e):
    _EZIK[0] = "bg" if e.startswith("bg") else "en"


EN = {
    # --- режими и варианти (jezgro)
    "Тих": "Quiet",
    "Само анимацията. Без съобщения на ядрото и без мигащ курсор. Esc ги показва, ако потрябват.":
        "Only the animation. No kernel messages and no blinking cursor. Press Esc to see them if needed.",
    "Нормален": "Normal",
    "Анимация, но важните съобщения на системата може да се мярнат.": "Animation, but important system messages may flash by.",
    "Подробен": "Verbose",
    "Без анимация, всичко се изписва. За когато нещо не тръгва.": "No animation, everything is printed. For when something won't start.",
    "Видеокартата NVIDIA е без „modeset“. Ако екранът е вързан към нея, анимацията може да не се покаже. Отметни „Поправка за NVIDIA“, за да добавя nvidia-drm.modeset=1.":
        "The NVIDIA card runs without “modeset”. If the screen is connected to it, the animation may not show. Tick “NVIDIA fix” to add nvidia-drm.modeset=1.",
    "Трикольор: една лента блещука отляво надясно, с искра": "Tricolor: one bar shimmers left to right, with a spark",
    "Знаме: три ивици се пълнят на място, с искри": "Flag: three stripes fill in place, with sparks",
    "Бягаща светлинка (повтаря се)": "Running light (loops)",
    "Три пулсиращи точки": "Three pulsing dots",
    "Надпис „Зареждане…“, който свети и угасва": "“Loading…” text that glows and fades",
    "Лента за напредъка (може да не стигне до края)": "Progress bar (may not reach the end)",
    "Нищо": "Nothing",
    "Правя кадрите…": "Making the frames…",
    "Не можах да извадя кадри от файла. ": "Could not extract frames from the file. ",
    "Зареждане…": "Loading…",
    "Анимация (Plymouth): {}": "Animation (Plymouth): {}",
    "Текст при зареждане: {}": "Boot text: {}",
    "GRUB: {} с, меню: {}, помни последния избор: {}, разделителна способност: {}":
        "GRUB: {} s, menu: {}, remember last choice: {}, resolution: {}",
    "Ред на ядрото (настроен): {}": "Kernel command line (configured): {}",
    "Ред на ядрото (сега): {}": "Kernel command line (now): {}",
    "Настройки от boot-marka: {}": "Settings from boot-marka: {}",
    "Теми: ": "Themes: ",
    "да": "yes", "не": "no", "няма": "none",
    # --- помощникът (prilozhi)
    "ГРЕШКА: ": "ERROR: ",
    "непознат аргумент: {}": "unknown argument: {}",
    "неправилно име на тема": "invalid theme name",
    "неправилен режим": "invalid mode",
    "времето на GRUB трябва да е от 0 до 30 секунди": "GRUB timeout must be 0 to 30 seconds",
    "неправилен вид на менюто": "invalid menu style",
    "неправилна разделителна способност": "invalid resolution",
    "--grub-pomni е 0 или 1": "--grub-pomni is 0 or 1",
    "неправилно име на новата тема": "invalid name for the new theme",
    "няма такава тема: {}": "no such theme: {}",
    "папката с новата тема липсва": "the folder with the new theme is missing",
    "непознати файлове в темата: ": "unknown files in the theme: ",
    "липсва {}": "missing {}",
    "файловете на темата са за друго име": "the theme files are for another name",
    "файлът .plymouth не е направен от програмата": "the .plymouth file was not made by this program",
    "{} не е правилна PNG картинка": "{} is not a valid PNG image",
    "темата е твърде голяма ({} MB, най-много {} MB)": "the theme is too big ({} MB, at most {} MB)",
    "Темата е сложена: {} ({} файла, {} KB)": "Theme installed: {} ({} files, {} KB)",
    "Пазя как е било преди програмата: ": "Saving how things were before the program: ",
    "Анимация: {} → {}": "Animation: {} → {}",
    "plymouth-set-default-theme не успя": "plymouth-set-default-theme failed",
    "фонът на GRUB трябва да е PNG до 4096 px и 20 MB": "the GRUB background must be a PNG up to 4096 px and 20 MB",
    "Внимание: в GRUB има тема (GRUB_THEME) и тя покрива фона.": "Note: GRUB has a theme (GRUB_THEME) and it covers the background.",
    "Записах ": "Wrote ",
    "GRUB: няма промяна.": "GRUB: no change.",
    "Обновявам initramfs (анимацията се зарежда оттам). Това отнема минута-две…":
        "Updating initramfs (the animation loads from it). This takes a minute or two…",
    "update-initramfs не успя. Старото зареждане е непокътнато, анимацията просто няма да се смени.":
        "update-initramfs failed. The old boot is untouched; the animation simply won't change.",
    "Обновявам GRUB…": "Updating GRUB…",
    "update-grub не успя. Изтрий ": "update-grub failed. Delete ",
    " и пусни update-grub, или натисни „Върни както беше“.": " and run update-grub, or press “Undo everything”.",
    "\nГотово. Промените се виждат при следващото рестартиране.": "\nDone. You will see the changes on the next restart.",
    "Програмата не е променяла нищо. Няма какво да връщам.": "The program has not changed anything. Nothing to undo.",
    "Махнах ": "Removed ",
    "Върнах стария ": "Restored the old ",
    "Анимация: връщам {}": "Animation: restoring {}",
    "Махнах темата ": "Removed theme ",
    "\nВсичко е както преди програмата. Вижда се при следващото рестартиране.":
        "\nEverything is as it was before the program. You will see it on the next restart.",
    "пуска се като root (през pkexec от програмата)": "must run as root (through pkexec from the program)",
    # --- прозорецът (boot-marka.py)
    "Скрито (влиза направо)": "Hidden (boots straight in)",
    "Обратно броене": "Countdown",
    "Меню": "Menu",
    "Да върна ли зареждането както беше преди програмата? [д/Н] ": "Restore the boot as it was before the program? [y/N] ",
    "Липсва GTK 4 / libadwaita за прозореца:\n  sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1\n":
        "GTK 4 / libadwaita is missing for the window:\n  sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1\n",
    "Затвори": "Close",
    "\nОтказано: паролата не беше въведена.\n": "\nCancelled: the password was not entered.\n",
    "\nСпря с грешка (код {}). Старите настройки са непокътнати или се връщат с „↶ Върни както беше“.\n":
        "\nStopped with an error (code {}). The old settings are untouched or can be restored with “↶ Undo everything”.\n",
    "Моя анимация": "My animation",
    "Добави": "Add",
    "Как ще изглежда": "How it will look",
    "Избери файл. Прегледът се прави на компютъра ти, нищо не се пипа.": "Pick a file. The preview is made on your computer; nothing is changed.",
    "Анимация": "Animation",
    "Файл": "File",
    "GIF, видео (MP4, WebM) или картинка/лого (PNG, JPG)": "GIF, video (MP4, WebM) or picture/logo (PNG, JPG)",
    "Избери…": "Choose…",
    "Име на темата": "Theme name",
    "Моята анимация": "My animation",
    "Надпис под анимацията (по желание)": "Text under the animation (optional)",
    "Цвят на фона": "Background color",
    "Големина, % от екрана": "Size, % of the screen",
    "Скорост, кадъра в секунда": "Speed, frames per second",
    "Отдолу": "Below",
    "Повтарящите се не зависят от това колко бързо зарежда компютърът": "The looping ones don't depend on how fast the computer boots",
    "Направи прегледа": "Make the preview",
    "Избери анимация": "Choose an animation",
    "Анимации и картинки": "Animations and pictures",
    "{} кадъра, {} KB. Темата ще се казва „boot-marka-{}“.": "{} frames, {} KB. The theme will be called “boot-marka-{}”.",
    " Внимание: голяма е, зареждането може да стане по-бавно.": " Note: it is big; booting may get slower.",
    "Зареждане (boot-marka)": "Boot (boot-marka)",
    "Приложи": "Apply",
    "Записва избраното. Ще поиска паролата ти.": "Saves your choices. It will ask for your password.",
    "↶ Върни както беше преди програмата": "↶ Undo everything the program did",
    "Текст при зареждане": "Boot text",
    "нова тема „{}“": "new theme “{}”",
    "анимация: {} → {}": "animation: {} → {}",
    "текст: {} → {}": "text: {} → {}",
    "поправка за NVIDIA": "NVIDIA fix",
    "Ще се промени: ": "Will change: ",
    ". Вижда се при следващото рестартиране.": ". You will see it on the next restart.",
    "Избери как да изглежда зареждането и натисни „Приложи“. Нищо не се записва преди това.":
        "Choose how booting should look and press “Apply”. Nothing is saved before that.",
    "Избери анимацията, която се вижда, докато Linux зарежда. Миниатюрите са живи.":
        "Choose the animation you see while Linux boots. The thumbnails are live.",
    "Направи тема от свой GIF, видео или лого": "Make a theme from your own GIF, video or logo",
    "от GIF, видео или лого": "from a GIF, video or logo",
    "логото на производителя": "the manufacturer's logo",
    " (само текст)": " (text only)",
    "сега": "now",
    "нова": "new",
    "Анимацията се вижда само в режим „Тих“ или „Нормален“ (страница „Текст при зареждане“).":
        "The animation only shows in “Quiet” or “Normal” mode (the “Boot text” page).",
    "Какво се вижда, докато Linux зарежда": "What you see while Linux boots",
    "Сега е: ": "Now: ",
    ". Основният файл на GRUB не се пипа.": ". The main GRUB file is not touched.",
    "Поправка за NVIDIA": "NVIDIA fix",
    "Добавя nvidia-drm.modeset=1, за да се вижда анимацията": "Adds nvidia-drm.modeset=1 so the animation shows",
    "Редът на ядрото след „Приложи“": "The kernel command line after “Apply”",
    "Нашите настройки се сменят, всичко друго (напр. за видеокартата) остава.": "Only our settings change; everything else (e.g. for the graphics card) stays.",
    "Дискът е криптиран: паролата се пита върху анимацията.": "The disk is encrypted: the password is asked on top of the animation.",
    "Менюто при включване (GRUB)": "The boot menu (GRUB)",
    "Колко секунди да чака": "How many seconds to wait",
    "0 = направо, без чакане": "0 = straight in, no waiting",
    "Помни последния избор": "Remember the last choice",
    "Ако имаш и друга система (напр. Windows), стартира последно избраната": "If you have another system (e.g. Windows), starts the last one chosen",
    "Разделителна способност на менюто": "Menu resolution",
    "автоматично": "automatic",
    "Фон на менюто": "Menu background",
    "⚠ В GRUB има тема (GRUB_THEME) и тя покрива фона.": "⚠ GRUB has a theme (GRUB_THEME) and it covers the background.",
    "Картинка зад менюто на GRUB. Вижда се, ако менюто не е скрито.": "A picture behind the GRUB menu. Visible when the menu is not hidden.",
    "Картинка": "Picture",
    "Без картинка": "No picture",
    "Картинка за фона на GRUB": "Picture for the GRUB background",
    "Картинки": "Pictures",
    "Не мога да отворя картинката: {}": "Can't open the picture: {}",
    "няма (ще се махне)": "none (will be removed)",
    "Прилагам": "Applying",
    "Да върна ли всичко както беше?": "Undo everything?",
    "Маха настройките и темите, сложени от програмата, и връща старата анимация. Ще поиска паролата ти.":
        "Removes the settings and themes added by the program and restores the old animation. It will ask for your password.",
    "Върни": "Undo",
    "Връщам както беше": "Restoring as it was",
}

_SH = None


def _shabloni():
    global _SH
    if _SH is None:
        _SH = []
        for k, v in EN.items():
            if "{}" in k:
                rx = re.compile("^" + re.escape(k).replace(r"\{\}", "(.*?)") + "$", re.S)
                _SH.append((rx, v))
    return _SH


def _(s):
    if ezik() == "bg" or not isinstance(s, str):
        return s
    if s in EN:
        return EN[s]
    for rx, v in _shabloni():
        m = rx.match(s)
        if m:
            return v.format(*(EN.get(g, g) for g in m.groups()))
    return s
