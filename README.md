# Link Checker

Asistente para la Práctica #1 del curso de Redes de Datos de la UPB en las que dos
equipos se conectan directamente con un cable UTP. Detecta la interfaz Ethernet,
asigna (opcionalmente) una IP link-local `169.254.x.y/16` y comprueba que el otro
extremo responda al ping.

## Requisitos

- Python 3.10 o superior.
- Dependencia: `psutil` (ver `requirements.txt`).
- Permisos de administrador:
  - **Linux**: `sudo` para asignar la IP (no hace falta para hacer ping).
  - **Windows**: ejecutar PowerShell como Administrador.
- **Firewall**: en Windows, desactiva temporalmente el ICMPv4 entrante durante
  la práctica, o permitir ping cuando lo pida el sistema.

## Instalación

```bash
git clone git@github.com:Damsonite/link-checker.git
cd link-checker
pip install -r requirements.txt
```

Si la práctica se ejecuta en máquinas del laboratorio sin acceso a Internet,
se puede preinstalar la dependencia en una imagen o llevarla en un USB:

```bash
pip install --target ./libs psutil
PYTHONPATH=./libs python link_check.py ...
```

## Cómo arrancar

Tienes dos puntos de entrada. Elige según el nivel de control que necesites.

### `start.sh` / `start.bat` (recomendado para la práctica)

Son scripts de auto-arranque que preparan el entorno antes de la práctica:

- Detectan el Python disponible en el sistema.
- Si `psutil` no está instalado, lo instalan con `pip`.
- Si hay permisos de administrador, asignan automáticamente la IP
  link-local a tu interfaz.
- Si no los hay, abren un menú interactivo con hacer ping, re-asignar
  IP, mostrar el Plan B, etc.

```bash
./start.sh              # Linux / macOS
start.bat                # Windows (cmd o PowerShell)
sudo ./start.sh          # Linux / macOS: para que la asignación de IP sea automática
```

> En el laboratorio sin internet, primero instala `psutil` en una
> máquina con red (`pip install -r requirements.txt`) y copia la
> carpeta al equipo del laboratorio. El auto-arranque seguirá
> intentando `pip install`; si falla, mostrará el Plan B.

### `link_check.py` (modo directo)

Para usar el script sin auto-install ni auto-asignación. Útil cuando
ya tienes todo listo o quieres controlar cada paso:

```bash
python link_check.py --assign-ip
python link_check.py 169.254.42.10
```

Equivalente a `python -m linkcheck`.

### Comandos externos visibles

Antes de invocar cada comando del sistema (`netsh`, `ip`, `ping`)
el script imprime la línea exacta que va a ejecutar, por ejemplo:

```
[*] Ejecutando: ip addr add 169.254.194.89/16 dev enp3s0
[*] Ejecutando: ping -c 4 -W 2 169.254.42.10
```

Sirve para que sepas qué hace el script por detrás y puedas replicarlo
a mano si algo falla (consulta el Plan B más abajo).

## Uso rápido

1. **Asigna tu IP link-local** (una sola vez al iniciar la práctica):

   ```bash
   python link_check.py --assign-ip
   ```

   La IP es determinista a partir de la MAC del equipo, así que cada equipo
   obtiene siempre la misma IP al volver a ejecutar el comando.

2. **Mira la IP que te asignó el script** y comunícasela a tu compañero:

   ```bash
   [+] Mi IP: 169.254.142.57/16
   ```

3. **Haz ping al otro extremo** (sustituye por la IP real que te dé tu compañero):

   ```bash
   python link_check.py 169.254.42.10
   ```

## Opciones

| Opción                     | Descripción                                 |
| -------------------------- | ------------------------------------------- |
| `IP` (posicional)          | IP del otro extremo al que hacer ping.      |
| `-i`, `--interface NOMBRE` | Fuerza una interfaz específica.             |
| `--assign-ip`              | Asigna IP link-local a la interfaz.         |
| `-c`, `--count N`          | Número de pings (default 4).                |
| `-W`, `--timeout SEG`      | Timeout por ping en segundos (default 2).   |
| `-v`, `--verbose`          | Muestra la salida cruda del comando `ping`. |
| `--no-color`               | Desactiva el color ANSI en la salida.       |

## Ejemplos

```bash
python link_check.py --assign-ip
python link_check.py 169.254.42.10
python link_check.py --assign-ip 169.254.42.10
python link_check.py -i enp0s3 169.254.42.10 -c 8 -v
```

## Salida esperada (éxito)

```
[+] Asignando IP link-local a enp0s3: 169.254.142.57/16 ...
    [*] Ejecutando: ip addr add 169.254.142.57/16 dev enp0s3
    OK -> 169.254.142.57/16

[+] Interfaz enp0s3: ENLACE UP (1000 Mbps, full-duplex, MTU 1500)
[+] Mi IP: 169.254.142.57/16

[+] Ping a 169.254.42.10 (4 paquetes, timeout 2s)...
    [*] Ejecutando: ping -c 4 -W 2 169.254.42.10
    Enviados: 4   Recibidos: 4   Pérdida: 0.0%
    Latencia: min=0.4 ms  media=0.7 ms  max=1.1 ms

[OK] Enlace correcto.
     Local: 169.254.142.57   Remoto: 169.254.42.10
```

## Errores frecuentes y soluciones

Haz clic en cada error para ver la causa y los pasos de revisión.

<details>
<summary><code>No se detecta enlace físico</code></summary>

- **Causa probable:** Cable mal conectado, mal ponchado o NIC deshabilitada.
- **Qué revisar:**
  - Confirmar que el conector hace "clic" en ambos extremos.
  - Revisar el orden de los hilos (T568A en los dos lados o T568B en los dos lados para cable directo).
  - En Windows, verificar que el adaptador está habilitado.

</details>

<details>
<summary>Enlace UP pero ping al 100% con tiempo agotado</summary>

- **Causa probable:** Firewall del otro extremo o IP mal configurada.
- **Qué revisar:**
  - Desactivar el firewall temporalmente.
  - Confirmar que ambas IPs están en `169.254.0.0/16`.

</details>

<details>
<summary><code>Destination host unreachable</code></summary>

- **Causa probable:** Las IPs no comparten subred o el otro extremo no tiene IP asignada.
- **Qué revisar:**
  - Volver a correr `python link_check.py --assign-ip` en ambos equipos.

</details>

<details>
<summary>Pérdida parcial (0% &lt; x &lt; 100%)</summary>

- **Causa probable:** Cable dañado o con interferencia.
- **Qué revisar:**
  - Rehacer el ponchado.
  - Evitar pasar el cable cerca de fuentes de ruido eléctrico.

</details>

<details>
<summary><code>No se pudo asignar la IP ... Ejecuta con sudo</code></summary>

- **Causa probable:** El script se ejecuta sin permisos.
- **Qué revisar:**
  - Linux: `sudo python link_check.py ...`
  - Windows: PowerShell como Administrador.

</details>

<details>
<summary><code>Falta la dependencia 'psutil'</code></summary>

- **Causa probable:** No se instaló el módulo.
- **Qué revisar:**
  - `pip install -r requirements.txt`.

</details>

## Plan B — Si el script no funciona

Si el script no arranca o no detecta tu interfaz, aún puedes completar la
práctica con los comandos del sistema. Guarda esta sección como referencia.

### Asignar IP link-local manualmente

**Linux:**

```bash
sudo ip addr add 169.254.X.Y/16 dev <interfaz>
```

**Windows (PowerShell como Administrador):**

```powershell
New-NetIPAddress -InterfaceAlias "<interfaz>" -IPAddress 169.254.X.Y -PrefixLength 16
```

Conviene coordinarse con el compañero para que cada uno elija un último octeto
distinto (por ejemplo, A usa `…X.1` y B usa `…X.2`).

### Hacer ping sin el script

**Linux:**

```bash
ping -c 4 -W 2 <IP-vecino>
```

**Windows:**

```cmd
ping -n 4 -w 2000 <IP-vecino>
```

### Diagnosticar la interfaz

**Linux:**

```bash
ip link show <interfaz>
sudo ethtool <interfaz>            # velocidad, dúplex, link detect
ip -s addr show dev <interfaz>     # IPs asignadas, contadores
```

**Windows:**

```powershell
Get-NetAdapter | Format-Table Name, Status, LinkSpeed, MediaType
Get-NetIPAddress -InterfaceAlias "<interfaz>"
```

### Si nada funciona, sigue esta lista en orden

1. **¿Está `psutil`?** → `python3 -c "import psutil"`. Si falla:
   `pip install -r requirements.txt`.
2. **¿Tienes permisos?** → Linux: `sudo`. Windows: PowerShell como Administrador.
3. **¿Aparece `No se detectó ninguna interfaz Ethernet`?** → Confirma que el
   cable está conectado y que la NIC no está deshabilitada.
4. **¿Aparece `ENLACE DOWN`?** → Rehacer el ponchado. Para cable directo entre
   dos PCs, usa **T568A en ambos extremos** o **T568B en ambos extremos**.
5. **¿`ENLACE UP` pero ping al 100%?** → Firewall. En Windows desactivar
   temporalmente el firewall. En Linux, acepta ICMP con:
   `sudo iptables -I INPUT -p icmp --icmp-type echo-request -j ACCEPT`.
6. **¿`Destination host unreachable`?** → Confirma que ambas IPs están en
   `169.254.0.0/16`.

## Notas para la práctica

- Las IPs `169.254.x.y` se llaman **APIPA / link-local**. Se usan solo cuando
  no hay servidor DHCP en la red, como en este caso.
- El script **no modifica un enlace ya existente**. Si necesitas reasignar,
  elimina primero la IP manualmente:
  - Linux: `sudo ip addr del 169.254.X.Y/16 dev <interfaz>`
  - Windows: `netsh interface ip set address name="<interfaz>" dhcp`
- Exit codes: `0` si el ping fue exitoso, `1` si falló, `2` si el script
  no pudo ejecutarse (falta de permisos, dependencia ausente, etc.).
  Útil para automatizar la calificación.
