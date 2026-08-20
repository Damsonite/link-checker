"""Wrapper alrededor de subprocess.run que muestra los comandos externos."""
import shlex
import subprocess


def run_visible(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Imprime el comando que se va a ejecutar y lo delega a subprocess.run.

    Útil para que el usuario vea qué está haciendo el script por debajo
    (netsh, ip addr, ping, …). Los argumentos se quotan con shlex.quote
    para que la línea impresa sea apta para copiar y pegar en un shell.
    """
    print(f"[*] Ejecutando: {' '.join(shlex.quote(a) for a in cmd)}")
    return subprocess.run(cmd, **kwargs)


__all__ = ["run_visible"]
