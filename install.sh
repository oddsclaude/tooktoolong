#!/usr/bin/env bash
# Installs tooktoolongd + ttlctl under /usr/local, matching
# systemd/usr-local/TookTooLong.service.
#
# Usage:
#   sudo ./install.sh                 install (or upgrade) and enable+start the service
#   sudo ./install.sh --no-enable     install but don't enable the service
#   sudo ./install.sh --no-start      install/enable but don't start it now
#   sudo ./install.sh --uninstall     remove the installed files and service
#   sudo ./install.sh --uninstall --purge   also delete persisted timers/stopwatches
set -euo pipefail

PREFIX=/usr/local
LIBDIR="$PREFIX/lib/tooktoolong"
BINDIR="$PREFIX/bin"
UNIT_SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_SRC="$UNIT_SRC_DIR/systemd/usr-local/TookTooLong.service"
UNIT_DST="/etc/systemd/system/TookTooLong.service"
DATA_DIR="/var/lib/tooktoolong"
RUN_DIR="/run/tooktoolong"

ENABLE=1
START=1
UNINSTALL=0
PURGE=0

for arg in "$@"; do
    case "$arg" in
        --no-enable) ENABLE=0 ;;
        --no-start) START=0 ;;
        --uninstall) UNINSTALL=1 ;;
        --purge) PURGE=1 ;;
        -h|--help)
            sed -n '2,10p' "${BASH_SOURCE[0]}"
            exit 0
            ;;
        *)
            echo "unknown argument: $arg" >&2
            exit 1
            ;;
    esac
done

if [[ $EUID -ne 0 ]]; then
    echo "must be run as root (e.g. via sudo)" >&2
    exit 1
fi

if [[ $UNINSTALL -eq 1 ]]; then
    echo "stopping and disabling TookTooLong.service..."
    systemctl disable --now TookTooLong.service 2>/dev/null || true
    rm -f "$UNIT_DST"
    systemctl daemon-reload
    echo "removing installed files..."
    rm -f "$BINDIR/ttlctl"
    rm -rf "$LIBDIR"
    if [[ $PURGE -eq 1 ]]; then
        echo "purging persisted timers/stopwatches and runtime state..."
        rm -rf "$DATA_DIR" "$RUN_DIR"
    else
        echo "left $DATA_DIR in place (pass --purge to remove it too)"
    fi
    echo "uninstalled."
    exit 0
fi

for f in tooktoolongd ttlcommon.py ttlctl; do
    if [[ ! -f "$UNIT_SRC_DIR/$f" ]]; then
        echo "missing $UNIT_SRC_DIR/$f - run this script from the tooktoolong source tree" >&2
        exit 1
    fi
done
if [[ ! -f "$UNIT_SRC" ]]; then
    echo "missing $UNIT_SRC" >&2
    exit 1
fi

echo "installing to $LIBDIR..."
install -d -m 0755 "$LIBDIR"
install -m 0755 "$UNIT_SRC_DIR/tooktoolongd" "$LIBDIR/tooktoolongd"
install -m 0644 "$UNIT_SRC_DIR/ttlcommon.py" "$LIBDIR/ttlcommon.py"
install -m 0755 "$UNIT_SRC_DIR/ttlctl" "$LIBDIR/ttlctl"

echo "linking $BINDIR/ttlctl..."
install -d -m 0755 "$BINDIR"
ln -sf "$LIBDIR/ttlctl" "$BINDIR/ttlctl"

echo "installing systemd unit to $UNIT_DST..."
install -m 0644 "$UNIT_SRC" "$UNIT_DST"
systemctl daemon-reload

if [[ $ENABLE -eq 1 ]]; then
    if [[ $START -eq 1 ]]; then
        systemctl enable --now TookTooLong.service
    else
        systemctl enable TookTooLong.service
    fi
else
    echo "not enabling the service (--no-enable given); start it manually with:"
    echo "  systemctl enable --now TookTooLong.service"
fi

echo "done. tooktoolongd -> $LIBDIR/tooktoolongd, ttlctl -> $BINDIR/ttlctl"
