"""Backend for the System Info widget.

Gtk4-DING starts this when the widget appears and talks to it with one JSON
object per line: hello/request/shutdown arrive on stdin, and response/event
messages go back on stdout. Most things are read from /proc and /sys; the
network status comes from nmcli, tailscale and ping, and Bluetooth from
bluetoothctl and pactl, which run in their own threads so a slow one never
holds up the stats.
"""
import collections
import glob
import json
import os
import re
import shutil
import socket
import statistics
import subprocess
import sys
import threading
import time

_write_lock = threading.Lock()


def send(message):
    with _write_lock:
        sys.stdout.write(json.dumps(message) + "\n")
        sys.stdout.flush()


def read_text(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


class CpuSampler:
    def __init__(self):
        self._previous = self._read()

    @staticmethod
    def _read():
        with open("/proc/stat") as f:
            fields = [int(x) for x in f.readline().split()[1:]]
        idle = fields[3] + fields[4]  # idle + iowait
        return idle, sum(fields)

    def sample(self):
        idle, total = self._read()
        previous_idle, previous_total = self._previous
        self._previous = (idle, total)
        elapsed = total - previous_total
        if elapsed <= 0:
            return 0.0
        return 1 - (idle - previous_idle) / elapsed


class ProcessSampler:
    """CPU use per process name since the last sample, from /proc/<pid>/stat.

    Names group a program's processes (all of Chrome's are "chrome"); 100 is one
    full core, as in top. Only runs while the machine is busy.
    """

    TICKS = os.sysconf("SC_CLK_TCK")

    def __init__(self):
        self._previous = None

    @staticmethod
    def _read():
        ticks = {}
        for pid in os.listdir("/proc"):
            if not pid.isdigit():
                continue
            try:
                with open(f"/proc/{pid}/stat") as f:
                    stat = f.read()
            except OSError:  # exited since listdir
                continue
            # The name is in parentheses and may itself contain spaces or ")".
            name = stat[stat.index("(") + 1:stat.rindex(")")]
            fields = stat[stat.rindex(")") + 2:].split()
            ticks[pid] = (name, int(fields[11]) + int(fields[12]))  # utime + stime
        return time.monotonic(), ticks

    def reset(self):
        self._previous = None

    def sample(self, top=3):
        now, ticks = self._read()
        previous, self._previous = self._previous, (now, ticks)
        if not previous or now <= previous[0]:
            return None
        elapsed = now - previous[0]
        by_name = collections.defaultdict(lambda: [0.0, 0])
        for pid, (name, total) in ticks.items():
            # A process new since the last sample spent all its time inside this window.
            before = previous[1].get(pid)
            used = max(0, total - before[1]) if before else total
            by_name[name][0] += used / self.TICKS / elapsed * 100
            by_name[name][1] += 1
        ranked = sorted(by_name.items(), key=lambda item: item[1][0], reverse=True)[:top]
        return [{"name": name, "cpu": round(cpu), "processes": count} for name, (cpu, count) in ranked]


class NetSampler:
    """Byte rates summed over physical interfaces (skips lo, tailscale, docker...)."""

    def __init__(self):
        self._previous = self._read()

    @staticmethod
    def _read():
        rx = tx = 0
        with open("/proc/net/dev") as f:
            for line in f.readlines()[2:]:
                name, data = line.split(":", 1)
                name = name.strip()
                if not os.path.exists(f"/sys/class/net/{name}/device"):
                    continue
                fields = data.split()
                rx += int(fields[0])
                tx += int(fields[8])
        return time.monotonic(), rx, tx

    def sample(self):
        now, rx, tx = self._read()
        then, previous_rx, previous_tx = self._previous
        self._previous = (now, rx, tx)
        elapsed = now - then
        if elapsed <= 0:
            return 0, 0
        return max(0, rx - previous_rx) / elapsed, max(0, tx - previous_tx) / elapsed


def read_memory():
    info = {}
    with open("/proc/meminfo") as f:
        for line in f:
            key, value = line.split(":", 1)
            info[key] = int(value.split()[0]) * 1024
    return info["MemTotal"] - info["MemAvailable"], info["MemTotal"]


def read_disk(path="/"):
    st = os.statvfs(path)
    total = st.f_blocks * st.f_frsize
    return total - st.f_bavail * st.f_frsize, total


def read_temperature():
    """CPU package temperature in °C, or None if no sensor is found."""
    for hwmon in glob.glob("/sys/class/hwmon/hwmon*"):
        if read_text(f"{hwmon}/name") not in ("coretemp", "k10temp", "zenpower"):
            continue
        for label_path in sorted(glob.glob(f"{hwmon}/temp*_label")):
            if read_text(label_path) in ("Package id 0", "Tctl", "Tdie"):
                value = read_text(label_path.replace("_label", "_input"))
                if value:
                    return int(value) / 1000
    for zone in glob.glob("/sys/class/thermal/thermal_zone*"):
        if read_text(f"{zone}/type") == "x86_pkg_temp":
            value = read_text(f"{zone}/temp")
            if value:
                return int(value) / 1000
    return None


def read_battery():
    for supply in sorted(glob.glob("/sys/class/power_supply/BAT*")):
        capacity = read_text(f"{supply}/capacity")
        if capacity is not None:
            return {"percent": int(capacity), "status": read_text(f"{supply}/status") or "Unknown"}
    return None


def read_cpu_freq_ghz():
    freqs = []
    for path in glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_cur_freq"):
        value = read_text(path)
        if value:
            freqs.append(int(value))
    return sum(freqs) / len(freqs) / 1e6 if freqs else None


def read_os_name():
    text = read_text("/etc/os-release") or ""
    for line in text.splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip('"')
    return "Linux"


def run(argv, timeout=5):
    """stdout of argv, or None if it is missing, fails or hangs."""
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                                stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def nmcli_rows(*args):
    """nmcli -t output split into fields; -t escapes ':' and '\\' inside values."""
    out = run(["nmcli", "-t", *args]) or ""
    return [[f.replace("\\:", ":").replace("\\\\", "\\")
             for f in re.split(r"(?<!\\):", line)]
            for line in out.splitlines() if line]


class NetworkStatus:
    """What the machine is connected through, polled every few seconds."""

    INTERVAL = 5

    def __init__(self):
        self.latest = {"link": None, "vpn": [], "tailscale": None, "connectivity": None}

    def _link(self):
        devices = nmcli_rows("-f", "DEVICE,TYPE,STATE,CONNECTION", "device")
        connected = {kind: (dev, name) for dev, kind, state, name in devices
                     if state.startswith("connected") and kind in ("ethernet", "wifi")}
        if "ethernet" in connected:
            dev, name = connected["ethernet"]
            speed = read_text(f"/sys/class/net/{dev}/speed")
            return {"kind": "ethernet", "name": "Ethernet", "device": dev,
                    "speedMbps": int(speed) if speed and int(speed) > 0 else None}
        if "wifi" in connected:
            dev, name = connected["wifi"]
            link = {"kind": "wifi", "name": name, "device": dev, "signal": None, "band": None}
            for in_use, ssid, signal, freq in nmcli_rows(
                    "-f", "IN-USE,SSID,SIGNAL,FREQ", "device", "wifi", "list",
                    "ifname", dev, "--rescan", "no"):
                if in_use == "*":
                    mhz = int(freq.split()[0]) if freq else 0
                    link.update(name=ssid or name, signal=int(signal or 0),
                                band="6 GHz" if mhz >= 5925 else "5 GHz" if mhz >= 5000 else "2.4 GHz")
                    break
            return link
        return None

    @staticmethod
    def _vpns():
        return [name for name, kind in nmcli_rows("-f", "NAME,TYPE", "connection", "show", "--active")
                if kind in ("vpn", "wireguard")]

    @staticmethod
    def _tailscale():
        if not shutil.which("tailscale"):
            return None
        out = run(["tailscale", "status", "--json"])
        try:
            status = json.loads(out) if out else None
        except ValueError:
            status = None
        if not status:
            return {"running": False}
        peers = (status.get("Peer") or {}).values()
        exit_node = next((p.get("HostName") for p in peers if p.get("ExitNode")), None)
        return {"running": status.get("BackendState") == "Running",
                "online": sum(1 for p in peers if p.get("Online")),
                "peers": len(peers),
                "exitNode": exit_node}

    def poll(self):
        self.latest = {
            "link": self._link(),
            "vpn": self._vpns(),
            "tailscale": self._tailscale(),
            # NetworkManager's own internet check: full, limited, portal or none.
            "connectivity": (run(["nmcli", "networking", "connectivity"]) or "").strip() or None,
        }

    def loop(self, stop):
        while True:
            self.poll()
            if stop.wait(self.INTERVAL):
                return


class BluetoothStatus:
    """Paired devices from bluetoothctl, with battery, and the audio profile from PipeWire."""

    INTERVAL = 6

    def __init__(self):
        self.latest = None  # None until the first poll, or when there is no adapter

    @staticmethod
    def _info(text):
        fields = {}
        for line in text.splitlines():
            key, sep, value = line.strip().partition(": ")
            if sep:
                fields.setdefault(key, value)
        return fields

    @staticmethod
    def _audio_profiles():
        """Address -> "A2DP · SBC-XQ" or "HFP · mSBC" for connected Bluetooth audio cards."""
        out = run(["pactl", "-f", "json", "list", "cards"])
        try:
            cards = json.loads(out) if out else []
        except ValueError:
            cards = []
        profiles = {}
        for card in cards:
            address = (card.get("properties") or {}).get("api.bluez5.address")
            active = card.get("active_profile")
            if not address or not active or active == "off":
                continue
            description = ((card.get("profiles") or {}).get(active) or {}).get("description") or ""
            match = re.search(r"\((.+?), codec (.+?)\)", description)
            if not match:
                continue
            kind = "A2DP" if "A2DP" in match.group(1) else "HFP" if "HFP" in match.group(1) else match.group(1)
            codec = "mSBC" if match.group(2) == "MSBC" else match.group(2)
            profiles[address.upper()] = f"{kind} · {codec}"
        return profiles

    def poll(self):
        show = run(["bluetoothctl", "show"])
        if not show:
            self.latest = None
            return
        powered = self._info(show).get("Powered") == "yes"
        devices = []
        if powered:
            profiles = self._audio_profiles()
            for line in (run(["bluetoothctl", "devices", "Paired"]) or "").splitlines():
                parts = line.split(" ", 2)
                if len(parts) < 2 or parts[0] != "Device":
                    continue
                info = self._info(run(["bluetoothctl", "info", parts[1]]) or "")
                battery = re.search(r"\((\d+)\)", info.get("Battery Percentage", ""))
                devices.append({
                    "address": parts[1],
                    "name": info.get("Alias") or info.get("Name") or (parts[2] if len(parts) > 2 else parts[1]),
                    "icon": info.get("Icon"),
                    "connected": info.get("Connected") == "yes",
                    "battery": int(battery.group(1)) if battery else None,
                    "profile": profiles.get(parts[1].upper()),
                })
        devices.sort(key=lambda d: (not d["connected"], d["name"].lower()))
        self.latest = {"powered": powered, "devices": devices}

    def loop(self, stop):
        while True:
            self.poll()
            if stop.wait(self.INTERVAL):
                return


class Pinger:
    """Round trips to a public host, to tell a slow or lossy connection from a good one."""

    HOST = "1.1.1.1"
    INTERVAL = 5
    WINDOW = 12  # the last minute

    def __init__(self):
        self._results = collections.deque(maxlen=self.WINDOW)

    def ping(self):
        out = run(["ping", "-n", "-q", "-c", "1", "-W", "2", self.HOST], timeout=4) or ""
        match = re.search(r"= [\d.]+/([\d.]+)/", out)
        self._results.append(float(match.group(1)) if match else None)

    @property
    def latest(self):
        if not self._results:
            return None
        times = [t for t in self._results if t is not None]
        recent = [t for t in list(self._results)[-5:] if t is not None]
        return {
            "host": self.HOST,
            "ms": round(statistics.median(recent)) if recent else None,
            "loss": round(1 - len(times) / len(self._results), 2),
            "samples": len(self._results),
        }

    def loop(self, stop):
        while True:
            self.ping()
            if stop.wait(self.INTERVAL):
                return


HISTORY_LENGTH = 60
# The CPU caption names the busiest program once the machine has been hot for a while.
HOT_CPU = 0.6
HOT_TEMP_C = 80
HOT_FOR_SECONDS = 10
HOG_MIN_CPU = 20  # percent of one core; below this nothing is really to blame


class Backend:
    def __init__(self):
        self._cpu = CpuSampler()
        self._net = NetSampler()
        self._network = NetworkStatus()
        self._pinger = Pinger()
        self._bluetooth = BluetoothStatus()
        self._processes = ProcessSampler()
        self._hot_since = None
        self._os_name = read_os_name()
        self._stop = threading.Event()
        self._interval = 2.0
        # Kept here so the graph is full again when Gtk4-DING reloads the widget page.
        self._cpu_history = collections.deque(maxlen=HISTORY_LENGTH)
        self._stop.wait(0.25)  # give the first CPU and network samples a real time window
        self._latest = self._read_stats()

    def _read_stats(self):
        mem_used, mem_total = read_memory()
        disk_used, disk_total = read_disk()
        down, up = self._net.sample()
        with open("/proc/uptime") as f:
            uptime = float(f.read().split()[0])
        cpu = round(self._cpu.sample(), 3)
        self._cpu_history.append(cpu)
        temp = read_temperature()
        hogs = self._hogs(cpu, temp)
        return {
            "host": socket.gethostname(),
            "os": self._os_name,
            "kernel": os.uname().release,
            "uptime": int(uptime),
            "cpu": cpu,
            "cores": os.cpu_count(),
            "freqGhz": read_cpu_freq_ghz(),
            "memUsed": mem_used,
            "memTotal": mem_total,
            "diskUsed": disk_used,
            "diskTotal": disk_total,
            "tempC": temp,
            "hogs": hogs,
            "battery": read_battery(),
            "netDown": round(down),
            "netUp": round(up),
            "load": os.getloadavg()[0],
            "network": dict(self._network.latest, ping=self._pinger.latest),
            "bluetooth": self._bluetooth.latest,
        }

    def _hogs(self, cpu, temp):
        """The busiest programs while CPU or temperature has stayed high, else None."""
        if cpu < HOT_CPU and (temp is None or temp < HOT_TEMP_C):
            self._hot_since = None
            self._processes.reset()
            return None
        now = time.monotonic()
        if self._hot_since is None:
            self._hot_since = now
        top = self._processes.sample()  # sampled from the start, so there is a window by then
        if now - self._hot_since < HOT_FOR_SECONDS or not top or top[0]["cpu"] < HOG_MIN_CPU:
            return None
        return top

    def _push_loop(self):
        while not self._stop.wait(self._interval):
            self._latest = self._read_stats()
            send({"type": "event", "name": "stats", "payload": self._latest})

    def _handle(self, message):
        kind = message.get("type")
        if kind == "hello":
            config = message.get("config") or {}
            self._interval = max(0.5, float(config.get("intervalSec", self._interval)))
        elif kind == "request":
            if message.get("method") in ("openNetworkSettings", "openBluetoothSettings"):
                link = self._network.latest["link"] or {}
                panel = ("bluetooth" if message["method"] == "openBluetoothSettings"
                         else "network" if link.get("kind") == "ethernet" else "wifi")
                subprocess.Popen(["gnome-control-center", panel], stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True)
                send({"type": "response", "id": message.get("id"), "ok": True, "result": None})
            elif message.get("method") == "getStats":
                result = dict(self._latest, cpuHistory=list(self._cpu_history))
                send({"type": "response", "id": message.get("id"), "ok": True, "result": result})
            else:
                send({"type": "response", "id": message.get("id"), "ok": False,
                      "error": f"unknown method {message.get('method')!r}"})
        elif kind == "shutdown":
            self._stop.set()

    def run(self):
        threading.Thread(target=self._push_loop, daemon=True).start()
        threading.Thread(target=self._network.loop, args=(self._stop,), daemon=True).start()
        threading.Thread(target=self._pinger.loop, args=(self._stop,), daemon=True).start()
        threading.Thread(target=self._bluetooth.loop, args=(self._stop,), daemon=True).start()
        while not self._stop.is_set():
            line = sys.stdin.readline()
            if not line:  # host closed our stdin
                break
            try:
                self._handle(json.loads(line))
            except (ValueError, AttributeError):
                continue
        self._stop.set()


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import rice_theme
    rice_theme.watch(send)
    Backend().run()
