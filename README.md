# boot-marka: зареждане на Linux с картинки

Програма за Debian, с която настройваш **как изглежда зареждането на компютъра**, без да пипаш конфигурационни файлове.

![Анимацията при зареждане: логото „диша“, а отдолу трикольорът блещука отляво надясно](docs/zarezhdane.gif)

## Какво може
- **🎬 Анимация (Plymouth).** Галерия с всички инсталирани теми, с **живи миниатюри**. Има и **„Моя анимация“**: даваш GIF, видео или лого, а програмата прави от него тема. Задаваш цвят на фона (сам се взема от картинката), големина, скорост и надпис.
- **Какво има под анимацията.** Повтарящите се варианти не зависят от това колко бързо зарежда компютърът:
  - **Трикольор:** една лента в бяло, зелено и червено блещука отляво надясно, с искра;
  - **Знаме:** три ивици се пълнят на място, искрят и проблясват;
  - бягаща светлинка, три пулсиращи точки или надпис „Зареждане…“;
  - класическата лента за напредъка или нищо.
- **🤫 Текст при зареждане.** Три режима. Другите настройки на ядрото (например за видеокартата) остават непокътнати.
  - **Тих:** само анимацията, без съобщения на ядрото и без мигащ курсор.
  - **Нормален.**
  - **Подробен:** всичко се изписва, за когато нещо не тръгва.
- **🐧 GRUB.** Скрито меню, обратно броене или меню; колко секунди да чака; да помни ли последния избор; разделителна способност; картинка за фон.
- **↶ Върни както беше.** Маха всичко, направено от програмата, и връща старата анимация.

![Галерията с темите](docs/anim.png)

| Текст при зареждане | GRUB |
|---|---|
| ![](docs/tekst.png) | ![](docs/grub.png) |

## Инсталиране
Свали `.deb` от [Releases](https://github.com/nikogurzov/boot-marka/releases) и:
```
sudo apt install ./boot-marka_*_all.deb
```
В менюто я търси като **„Зареждане (boot-marka)“**.

## Безопасно
- Нищо не се записва, докато не натиснеш **„Приложи“** и не въведеш паролата (pkexec).
- **Основният `/etc/default/grub` не се пипа.** Настройките са в отделен файл, `/etc/default/grub.d/99-boot-marka.cfg`, който може да се изтрие на ръка.
- При първото прилагане програмата запазва как е било всичко преди нея (`/var/backups/boot-marka`).
- Собствените теми са в `/usr/share/plymouth/themes/boot-marka-*`. Помощникът проверява всеки файл, преди да го сложи: само PNG кадри и скрипт, направен от програмата.
- Ако дискът е криптиран, паролата се пита върху анимацията.
- При NVIDIA програмата предлага поправката `nvidia-drm.modeset=1`, без която анимацията може да не се вижда.

## За разработчици
```
./boot-marka.py            прозорец
./boot-marka.py --text     как е настроено сега (само чете)
./boot-marka.py --reset    връща всичко както беше
./build-deb.sh             прави dist/boot-marka_<версия>_all.deb
python3 -m unittest discover -s tests          тестове в пясъчник (не пипат системата)
python3 tools/pregled.py анимация.gif out.mp4 trikolor     видео преглед без рестартиране
```

## English
boot-marka is a GTK 4 / libadwaita app for Debian that sets **how your computer looks while it boots**, without editing config files. **The interface is in English when your system is in English** (and in Bulgarian on a Bulgarian system; `BOOT_MARKA_EZIK=en` forces English).

- **Animation (Plymouth):** a gallery of all installed boot splash themes with **live thumbnails**, plus **“My animation”**: turn your own GIF, video or logo into a theme (background color picked automatically, size, speed, optional text).
- **Below the animation:** looping indicators that don't pretend to know how long booting takes: a **tricolor shimmer**, a **filling flag**, a running light, pulsing dots or “Loading…” text. The classic progress bar is still there.
- **Boot text:** Quiet (only the animation, no kernel messages, no blinking cursor), Normal, or Verbose. Your other kernel options stay untouched.
- **GRUB:** hidden menu, countdown or menu; timeout; remember last choice; resolution; background picture.
- **Safe:** nothing is written until you press “Apply” and enter your password; settings go to a separate `/etc/default/grub.d/99-boot-marka.cfg` (the main `/etc/default/grub` is never touched); the original state is saved; **↶ Undo everything** restores it.

![The gallery in English](docs/en/anim.png)

| Boot text | GRUB |
|---|---|
| ![](docs/en/tekst.png) | ![](docs/en/grub.png) |

Install: download the `.deb` from [Releases](https://github.com/nikogurzov/boot-marka/releases) and run `sudo apt install ./boot-marka_*_all.deb`. Tested on Debian 13. If something looks wrong after a restart, open the app and press ↶. Bug reports are welcome in Issues.

License: MIT. Sister project: [drv-marka](https://github.com/nikogurzov/drv-marka).
