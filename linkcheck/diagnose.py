"""Mensajes de diagnóstico a partir del estado del enlace."""
from .constants import IS_WINDOWS


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


def admin_hint() -> str:
    """Mensaje sobre cómo elevar permisos según la plataforma."""
    return "Ejecuta PowerShell como Administrador." if IS_WINDOWS else "Ejecuta con sudo."


__all__ = ["diagnose", "admin_hint"]
