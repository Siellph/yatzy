from __future__ import annotations

import json
import secrets
import socket
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from yatzy.io import dumps_pack, parse_tournaments
from yatzy.models import Tournament

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6
DISCOVERY_PORT = 18777
BEACON_PREFIX = b"YATZY1|"
PROBE_PREFIX = b"YATZY?"
HTTP_TIMEOUT = 20
DISCOVERY_SECONDS = 8


class SyncError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Invite:
    token: str
    host: str = ""
    port: int = 0

    @property
    def direct(self) -> bool:
        return bool(self.host and self.port)


@dataclass(slots=True)
class LanHost:
    token: str
    ip: str
    port: int
    _httpd: ThreadingHTTPServer
    _http_thread: threading.Thread
    _stop: threading.Event
    _disco_thread: threading.Thread

    @property
    def invite(self) -> str:
        return f"{self.ip}:{self.port}/{self.token}"

    def stop(self) -> None:
        self._stop.set()
        try:
            self._httpd.shutdown()
        except Exception:
            pass
        try:
            self._httpd.server_close()
        except Exception:
            pass
        self._http_thread.join(timeout=2)
        self._disco_thread.join(timeout=2)


def new_token() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def format_token(token: str) -> str:
    clean = normalize_token(token)
    return " ".join(clean[index : index + 2] for index in range(0, len(clean), 2))


def mask_code_input(raw: str) -> str:
    """Капс и группировка как на экране хоста: AB 23 CD. Адрес не ломаем."""
    text = raw or ""
    if any(char in text for char in ".:/"):
        return text.upper().replace(" ", "")
    return format_token(normalize_token(text)[:CODE_LENGTH])


def normalize_token(token: str) -> str:
    return "".join(char for char in token.upper() if char.isalnum())


def parse_invite(raw: str) -> Invite:
    text = (raw or "").strip().upper().replace(" ", "").replace("-", "")
    if not text:
        raise SyncError("Введите код с другого устройства.")
    if "/" in text:
        address, token = text.rsplit("/", 1)
        token = normalize_token(token)
        if ":" not in address:
            raise SyncError("Адрес должен быть вида 192.168.0.10:18881/AB12CD.")
        host, port_text = address.rsplit(":", 1)
        if not _valid_token(token):
            raise SyncError("Код должен быть из 6 символов.")
        try:
            port = int(port_text)
        except ValueError as error:
            raise SyncError("Неверный порт в адресе.") from error
        if not host or not (1 <= port <= 65535):
            raise SyncError("Неверный адрес.")
        return Invite(token=token, host=host, port=port)
    token = normalize_token(text)
    if not _valid_token(token):
        raise SyncError("Код должен быть из 6 символов, либо адрес целиком.")
    return Invite(token=token)


def lan_ip() -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        address = probe.getsockname()[0]
    except OSError:
        address = "127.0.0.1"
    finally:
        probe.close()
    return address


def start_host(token: str, on_sync) -> LanHost:
    token = normalize_token(token)
    httpd = ThreadingHTTPServer(("0.0.0.0", 0), _SyncHandler)
    httpd.yatzy_token = token
    httpd.yatzy_sync = on_sync
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, name="yatzy-sync-http", daemon=True)
    thread.start()
    stop = threading.Event()
    ip = lan_ip()
    port = int(httpd.server_address[1])
    disco = threading.Thread(
        target=_announce,
        args=(token, ip, port, stop),
        name="yatzy-sync-disco",
        daemon=True,
    )
    disco.start()
    return LanHost(token, ip, port, httpd, thread, stop, disco)


def join_session(raw: str, tournaments: list[Tournament]) -> list[Tournament]:
    invite = parse_invite(raw)
    if invite.direct:
        host, port = invite.host, invite.port
    else:
        found = discover_host(invite.token)
        if found is None:
            raise SyncError(
                "Не нашли устройство в Wi‑Fi. Введите адрес целиком — он показан под кодом."
            )
        host, port = found
    return exchange(host, port, invite.token, tournaments)


def discover_host(token: str, timeout: float = DISCOVERY_SECONDS) -> tuple[str, int] | None:
    token = normalize_token(token)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.4)
    probe = PROBE_PREFIX + token.encode("ascii")
    try:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            for target in _broadcast_targets():
                try:
                    sock.sendto(probe, (target, DISCOVERY_PORT))
                except OSError:
                    continue
            try:
                data, _addr = sock.recvfrom(256)
            except TimeoutError:
                continue
            except OSError:
                break
            parsed = _parse_beacon(data)
            if parsed and parsed[0] == token:
                return parsed[1], parsed[2]
    finally:
        sock.close()
    return None


def exchange(host: str, port: int, token: str, tournaments: list[Tournament]) -> list[Tournament]:
    request = Request(
        f"http://{host}:{port}/sync",
        data=dumps_pack(tournaments).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Yatzy-Key": normalize_token(token),
        },
    )
    try:
        with urlopen(request, timeout=HTTP_TIMEOUT) as response:
            return parse_tournaments(response.read(), allow_empty=True)
    except HTTPError as error:
        if error.code == 401:
            raise SyncError("Неверный код.") from error
        raise SyncError("Устройство ответило ошибкой.") from error
    except URLError as error:
        raise SyncError("Нет связи. Проверьте Wi‑Fi и что на другом устройстве открыт код.") from error
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SyncError("Не удалось прочитать ответ.") from error


def _valid_token(token: str) -> bool:
    return len(token) == CODE_LENGTH and all(char in CODE_ALPHABET for char in token)


def _keys_match(given: str, expected: str) -> bool:
    left = normalize_token(given)
    right = normalize_token(expected)
    if len(left) != len(right):
        return False
    return secrets.compare_digest(left.encode("ascii"), right.encode("ascii"))


def _broadcast_targets() -> list[str]:
    targets = ["255.255.255.255"]
    ip = lan_ip()
    parts = ip.split(".")
    if len(parts) == 4 and not ip.startswith("127."):
        targets.append(".".join(parts[:3] + ["255"]))
    return targets


def _beacon_bytes(token: str, ip: str, port: int) -> bytes:
    return BEACON_PREFIX + f"{token}|{ip}|{port}".encode("ascii")


def _parse_beacon(data: bytes) -> tuple[str, str, int] | None:
    if not data.startswith(BEACON_PREFIX):
        return None
    try:
        token, ip, port_text = data[len(BEACON_PREFIX) :].decode("ascii").split("|")
        port = int(port_text)
    except (ValueError, UnicodeDecodeError):
        return None
    if not _valid_token(token) or not (1 <= port <= 65535):
        return None
    return token, ip, port


def _announce(token: str, ip: str, port: int, stop: threading.Event) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(0.5)
    beacon = _beacon_bytes(token, ip, port)
    try:
        try:
            sock.bind(("", DISCOVERY_PORT))
        except OSError:
            pass
        while not stop.is_set():
            try:
                data, addr = sock.recvfrom(256)
            except TimeoutError:
                data, addr = b"", None
            except OSError:
                break
            if data.startswith(PROBE_PREFIX) and _keys_match(data[len(PROBE_PREFIX) :].decode("ascii", "ignore"), token):
                if addr:
                    try:
                        sock.sendto(beacon, addr)
                    except OSError:
                        pass
            if stop.wait(0.8):
                break
            for target in _broadcast_targets():
                try:
                    sock.sendto(beacon, (target, DISCOVERY_PORT))
                except OSError:
                    continue
    finally:
        sock.close()


class _SyncHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path.split("?", 1)[0] != "/sync":
            self.send_error(404)
            return
        if not _keys_match(self.headers.get("X-Yatzy-Key", ""), self.server.yatzy_token):
            self.send_error(401)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400)
            return
        body = self.rfile.read(max(0, length))
        try:
            incoming = parse_tournaments(body, allow_empty=True)
            merged = self.server.yatzy_sync(incoming)
            payload = dumps_pack(merged).encode("utf-8")
        except (ValueError, TypeError, OSError):
            self.send_error(400)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return
