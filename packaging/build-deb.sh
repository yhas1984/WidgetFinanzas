#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-5.0.2}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD="${ROOT}/.package-build"
DIST="${ROOT}/dist"
PKG="${BUILD}/widget-finanzas_${VERSION}_amd64"

rm -rf "${BUILD}"
mkdir -p "${PKG}/DEBIAN" "${PKG}/opt/widget-finanzas" "${PKG}/usr/bin" "${PKG}/usr/share/applications" "${PKG}/usr/share/doc/widget-finanzas"

python3 -m PyInstaller --clean --noconfirm --distpath "${DIST}" --workpath "${BUILD}/pyinstaller" "${ROOT}/CryptoWidget.spec"
install -m 0755 "${DIST}/CryptoWidget" "${PKG}/opt/widget-finanzas/CryptoWidget"
install -m 0644 "${ROOT}/config.json" "${PKG}/opt/widget-finanzas/config.json"
install -m 0644 "${ROOT}/icon.png" "${PKG}/opt/widget-finanzas/icon.png"

cat > "${PKG}/usr/bin/widget-finanzas" <<'EOF'
#!/bin/sh
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
exec /opt/widget-finanzas/CryptoWidget "$@"
EOF
chmod 0755 "${PKG}/usr/bin/widget-finanzas"

cat > "${PKG}/usr/share/applications/widget-finanzas.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Widget Finanzas
Comment=Widget Finanzas V5
Exec=/usr/bin/widget-finanzas
Terminal=false
Categories=Utility;Finance;
EOF

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
Depends: libxcb-xinerama0
Description: Widget Finanzas V5
 Desktop financial ticker widget with configurable assets and cached data.
EOF

OUT="${ROOT}/widget-finanzas_${VERSION}_amd64.deb"
dpkg-deb --build --root-owner-group "${PKG}" "${OUT}"
dpkg-deb --info "${OUT}"
dpkg-deb --contents "${OUT}" | grep -E 'opt/widget-finanzas/(CryptoWidget|config.json|icon.png)|usr/bin/widget-finanzas|usr/share/applications|SOURCE.txt'
file "${DIST}/CryptoWidget"
echo "created ${OUT}"
