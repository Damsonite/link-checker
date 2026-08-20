"""Constantes compartidas por el paquete."""
import platform
import re

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
