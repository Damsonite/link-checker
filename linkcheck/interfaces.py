"""Detección de la interfaz Ethernet, MAC y direcciones IP."""
import hashlib

import psutil

from .colors import Color
from .constants import (
    ETH_PREFIXES,
    LINK_LOCAL_NET,
    MAC_RE,
    SKIP_EXACT,
    SKIP_PREFIXES,
    SKIP_SUBSTR,
)


def list_eth_interfaces() -> list[str]:
    candidates = []
    fallbacks = []
    for name in psutil.net_if_stats().keys():
        ln = name.lower()
        if ln in SKIP_EXACT:
            continue
        if any(ln.startswith(p) for p in SKIP_PREFIXES):
            continue
        if any(s in ln for s in SKIP_SUBSTR):
            continue
        if any(ln.startswith(p) for p in ETH_PREFIXES):
            candidates.append(name)
        else:
            fallbacks.append(name)
    return candidates + fallbacks


def pick_active_interface(forced: str | None) -> str | None:
    if forced:
        return forced
    candidates = list_eth_interfaces()
    if not candidates:
        return None
    up_first = [i for i in candidates if psutil.net_if_stats()[i].isup]
    return up_first[0] if up_first else candidates[0]


def get_mac(iface: str) -> str | None:
    for a in psutil.net_if_addrs().get(iface, []):
        if MAC_RE.match(a.address):
            return a.address
    return None


def link_local_from_mac(mac: str) -> str:
    digest = hashlib.sha256(mac.encode()).digest()
    third = 1 + (digest[0] % 253)
    fourth = 1 + (digest[1] % 253)
    return f"{LINK_LOCAL_NET}.{third}.{fourth}"


def has_link_local(iface: str) -> str | None:
    for a in psutil.net_if_addrs().get(iface, []):
        if a.family == getattr(psutil, "AF_INET", 2):
            if a.address.startswith(LINK_LOCAL_NET + "."):
                return f"{a.address}/{a.netmask}"
    return None


def current_ipv4(iface: str) -> str | None:
    for a in psutil.net_if_addrs().get(iface, []):
        if a.family == getattr(psutil, "AF_INET", 2):
            return f"{a.address}/{a.netmask}"
    return None


def show_interface_status(iface: str) -> dict:
    s = psutil.net_if_stats()[iface]
    duplex = {
        getattr(psutil, "NIC_DUPLEX_FULL", 2): "full-duplex",
        getattr(psutil, "NIC_DUPLEX_HALF", 1): "half-duplex",
    }.get(s.duplex, "?")
    speed = f"{s.speed} Mbps" if s.speed and s.speed > 0 else "velocidad desconocida"
    is_up = s.isup
    if is_up:
        print(
            f"[+] Interfaz {iface}: {Color.wrap(Color.GREEN, 'ENLACE UP')} "
            f"({speed}, {duplex}, MTU {s.mtu})"
        )
    else:
        print(f"[!] Interfaz {iface}: {Color.wrap(Color.RED, 'ENLACE DOWN')}")
    ip = current_ipv4(iface)
    if ip:
        print(f"[+] Mi IP: {ip}")
    else:
        print(f"[!] {iface} no tiene IPv4 asignada.")
    return {"is_up": is_up}
