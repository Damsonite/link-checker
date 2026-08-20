#!/usr/bin/env python3
import argparse
import hashlib
import platform
import re
import subprocess
import sys

try:
    import psutil
except ImportError:
    sys.stderr.write("[ERROR] Falta la dependencia 'psutil'.\n")
    sys.stderr.write("        Ejecuta: pip install -r requirements.txt\n")
    sys.exit(2)


IS_WINDOWS = platform.system() == "Windows"
LINK_LOCAL_NET = "169.254"
COUNT_DEFAULT = 4
TIMEOUT_DEFAULT = 2
MAC_RE = re.compile(r"^([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}$")

ETH_PREFIXES = (
    "eth",
    "en",
    "eno",
    "enp",
    "ens",
    "ethernet",
    "realtek",
    "intel",
    "local area connection",
    "lan",
)
SKIP_EXACT = {"lo", "lo0"}
SKIP_PREFIXES = (
    "veth",
    "docker",
    "br-",
    "tun",
    "tap",
    "vlan",
    "bluetooth",
    "bnep",
    "awdl",
    "vmnet",
    "vmware",
    "virtualbox",
    "hyper-v",
    "wi-fi",
    "wlan",
    "wlp",
    "wwan",
    "wwp",
    "wl",
    "isatap",
    "teredo",
    "6to4",
)
SKIP_SUBSTR = ("loopback",)


class Color:
    ENABLED = sys.stdout.isatty() and not IS_WINDOWS
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"

    @classmethod
    def disable(cls):
        cls.ENABLED = False
        for attr in ("RESET", "BOLD", "RED", "GREEN", "YELLOW", "BLUE"):
            setattr(cls, attr, "")

    @classmethod
    def wrap(cls, color: str, text: str) -> str:
        if not cls.ENABLED:
            return text
        return f"{color}{text}{cls.RESET}"


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


def parse_ping(output: str) -> dict:
    s = {
        "sent": None,
        "received": None,
        "loss_pct": None,
        "min_ms": None,
        "avg_ms": None,
        "max_ms": None,
        "reachable": False,
        "unreachable": False,
        "timed_out": False,
    }

    m = re.search(
        r"(\d+(?:[.,]\d+)?)\s*%\s*(?:packet\s+)?(?:loss|perdidos?)",
        output,
        re.IGNORECASE,
    )
    if m:
        s["loss_pct"] = float(m.group(1).replace(",", "."))

    m = re.search(r"(?:sent|enviados)\s*=\s*(\d+)", output, re.IGNORECASE)
    if m:
        s["sent"] = int(m.group(1))
    m = re.search(r"(?:received|recibidos)\s*=\s*(\d+)", output, re.IGNORECASE)
    if m:
        s["received"] = int(m.group(1))

    m = re.search(r"min/avg/max[^\n=]*=\s*([\d.]+)/([\d.]+)/([\d.]+)", output)
    if m:
        s["min_ms"] = float(m.group(1))
        s["avg_ms"] = float(m.group(2))
        s["max_ms"] = float(m.group(3))

    m = re.search(
        r"(?:M[ií]nimo|Minimum|Min)\s*=\s*(\d+)\s*ms.*?"
        r"(?:M[aá]ximo|Maximum|Max)\s*=\s*(\d+)\s*ms.*?"
        r"(?:M[eé]dia|Media|Average|Avg)\s*=\s*(\d+)\s*ms",
        output,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        s["min_ms"] = float(m.group(1))
        s["max_ms"] = float(m.group(2))
        s["avg_ms"] = float(m.group(3))

    if (
        "Destination host unreachable" in output
        or "Destination net unreachable" in output
    ):
        s["unreachable"] = True
    if "Request timed out" in output or "Tiempo de espera agotado" in output:
        s["timed_out"] = True
    if s["received"] is not None and s["received"] > 0:
        s["reachable"] = True
    return s


def diagnose(state: dict) -> list[str]:
    hints = []
    if not state.get("is_up"):
        hints.append(
            "No se detecta enlace físico. Revisa:\n"
            "      - Cable conectado firmemente en ambos extremos.\n"
            "      - Ponchado correcto (T568A en ambos lados o T568B en ambos lados,\n"
            "        para cable directo).\n"
            "      - NIC habilitada en el sistema operativo."
        )
        return hints
    if state.get("reachable"):
        return hints
    if state.get("unreachable"):
        hints.append(
            "El otro extremo no está en nuestra subred (169.254.0.0/16).\n"
            "      Verifica que ambos equipos usen IPs link-local del mismo rango."
        )
    elif state.get("timed_out"):
        hints.append(
            "El otro extremo no responde. Posibles causas:\n"
            "      - IP mal escrita o asignada en otra interfaz.\n"
            "      - Firewall bloqueando ICMPv4 entrante (en Windows desactívalo temporalmente).\n"
            "      - Cable con pares cruzados: solo un sentido funciona."
        )
    elif state.get("loss_pct") == 100.0:
        hints.append(
            "100% de pérdida. Comprueba que el otro extremo ya haya ejecutado este script"
            " (o configurado una IP manualmente)."
        )
    if state.get("loss_pct") and 0 < state["loss_pct"] < 100:
        hints.append(
            f"Pérdida de paquetes del {state['loss_pct']:.1f}%. "
            "Posible cable dañado o con interferencia."
        )
    return hints


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


def run(args: argparse.Namespace) -> int:
    iface = pick_active_interface(args.interface)
    if not iface:
        print("[ERROR] No se detectó ninguna interfaz Ethernet.")
        print("        Interfaces disponibles:")
        for n in psutil.net_if_stats().keys():
            print(f"          - {n}")
        print("        Usa -i NOMBRE para especificar una manualmente.")
        return 2
    if iface not in psutil.net_if_stats():
        print(f"[ERROR] La interfaz '{iface}' no existe.")
        return 2

    if args.assign_ip:
        mac = get_mac(iface)
        if not mac:
            print(f"[ERROR] No se pudo obtener la MAC de {iface}; no se asigna IP.")
            return 2
        new_ip = link_local_from_mac(mac)
        existing = has_link_local(iface)
        if existing:
            print(f"[-] {iface} ya tiene link-local: {existing}")
            print("    No se modifica para no pisar la IP del compañero.")
            local_ip = existing.split("/")[0]
        else:
            print(f"[+] Asignando IP link-local a {iface}: {new_ip}/16 ...")
            ok, err = assign_ip(iface, new_ip)
            if not ok:
                print(f"[ERROR] No se pudo asignar la IP: {err}")
                if IS_WINDOWS:
                    print("        Ejecuta PowerShell como Administrador.")
                else:
                    print("        Ejecuta con sudo.")
                return 2
            print(f"    OK -> {new_ip}/16")
            local_ip = new_ip
    else:
        ip_info = current_ipv4(iface)
        local_ip = ip_info.split("/")[0] if ip_info else None

    print()
    state = show_interface_status(iface)

    if not args.ip:
        if state["is_up"] and local_ip:
            print()
            print("[OK] Indica la IP del otro extremo para hacer ping.")
            print("     Ejemplo: python link_check.py <IP-del-compañero>")
        else:
            print()
            print("[!] No se puede continuar sin IP propia. Usa --assign-ip.")
        return 0 if state["is_up"] else 1

    if not state["is_up"]:
        print()
        print("[!] No se puede hacer ping con el enlace caído.")
        for hint in diagnose({"is_up": False}):
            print(f"    {hint}")
        return 1

    print()
    print(f"[+] Ping a {args.ip} ({args.count} paquetes, timeout {args.timeout}s)...")
    rc, result = run_ping(args.ip, args.count, args.timeout)

    if "error" in result:
        print(f"[ERROR] {result['error']}")
        return 1

    stats = result["stats"]

    if args.verbose:
        print()
        print(result["raw"].rstrip())
        print()

    sent = stats["sent"]
    received = stats["received"] if stats["received"] is not None else 0
    loss = stats["loss_pct"]
    if loss is None:
        loss = 0.0 if received == sent else 100.0

    print(f"    Enviados: {sent}   Recibidos: {received}   Pérdida: {loss:.1f}%")
    if stats["avg_ms"] is not None:
        print(
            f"    Latencia: min={stats['min_ms']:.1f} ms  "
            f"media={stats['avg_ms']:.1f} ms  max={stats['max_ms']:.1f} ms"
        )

    state.update(
        {
            "reachable": stats["reachable"],
            "unreachable": stats["unreachable"],
            "timed_out": stats["timed_out"],
            "loss_pct": stats["loss_pct"],
        }
    )

    print()
    if stats["reachable"]:
        print(f"[OK] {Color.wrap(Color.GREEN + Color.BOLD, 'Enlace correcto.')}")
        if local_ip:
            print(f"     Local: {local_ip}   Remoto: {args.ip}")
        return 0

    print(
        f"[FALLO] {Color.wrap(Color.RED + Color.BOLD, 'No se pudo establecer comunicación.')}"
    )
    for hint in diagnose(state):
        print(f"    {hint}")
    return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="link_check.py",
        description=(
            "Asistente para prácticas de redes. Verifica el enlace físico y lógico"
            " entre dos equipos. Pensado para cables UTP directos (cruzados o no);"
            " futuras versiones permitirán enlaces a través de un switch."
            " Admite asignación automática de IP link-local (169.254.x.y/16)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  python link_check.py --assign-ip\n"
            "  python link_check.py 169.254.42.10\n"
            "  python link_check.py --assign-ip 169.254.42.10\n"
            "  python link_check.py -i enp0s3 169.254.42.10 -c 8 -v\n"
        ),
    )
    p.add_argument(
        "ip", nargs="?", help="IP del otro extremo al que hacer ping (opcional)."
    )
    p.add_argument(
        "-i",
        "--interface",
        default=None,
        help="Fuerza una interfaz específica (por defecto autodetecta).",
    )
    p.add_argument(
        "--assign-ip",
        action="store_true",
        help="Asigna una IP link-local 169.254.x.y/16 a la interfaz.",
    )
    p.add_argument(
        "-c",
        "--count",
        type=int,
        default=COUNT_DEFAULT,
        help=f"Número de pings (default {COUNT_DEFAULT}).",
    )
    p.add_argument(
        "-W",
        "--timeout",
        type=int,
        default=TIMEOUT_DEFAULT,
        help=f"Timeout por ping en segundos (default {TIMEOUT_DEFAULT}).",
    )
    p.add_argument(
        "-v", "--verbose", action="store_true", help="Muestra la salida cruda del ping."
    )
    p.add_argument(
        "--no-color", action="store_true", help="Desactiva los códigos de color ANSI."
    )
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.no_color:
        Color.disable()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
