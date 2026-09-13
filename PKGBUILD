# Maintainer: TheOddCell <me@oddcell.ca>
pkgname=tooktoolong
pkgver=1.0.0
pkgrel=1
pkgdesc="Root daemon (tooktoolongd) and CLI (ttlctl) for wall/command timers and stopwatches"
arch=('any')
url=""  # TODO: fill in once this has a real project page/repo
license=('custom')  # TODO: pick a real license and update this
depends=('python' 'util-linux')
backup=()
install=tooktoolong.install
source=(
    "tooktoolongd"
    "ttlcommon.py"
    "ttlctl"
    "TookTooLong.service"
)
sha256sums=('SKIP'
            'SKIP'
            'SKIP'
            'SKIP')

package() {
    install -d -m 0755 "$pkgdir/usr/lib/tooktoolong"
    install -m 0755 "$srcdir/tooktoolongd" "$pkgdir/usr/lib/tooktoolong/tooktoolongd"
    install -m 0644 "$srcdir/ttlcommon.py" "$pkgdir/usr/lib/tooktoolong/ttlcommon.py"
    install -m 0755 "$srcdir/ttlctl" "$pkgdir/usr/lib/tooktoolong/ttlctl"

    install -d -m 0755 "$pkgdir/usr/bin"
    ln -s /usr/lib/tooktoolong/ttlctl "$pkgdir/usr/bin/ttlctl"

    install -Dm644 "$srcdir/TookTooLong.service" \
        "$pkgdir/usr/lib/systemd/system/TookTooLong.service"
}
