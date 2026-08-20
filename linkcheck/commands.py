"""Comandos del sistema operativo para configurar la red y probar el enlace."""
import subprocess

from .constants import IS_WINDOWS
from .ping import parse_ping


def assign_ip(iface: str, ip: str) -> tuple[bool, str]:
    if IS_WINDOWS:
        cmd = [
            "netsh",
            "interface",
            "ip",
            "set",
            "address",
            f"name={iface}",
            "static",
            ip,
            "255.255.0.0",
        ]
    else:
        cmd = ["ip", "addr", "add", f"{ip}/16", "dev", iface]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as e:
        return False, f"comando no disponible: {e}"
    if r.returncode != 0:
        msg = (r.stderr or r.stdout or "").strip()
        if "File exists" in msg or "ya existe" in msg.lower():
            return True, ""
        return False, msg or f"código de salida {r.returncode}"
    return True, ""


def run_ping(target: str, count: int, timeout: int) -> tuple[int, dict]:
    if IS_WINDOWS:
        cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), target]
    else:
        cmd = ["ping", "-c", str(count), "-W", str(timeout), target]
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=count * timeout + 10,
        )
    except subprocess.TimeoutExpired:
        return 1, {"error": "Tiempo agotado al ejecutar ping"}
    except FileNotFoundError:
        return 1, {"error": "`ping` no está disponible en el sistema"}
    output = (r.stdout or "") + "\n" + (r.stderr or "")
    return r.returncode, {"raw": output, "stats": parse_ping(output)}
