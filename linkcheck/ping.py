"""Parser de la salida cruda del comando ping."""
import re


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
