#!/bin/sh
# Прави dist/boot-marka_<версия>_all.deb (без root: dpkg-deb --root-owner-group).
set -e
cd "$(dirname "$0")"
V=$(sed -n 's/^VERSION = "\(.*\)"/\1/p' jezgro.py)
umask 022
R=$(mktemp -d)
chmod 755 "$R"
trap 'rm -rf "$R"' EXIT
mkdir -p "$R/DEBIAN" "$R/usr/lib/boot-marka" "$R/usr/bin" "$R/usr/share/applications" "$R/usr/share/doc/boot-marka"
install -m 755 boot-marka.py prilozhi.py "$R/usr/lib/boot-marka/"
install -m 644 jezgro.py ezik.py "$R/usr/lib/boot-marka/"
ln -s ../lib/boot-marka/boot-marka.py "$R/usr/bin/boot-marka"
install -m 644 debian/com.palamarka.bootmarka.desktop "$R/usr/share/applications/"
install -m 644 README.md "$R/usr/share/doc/boot-marka/"
install -m 644 LICENSE "$R/usr/share/doc/boot-marka/copyright"
sed "s/@VERSION@/$V/; s/@SIZE@/$(du -sk "$R/usr" | cut -f1)/" debian/control > "$R/DEBIAN/control"
mkdir -p dist
dpkg-deb --root-owner-group -Zxz --build "$R" "dist/boot-marka_${V}_all.deb"
echo "dist/boot-marka_${V}_all.deb"
