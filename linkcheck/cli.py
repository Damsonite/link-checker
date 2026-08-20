"""CLI principal: argparse + orquestación del flujo."""
import argparse
import importlib.util
import sys

import psutil

from .colors import Color
from .commands import assign_ip, run_ping
from .constants import COUNT_DEFAULT, TIMEOUT_DEFAULT
from .diagnose import admin_hint, diagnose
from .interfaces import (
    current_ipv4,
    get_mac,
    has_link_local,
    link_local_from_mac,
    pick_active_interface,
    show_interface_status,
)


def _print_interfaces() -> None:
    print("[ERROR] No se detectó ninguna interfaz Ethernet.")
    print("        Interfaces disponibles:")
    for n in psutil.net_if_stats().keys():
        print(f"          - {n}")
    print("        Usa -i NOMBRE para especificar una manualmente.")


def run(args: argparse.Namespace) -> int:
    iface = pick_active_interface(args.interface)
    if not iface:
        _print_interfaces()
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
                print(f"        {admin_hint()}")
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


def _check_psutil() -> bool:
    if importlib.util.find_spec("psutil") is None:
        sys.stderr.write("[ERROR] Falta la dependencia 'psutil'.\n")
        sys.stderr.write("        Ejecuta: pip install -r requirements.txt\n")
        return False
    return True


def main() -> int:
    if not _check_psutil():
        return 2
    args = build_parser().parse_args()
    if args.no_color:
        Color.disable()
    return run(args)
