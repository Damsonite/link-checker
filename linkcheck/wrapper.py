"""Wrapper: auto-instala psutil, opcionalmente asigna IP, ofrece menú.

Pensado para ejecutar `./start.sh` o `start.bat`. Delega toda la
lógica real en linkcheck.cli; este módulo sólo orquesta y construye
la CLI de alto nivel.
"""
import argparse
import importlib.util
import os
import subprocess
import sys

from . import cli

IS_WINDOWS = os.name == "nt"
PYTHON_MIN = (3, 10)
ADMIN_HINT = (
    "Abre PowerShell como Administrador." if IS_WINDOWS else "Ejecuta con sudo."
)


def version_str() -> str:
    return ".".join(str(v) for v in sys.version_info[:3])


def has_psutil() -> bool:
    return importlib.util.find_spec("psutil") is not None


def is_admin() -> bool:
    if IS_WINDOWS:
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except (OSError, AttributeError, ImportError):
            return False
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False


def install_psutil() -> tuple[bool, str]:
    print("[INFO] Intentando instalar 'psutil' con pip...")
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "psutil"],
            capture_output=True, text=True, timeout=180,
        )
    except subprocess.TimeoutExpired:
        return False, "pip tardó demasiado"
    except FileNotFoundError:
        return False, "pip no está disponible en este Python"
    if r.returncode == 0:
        return True, "psutil instalado correctamente"
    err = (r.stderr or r.stdout or "").strip()
    return False, (err[:500] if err else f"código de salida {r.returncode}")


def link_check(*args: str) -> int:
    """Delega en linkcheck.cli.main con --no-color activado."""
    return cli.main(["link_check", "--no-color", *args])


_PLAN_B_TEMPLATE = """
============================================================
  PLAN B — Procedimiento manual
============================================================

1. Asignar IP link-local:
{ip_cmd}

2. Hacer ping al otro extremo:
{ping_cmd}

3. Diagnosticar la interfaz:
{diag_cmd}

Para instrucciones completas consulta la sección '## Plan B' del README.md.
============================================================
"""

_PLAN_B_OS = {
    "ip_cmd": (
        "   PowerShell (Administrador):\n"
        '     New-NetIPAddress -InterfaceAlias "<interfaz>" '
        "-IPAddress 169.254.X.Y -PrefixLength 16"
        if IS_WINDOWS else
        "   Linux / macOS:\n"
        "     sudo ip addr add 169.254.X.Y/16 dev <interfaz>"
    ),
    "ping_cmd": (
        "   ping -n 4 -w 2000 <IP-vecino>" if IS_WINDOWS
        else "   ping -c 4 -W 2 <IP-vecino>"
    ),
    "diag_cmd": (
        "   Get-NetAdapter | Format-Table Name, Status, LinkSpeed, MediaType"
        if IS_WINDOWS else
        "   ip link show <interfaz>\n"
        "   sudo ethtool <interfaz>"
    ),
}


def show_plan_b() -> None:
    print(_PLAN_B_TEMPLATE.format(**_PLAN_B_OS))


def cmd_install(_a, _e):
    print(f"[i] Python {version_str()} detectado.")
    if has_psutil():
        print("[OK] psutil ya está instalado.")
        return 0
    ok, msg = install_psutil()
    if ok:
        print(f"[OK] {msg}")
        return 0
    print("[ERROR] No se pudo instalar psutil.")
    print(f"         {msg}")
    show_plan_b()
    return 1


def cmd_status(_a, extras):
    if not has_psutil():
        print("[ERROR] psutil no está instalado. Ejecuta primero: install")
        return 2
    return link_check(*extras)


def cmd_assign(_a, extras):
    if not has_psutil():
        print("[ERROR] psutil no está instalado.")
        return 2
    if not is_admin():
        print("[ERROR] Se requieren permisos de administrador.")
        print(f"        {ADMIN_HINT}")
        return 2
    return link_check("--assign-ip", *extras)


def cmd_ping(args, extras):
    if not has_psutil():
        print("[ERROR] psutil no está instalado.")
        return 2
    if not args.target:
        print("[ERROR] Falta la IP del otro extremo.")
        return 2
    return link_check(args.target, *extras)


def cmd_fallback(_a, _e):
    show_plan_b()
    return 0


SUBCOMMANDS = {
    "install": cmd_install,
    "status": cmd_status,
    "assign": cmd_assign,
    "ping": cmd_ping,
    "fallback": cmd_fallback,
}


def menu_loop() -> int:
    psutil_ok = has_psutil()
    admin_ok = is_admin()

    options = [
        ("1", "Hacer ping al otro extremo", psutil_ok, None),
        ("2", "Ver estado de la interfaz", psutil_ok, None),
        ("3", "Re-asignar IP link-local", psutil_ok, admin_ok),
        ("4", "Mostrar Plan B (procedimiento manual)", True, None),
    ]

    def run(key):
        if key in ("", "0"):
            print("Hasta luego.")
            return False
        match = next((o for o in options if o[0] == key), None)
        if match is None:
            print(f"[ERROR] Opción '{key}' no válida.")
            return True
        _, _, need_psutil, need_admin = match
        if need_psutil and not psutil_ok:
            print("[ERROR] Esta opción requiere psutil.")
            return True
        if need_admin and not admin_ok:
            print("[ERROR] Necesitas permisos de administrador.")
            return True
        if key == "1":
            try:
                target = input("IP del otro extremo: ").strip()
            except (EOFError, KeyboardInterrupt):
                return True
            if not target:
                print("[ERROR] IP vacía.")
                return True
            link_check(target)
        elif key == "2":
            link_check()
        elif key == "3":
            link_check("--assign-ip")
        elif key == "4":
            show_plan_b()
        return True

    while True:
        print()
        print("=" * 60)
        print("  Asistente de prácticas de redes")
        print("=" * 60)
        env = (
            f"psutil OK, {'admin OK' if admin_ok else 'sin permisos de admin'}"
            if psutil_ok else "psutil NO disponible (opciones limitadas)"
        )
        print(f"  Entorno: {env}")
        print("\n¿Qué quieres hacer?")
        for opt in options:
            print(f"  {opt[0]}. {opt[1]}")
        print("  0. Salir\n")

        try:
            choice = input("Opción [0]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo...")
            return 0

        if not run(choice):
            return 0


def bootstrap_and_menu() -> int:
    print(f"[i] Versión de Python: {version_str()}")
    if sys.version_info < PYTHON_MIN:
        wanted = ".".join(str(v) for v in PYTHON_MIN)
        print(f"[!] Se requiere Python {wanted}+.")
        print("    El menú seguirá funcionando pero las opciones automáticas no.")
        show_plan_b()
        return menu_loop()

    if has_psutil():
        print("[OK] psutil ya estaba instalado.")
    else:
        ok, msg = install_psutil()
        if ok:
            print(f"[OK] {msg}")
        else:
            print("[!] No se pudo instalar psutil automáticamente.")
            print(f"    Motivo: {msg}")
            show_plan_b()

    if has_psutil() and is_admin():
        print("\n[INFO] Asignando IP link-local automáticamente...")
        rc = link_check("--assign-ip")
        if rc != 0:
            print(f"[!] La asignación automática de IP falló (código {rc}).")
            print("    Puedes reintentarlo desde la opción 3 del menú.")
    elif has_psutil():
        print("\n[INFO] No detecto permisos de administrador.")
        if IS_WINDOWS:
            print("       Tras abrir PowerShell como Administrador, usa la opción 3.")
        else:
            print("       Para asignar IP automáticamente: sudo ./start.sh")
            print("       O usa la opción 3 del menú tras elevar permisos.")

    return menu_loop()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run.py",
        description=(
            "Asistente para prácticas de redes. Wrapper de link_check.py: "
            "instala dependencias, asigna IP link-local y ofrece un menú interactivo."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Sin subcomando: auto-arranque + menú. "
            "Subcomandos: install, status, assign, ping IP, fallback."
        ),
    )
    sub = p.add_subparsers(dest="command", metavar="SUBCOMANDO")

    for name, help_text in (
        ("install", "Asegura que psutil esté instalado."),
        ("status", "Muestra el estado de la interfaz (sin ping)."),
        ("assign", "Asigna IP link-local 169.254.x.y/16."),
        ("fallback", "Muestra el Plan B (procedimiento manual)."),
    ):
        sub.add_parser(name, help=help_text)

    p_ping = sub.add_parser(
        "ping", help="Hace ping al otro extremo y muestra diagnóstico."
    )
    p_ping.add_argument("target", help="IP del otro extremo.")

    return p


def main() -> int:
    args, extras = build_parser().parse_known_args()
    handler = SUBCOMMANDS.get(args.command)
    if handler:
        return handler(args, extras)
    return bootstrap_and_menu()
