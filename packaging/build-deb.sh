#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-5.0.3}"
PYTHON="${PYTHON:-python3}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD="${ROOT}/.package-build"
DIST="${ROOT}/dist"
PKG="${BUILD}/widget-finanzas_${VERSION}_amd64"

rm -rf "${BUILD}"
mkdir -p "${PKG}/DEBIAN" "${PKG}/opt/widget-finanzas" "${PKG}/usr/bin" "${PKG}/usr/share/applications" "${PKG}/usr/share/doc/widget-finanzas" "${PKG}/usr/share/icons/hicolor/512x512/apps"

"${PYTHON}" -m PyInstaller --clean --noconfirm --distpath "${DIST}" --workpath "${BUILD}/pyinstaller" "${ROOT}/CryptoWidget.spec"
install -m 0755 "${DIST}/CryptoWidget" "${PKG}/opt/widget-finanzas/CryptoWidget"
install -m 0644 "${ROOT}/config.json" "${PKG}/opt/widget-finanzas/config.json"
install -m 0644 "${ROOT}/icon.png" "${PKG}/opt/widget-finanzas/icon.png"
install -m 0644 "${ROOT}/icon.png" "${PKG}/usr/share/icons/hicolor/512x512/apps/widget-finanzas.png"

cat > "${PKG}/usr/bin/widget-finanzas" <<'EOF'
#!/bin/sh
exec /opt/widget-finanzas/CryptoWidget "$@"
EOF
chmod 0755 "${PKG}/usr/bin/widget-finanzas"

cat > "${PKG}/usr/share/applications/widget-finanzas.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Widget Finanzas
Comment=Widget Finanzas V5
Exec=/usr/bin/widget-finanzas
TryExec=/usr/bin/widget-finanzas
Icon=widget-finanzas
Terminal=false
Categories=Utility;Finance;
StartupWMClass=CryptoWidget
EOF

cat > "${PKG}/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true
fi
EOF
chmod 0755 "${PKG}/DEBIAN/postinst"

cat > "${PKG}/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
if [ "${1:-}" = "remove" ] || [ "${1:-}" = "purge" ]; then
    getent passwd | while IFS=: read -r _ _ uid _ _ home_dir _; do
        if { [ "${uid}" = "0" ] || [ "${uid}" -ge 1000 ] 2>/dev/null; } \
            && [ -n "${home_dir}" ] && [ "${home_dir}" != "/" ]; then
            for desktop_file in \
                "${home_dir}/.config/autostart/widget-finanzas.desktop" \
                "${home_dir}/.config/autostart/crypto_widget.desktop" \
                "${home_dir}/.local/share/applications/crypto_widget.desktop"; do
                if [ -f "${desktop_file}" ] \
                    && grep -Eq '^Exec=.*(widget-finanzas|CryptoWidget|crypto_widget)' "${desktop_file}"; then
                    rm -f -- "${desktop_file}"
                fi
            done
        fi
    done
fi
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true
fi
EOF
chmod 0755 "${PKG}/DEBIAN/postrm"

cat > "${PKG}/usr/share/doc/widget-finanzas/SOURCE.txt" <<EOF
Source repository: https://github.com/yhas1984/WidgetFinanzas
Source commit: $(git -C "${ROOT}" rev-parse HEAD)
Package: widget-finanzas
Version: ${VERSION}
Architecture: amd64
EOF

cat > "${PKG}/DEBIAN/control" <<EOF
Package: widget-finanzas
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: yhas1984
Depends: libegl1, libgl1, libxkbcommon-x11-0, libxcb-xinerama0
Description: Widget Finanzas V5
 Desktop financial ticker widget with configurable assets and cached data.
EOF

chmod 0644 \
    "${PKG}/DEBIAN/control" \
    "${PKG}/usr/share/applications/widget-finanzas.desktop" \
    "${PKG}/usr/share/doc/widget-finanzas/SOURCE.txt"
find "${PKG}" -type d -exec chmod 0755 {} +

OUT="${ROOT}/widget-finanzas_${VERSION}_amd64.deb"
dpkg-deb --build --root-owner-group "${PKG}" "${OUT}"
dpkg-deb --info "${OUT}"
dpkg-deb --contents "${OUT}" | grep -E 'opt/widget-finanzas/(CryptoWidget|config.json|icon.png)|usr/bin/widget-finanzas|usr/share/applications|usr/share/icons|SOURCE.txt'
file "${DIST}/CryptoWidget"
echo "created ${OUT}"
