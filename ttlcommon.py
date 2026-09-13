"""Shared protocol/helpers for tooktoolongd and ttlctl.

Both programs add their own directory to sys.path and `import ttlcommon`,
so this file must live next to both executables (or be installed to a
shared location that's on sys.path for both).
"""
import json
import os
import re
import socket
import struct
import time

PROTOCOL_VERSION = 1

SOCKET_PATH = "/run/tooktoolong/tooktoolongd.sock"
RUN_DIR = "/run/tooktoolong"
DATA_DIR = "/var/lib/tooktoolong/timers"

# Max size of one JSON line on the wire, to keep a hostile local user from
# handing the root daemon an unbounded read.
MAX_LINE = 1024 * 1024

KINDS = ("wall_group", "cmd", "stopwatch")


class ProtocolError(Exception):
    pass


# --------------------------------------------------------------------------
# duration parsing / formatting
# --------------------------------------------------------------------------

_DURATION_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([smhd]?)", re.IGNORECASE)
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "": 1}


def parse_duration(text):
    """Parse strings like '90', '90s', '5m', '1h30m', '2d3h' into seconds."""
    text = text.strip().lower()
    if not text:
        raise ValueError("empty duration")
    total = 0.0
    pos = 0
    matched_any = False
    for m in _DURATION_RE.finditer(text):
        if m.start() != pos:
            raise ValueError(f"invalid duration: {text!r}")
        pos = m.end()
        value, unit = m.groups()
        total += float(value) * _UNIT_SECONDS[unit]
        matched_any = True
    if not matched_any or pos != len(text):
        raise ValueError(f"invalid duration: {text!r}")
    if total <= 0:
        raise ValueError("duration must be positive")
    return total


def format_duration(seconds):
    seconds = int(round(seconds))
    if seconds < 0:
        sign = "-"
        seconds = -seconds
    else:
        sign = ""
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    return sign + " ".join(parts)


# --------------------------------------------------------------------------
# wire protocol: one JSON object per line, request/response
# --------------------------------------------------------------------------

def send_json(sock, obj):
    data = json.dumps(obj).encode("utf-8") + b"\n"
    sock.sendall(data)


def recv_line(sock):
    buf = bytearray()
    while True:
        chunk = sock.recv(1)
        if not chunk:
            if not buf:
                return None
            break
        if chunk == b"\n":
            break
        buf += chunk
        if len(buf) > MAX_LINE:
            raise ProtocolError("line too long")
    return bytes(buf)


def recv_json(sock):
    line = recv_line(sock)
    if line is None:
        return None
    try:
        return json.loads(line.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ProtocolError(f"bad json: {e}")


def request(obj, timeout=10.0):
    """Client-side helper: connect, send one request, return one response."""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(SOCKET_PATH)
    except (FileNotFoundError, ConnectionRefusedError) as e:
        raise ConnectionError(
            f"cannot reach tooktoolongd at {SOCKET_PATH} ({e}); is it running?"
        )
    try:
        send_json(sock, obj)
        resp = recv_json(sock)
        if resp is None:
            raise ConnectionError("daemon closed connection without a response")
        return resp
    finally:
        sock.close()


def get_peer_credentials(conn):
    """Return (pid, uid, gid) of the process on the other end of a UNIX socket.

    This is authoritative even though the socket itself is world-writable:
    the kernel fills in SO_PEERCRED from the connecting process's real
    credentials, so a client cannot lie about who it is.
    """
    creds = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    pid, uid, gid = struct.unpack("3i", creds)
    return pid, uid, gid


# --------------------------------------------------------------------------
# misc
# --------------------------------------------------------------------------

def now():
    return time.time()


def atomic_write_json(path, obj, mode=0o600):
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
