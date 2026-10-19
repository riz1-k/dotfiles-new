"""Backend for the Clock + Weather widget.

Fetches the forecast from Open-Meteo (no API key) and reads GNOME's clock
format and the locale's first weekday, so the widget matches the top bar.
Events come from Evolution Data Server, where GNOME Online Accounts syncs
Google Calendar (needs gir1.2-ecal-2.0; without it the widget hides them),
and so do Google Tasks, which the widget shows as reminders and can tick off.
Event and meeting links are opened from here, in the browser named by the
`browser` config (a desktop file id; empty means the default browser):
Gtk4-DING asks for confirmation every time a widget opens a link itself.

Gtk4-DING starts this when the widget appears and talks to it with one JSON
object per line: hello/request/shutdown arrive on stdin, and response/event
messages go back on stdout.
"""
import base64
import datetime
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request

try:
    import gi
    gi.require_version("ECal", "2.0")
    gi.require_version("EDataServer", "1.2")
    gi.require_version("ICalGLib", "3.0")
    from gi.repository import ECal, EDataServer, GLib, ICalGLib
except (ImportError, ValueError):
    ECal = None

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_PLACE = {"place": "Bengaluru", "latitude": 12.9716, "longitude": 77.5946}
DEFAULT_REFRESH_MIN = 15
RETRY_SECONDS = 60
HOURS_AHEAD = 12
CALENDAR_REFRESH_SECONDS = 60

# Video calls in an event's location, description or Google's conference data.
MEETING_LINK = re.compile(r"https://(?:meet\.google\.com/[a-z]+-[a-z]+-[a-z]+"
                          r"|(?:[\w-]+\.)?zoom\.us/j/[^\s<>\"'\\]+"
                          r"|teams\.(?:microsoft|live)\.com/[^\s<>\"'\\]+)")
OPENABLE_LINK = re.compile(r"https://(?:calendar|tasks)\.google\.com/|" + MEETING_LINK.pattern)

_write_lock = threading.Lock()


def send(message):
    with _write_lock:
        sys.stdout.write(json.dumps(message) + "\n")
        sys.stdout.flush()


def run(*argv):
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=5,
                              stdin=subprocess.DEVNULL).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def read_clock_settings():
    clock_format = run("gsettings", "get", "org.gnome.desktop.interface", "clock-format")
    show_seconds = run("gsettings", "get", "org.gnome.desktop.interface", "clock-show-seconds")
    # glibc gives the first weekday as an offset from a reference date (a Sunday in en_US).
    first_weekday = 0
    try:
        origin = datetime.datetime.strptime(run("locale", "week-1stday"), "%Y%m%d").date()
        offset = int(run("locale", "first_weekday")) - 1
        first_weekday = (origin.isoweekday() + offset) % 7  # 0 = Sunday
    except ValueError:
        pass
    return {
        "use24h": clock_format != "'12h'",
        "showSeconds": show_seconds == "true",
        "firstWeekday": first_weekday,
    }


def fetch_forecast(latitude, longitude):
    query = urllib.parse.urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,is_day,wind_speed_10m",
        "hourly": "temperature_2m,weather_code,precipitation_probability,is_day",
        "daily": "temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_probability_max",
        "timezone": "auto",
        "timeformat": "unixtime",
        "forecast_days": 2,
    })
    request = urllib.request.Request(f"{FORECAST_URL}?{query}", headers={"User-Agent": "riz1-desktop-widgets"})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)

    current = data["current"]
    daily = data["daily"]
    hourly = data["hourly"]
    now = time.time()
    # From the current hour, which the widget shows as "Now".
    upcoming = [i for i, t in enumerate(hourly["time"]) if t > now - 3600][:HOURS_AHEAD]
    return {
        "current": {
            "temp": current["temperature_2m"],
            "feels": current["apparent_temperature"],
            "humidity": current["relative_humidity_2m"],
            "wind": current["wind_speed_10m"],
            "code": current["weather_code"],
            "isDay": bool(current["is_day"]),
        },
        "today": {
            "max": daily["temperature_2m_max"][0],
            "min": daily["temperature_2m_min"][0],
            "rain": daily["precipitation_probability_max"][0],
            "sunrise": daily["sunrise"][0] * 1000,
            "sunset": daily["sunset"][0] * 1000,
        },
        # A few extra hours so the widget can drop past ones between refreshes.
        "hourly": [{
            "time": hourly["time"][i] * 1000,
            "temp": hourly["temperature_2m"][i],
            "code": hourly["weather_code"][i],
            "isDay": bool(hourly["is_day"][i]),
            "rain": hourly["precipitation_probability"][i],
        } for i in upcoming],
    }


def ical_ms(t):
    """An ICalGLib.Time in ms since the epoch. Dates and floating times are local."""
    if t.is_date():
        return int(datetime.datetime(t.get_year(), t.get_month(), t.get_day()).timestamp() * 1000)
    zone = t.get_timezone()
    if zone:
        return t.as_timet_with_zone(zone) * 1000
    if t.is_utc():
        return t.as_timet() * 1000
    local = datetime.datetime(t.get_year(), t.get_month(), t.get_day(),
                              t.get_hour(), t.get_minute(), t.get_second())
    return int(local.timestamp() * 1000)


def declined(icomp, email):
    attendee = icomp.get_first_property(ICalGLib.PropertyKind.ATTENDEE_PROPERTY)
    while attendee:
        if email and attendee.get_attendee().lower() == f"mailto:{email}":
            partstat = attendee.get_first_parameter(ICalGLib.ParameterKind.PARTSTAT_PARAMETER)
            return bool(partstat) and partstat.get_partstat() == ICalGLib.ParameterPartstat.DECLINED
        attendee = icomp.get_next_property(ICalGLib.PropertyKind.ATTENDEE_PROPERTY)
    return False


def google_calendar(source):
    """(calendar id, account) for a Google CalDAV calendar, else None."""
    if not source.has_extension(EDataServer.SOURCE_EXTENSION_WEBDAV_BACKEND):
        return None
    uri = source.get_extension(EDataServer.SOURCE_EXTENSION_WEBDAV_BACKEND).dup_uri()
    if not uri or uri.get_host() != "apidata.googleusercontent.com":
        return None
    match = re.match(r"/caldav/v2/([^/]+)/", uri.get_path())
    if not match:
        return None
    return urllib.parse.unquote(match.group(1)), urllib.parse.unquote(uri.get_user() or "")


def google_event_url(icomp, google):
    """The event's page on calendar.google.com. Its eid is base64 of "<event id> <calendar id>",
    and each instance of a recurring event adds its original start to the event id."""
    uid = icomp.get_uid() or ""
    if not google or not uid.endswith("@google.com"):
        return None
    calendar_id, account = google
    event_id = uid.removesuffix("@google.com")
    rid = icomp.get_recurrenceid()
    if rid and not rid.is_null_time():
        if rid.is_date():
            event_id += f"_{rid.get_year():04}{rid.get_month():02}{rid.get_day():02}"
        else:
            utc = datetime.datetime.fromtimestamp(ical_ms(rid) / 1000, datetime.timezone.utc)
            event_id += utc.strftime("_%Y%m%dT%H%M%SZ")
    calendar_id = calendar_id.replace("@group.calendar.google.com", "@g").replace("@gmail.com", "@m")
    eid = base64.b64encode(f"{event_id} {calendar_id}".encode()).decode().rstrip("=")
    query = {"eid": eid, "authuser": account} if account else {"eid": eid}
    return f"https://calendar.google.com/calendar/event?{urllib.parse.urlencode(query)}"


def google_task_url(source, uid):
    """The task on tasks.google.com, for lists synced from a Google account."""
    parent = source.get_parent()
    if not parent or not source.has_extension(EDataServer.SOURCE_EXTENSION_AUTHENTICATION):
        return None
    account = source.get_extension(EDataServer.SOURCE_EXTENSION_AUTHENTICATION).get_user() or ""
    query = f"?{urllib.parse.urlencode({'authuser': account})}" if account else ""
    return f"https://tasks.google.com/task/{urllib.parse.quote(uid)}{query}"


def meeting_link(icomp):
    # Searching the whole unfolded component finds Google's X-GOOGLE-CONFERENCE too.
    text = icomp.as_ical_string().replace("\r\n ", "").replace("\\n", " ")
    match = MEETING_LINK.search(text)
    return match.group(0) if match else None


def find_desktop_file(app_id):
    data_dirs = [os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")]
    data_dirs += (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")
    for data_dir in data_dirs:
        path = os.path.join(data_dir, "applications", app_id)
        if data_dir and os.path.isfile(path):
            return path
    return None


def open_url(url, browser):
    if not OPENABLE_LINK.match(url):
        raise ValueError(f"not a calendar or meeting link: {url}")
    if browser:
        desktop_file = find_desktop_file(browser)
        if not desktop_file:
            raise ValueError(f"{browser} isn't installed")
        argv = ["gio", "launch", desktop_file, url]
    else:
        argv = ["gio", "open", url]
    # Detached, and with our stdout (the pipe to Gtk4-DING) kept away from the browser.
    subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def event_range():
    """Covers the month grid (which starts up to a week early) and the agenda."""
    first = datetime.date.today().replace(day=1)
    start = datetime.datetime.combine(first - datetime.timedelta(days=7), datetime.time())
    return int(start.timestamp()), int((start + datetime.timedelta(days=56)).timestamp())


class Calendars:
    """Events from the calendars switched on in GNOME Calendar, like the top bar's date menu,
    and the open tasks with a due date from the task lists switched on in Evolution/Endeavour."""

    def __init__(self):
        self._registry = EDataServer.SourceRegistry.new_sync(None)
        self._clients = {}  # source uid -> (ECal.Client, the account's email)
        # The refresh loop and the widget's requests share the clients.
        self._lock = threading.Lock()

    def _client(self, source, kind=ECal.ClientSourceType.EVENTS if ECal else None):
        uid = source.get_uid()
        if uid not in self._clients:
            client = ECal.Client.connect_sync(source, kind, 10, None)
            _, email = client.get_backend_property_sync(ECal.BACKEND_PROPERTY_CAL_EMAIL_ADDRESS, None)
            self._clients[uid] = (client, (email or "").lower())
        return self._clients[uid]

    def tasks(self):
        """Open tasks that have a due date. Undated ones are lists (shopping), not reminders."""
        with self._lock:
            tasks = []
            for source in self._registry.list_enabled(EDataServer.SOURCE_EXTENSION_TASK_LIST):
                task_list = source.get_extension(EDataServer.SOURCE_EXTENSION_TASK_LIST)
                if not task_list.get_selected():
                    continue
                try:
                    client, _ = self._client(source, ECal.ClientSourceType.TASKS)
                    _, comps = client.get_object_list_as_comps_sync("(not (is-completed?))", None)
                except GLib.Error as e:
                    self._clients.pop(source.get_uid(), None)
                    send({"type": "log", "level": "warn", "message": f"tasks {source.get_display_name()}: {e.message}"})
                    continue
                for comp in comps:
                    icomp = comp.get_icalcomponent()
                    due = icomp.get_due()
                    if not due or due.is_null_time() or icomp.get_status() == ICalGLib.PropertyStatus.CANCELLED:
                        continue
                    tasks.append({
                        "uid": icomp.get_uid(),
                        "list": source.get_uid(),
                        "listName": source.get_display_name(),
                        "title": icomp.get_summary() or "(No title)",
                        # Google Tasks only keeps the day, so a due time would be noise.
                        "due": ical_ms(due) if due.is_date() else int(datetime.datetime.fromtimestamp(
                            ical_ms(due) / 1000).replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000),
                        "color": task_list.get_color(),
                        "url": google_task_url(source, icomp.get_uid()),
                    })
            tasks.sort(key=lambda t: (t["due"], t["title"]))
            return tasks

    def set_task_done(self, list_uid, uid, done=True):
        """Ticks a task off (or back on); EDS writes it through to Google Tasks."""
        with self._lock:
            source = self._registry.ref_source(list_uid)
            if not source or not source.has_extension(EDataServer.SOURCE_EXTENSION_TASK_LIST):
                raise ValueError(f"no task list {list_uid}")
            client, _ = self._client(source, ECal.ClientSourceType.TASKS)
            try:
                _, icomp = client.get_object_sync(uid, None, None)
                comp = ECal.Component.new_from_icalcomponent(icomp)
                if done:
                    comp.set_status(ICalGLib.PropertyStatus.COMPLETED)
                    comp.set_completed(ICalGLib.Time.new_current_with_zone(ICalGLib.Timezone.get_utc_timezone()))
                    comp.set_percent_complete(100)
                else:
                    comp.set_status(ICalGLib.PropertyStatus.NEEDSACTION)
                    comp.set_completed(None)
                    comp.set_percent_complete(0)
                client.modify_object_sync(comp.get_icalcomponent(), ECal.ObjModType.THIS,
                                          ECal.OperationFlags.NONE, None)
            except GLib.Error as e:
                raise ValueError(e.message) from e

    def events(self, start, end):
        """Every instance overlapping [start, end), in seconds since the epoch."""
        with self._lock:
            return self._events(start, end)

    def _events(self, start, end):
        events = []
        selected = set()
        for source in self._registry.list_enabled(EDataServer.SOURCE_EXTENSION_CALENDAR):
            calendar = source.get_extension(EDataServer.SOURCE_EXTENSION_CALENDAR)
            if not calendar.get_selected():
                continue
            selected.add(source.get_uid())
            google = google_calendar(source)

            def add(icomp, instance_start, instance_end, *_):
                if icomp.get_status() != ICalGLib.PropertyStatus.CANCELLED and not declined(icomp, me):
                    begin = ical_ms(instance_start)
                    events.append({
                        "start": begin,
                        "end": ical_ms(instance_end) if instance_end else begin,
                        "allDay": instance_start.is_date(),
                        # Instances of a repeating event carry the start they repeat from.
                        "recurring": bool(icomp.get_recurrenceid() and not icomp.get_recurrenceid().is_null_time()),
                        "title": icomp.get_summary() or "(No title)",
                        "location": icomp.get_location(),
                        "calendar": source.get_display_name(),
                        "color": calendar.get_color(),
                        "url": google_event_url(icomp, google),
                        "meeting": meeting_link(icomp),
                    })
                return True

            try:
                client, email = self._client(source)
                # Who the calendar belongs to. On a Google secondary calendar that's the
                # calendar itself, as on calendar.google.com: the account's own reply to
                # an event there only hides the copy on its primary calendar.
                me = google[0].lower() if google else email
                client.generate_instances_sync(start, end, None, add)
            except GLib.Error as e:
                # Reconnect next time: the calendar's backend may have restarted.
                self._clients.pop(source.get_uid(), None)
                send({"type": "log", "level": "warn", "message": f"calendar {source.get_display_name()}: {e.message}"})
        task_lists = {s.get_uid() for s in self._registry.list_enabled(EDataServer.SOURCE_EXTENSION_TASK_LIST)}
        for uid in self._clients.keys() - selected - task_lists:
            del self._clients[uid]
        events.sort(key=lambda e: (e["start"], not e["allDay"], e["title"]))
        return events


class Backend:
    def __init__(self):
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._lock = threading.Lock()
        self._location = dict(DEFAULT_PLACE)
        self._refresh_seconds = DEFAULT_REFRESH_MIN * 60
        self._state = {"weather": None, "error": None, "updatedAt": 0}
        self._events = None  # None until the first read, or with no calendar support
        self._tasks = None
        self._calendars = None
        self._calendar_wake = threading.Event()
        self._browser = ""
        self._thread = None

    def snapshot(self):
        with self._lock:
            return dict(self._state, place=self._location["place"], clock=read_clock_settings(),
                        events=self._events, tasks=self._tasks)

    def _refresh(self):
        try:
            weather = fetch_forecast(self._location["latitude"], self._location["longitude"])
        except (OSError, ValueError, KeyError, IndexError) as e:
            # Keep showing the last forecast; the widget marks it as stale.
            with self._lock:
                self._state["error"] = "Weather unavailable"
            send({"type": "log", "level": "warn", "message": f"forecast: {e}"})
            return False
        with self._lock:
            self._state = {"weather": weather, "error": None, "updatedAt": int(time.time() * 1000)}
        return True

    def _refresh_loop(self):
        while not self._stop.is_set():
            ok = self._refresh()
            send({"type": "event", "name": "weather", "payload": self.snapshot()})
            self._wake.wait(self._refresh_seconds if ok else RETRY_SECONDS)
            self._wake.clear()

    def _calendar_loop(self):
        # Evolution Data Server keeps a local copy and syncs with Google itself,
        # so reading it every minute is cheap.
        try:
            self._calendars = Calendars()
        except GLib.Error as e:
            send({"type": "log", "level": "warn", "message": f"calendar: {e.message}"})
            return
        while not self._stop.is_set():
            events = self._calendars.events(*event_range())
            tasks = self._calendars.tasks()
            with self._lock:
                changed = events != self._events or tasks != self._tasks
                self._events = events
                self._tasks = tasks
            if changed:
                send({"type": "event", "name": "weather", "payload": self.snapshot()})
            self._calendar_wake.wait(CALENDAR_REFRESH_SECONDS)
            self._calendar_wake.clear()

    def _request(self, method, params):
        if method in ("getWeather", "refresh"):
            if method == "refresh":
                self._wake.set()
                self._calendar_wake.set()
            return self.snapshot()
        if method == "events":
            # Another month in the calendar, in ms like the events themselves.
            if not self._calendars:
                return None
            return self._calendars.events(int(params["start"]) // 1000, int(params["end"]) // 1000)
        if method == "setTaskDone":
            if not self._calendars:
                raise ValueError("no calendar support")
            self._calendars.set_task_done(str(params["list"]), str(params["uid"]), bool(params.get("done", True)))
            self._calendar_wake.set()  # push the list without it
            return True
        if method == "open":
            open_url(str(params.get("url", "")), self._browser)
            return True
        raise ValueError(f"unknown method {method!r}")

    def _handle(self, message):
        kind = message.get("type")
        if kind == "hello":
            config = message.get("config") or {}
            for key in ("place", "latitude", "longitude"):
                if key in config:
                    self._location[key] = config[key]
            minutes = float(config.get("refreshMin", DEFAULT_REFRESH_MIN))
            self._refresh_seconds = max(5, minutes) * 60
            self._browser = config.get("browser", "")
        elif kind == "request":
            try:
                result = self._request(message.get("method"), message.get("params") or {})
                send({"type": "response", "id": message.get("id"), "ok": True, "result": result})
            except (ValueError, KeyError, TypeError, OSError) as e:
                send({"type": "response", "id": message.get("id"), "ok": False, "error": str(e)})
        elif kind == "shutdown":
            self._stop.set()
            self._wake.set()
            self._calendar_wake.set()

    def run(self):
        while not self._stop.is_set():
            line = sys.stdin.readline()
            if not line:  # host closed our stdin
                break
            try:
                self._handle(json.loads(line))
            except (ValueError, AttributeError):
                continue
            # Start fetching once hello has set the location.
            if not self._thread:
                self._thread = threading.Thread(target=self._refresh_loop, daemon=True)
                self._thread.start()
                if ECal:
                    # Google task lists only finish connecting once a main loop delivers
                    # their online signal; without one each connect waits out its timeout.
                    threading.Thread(target=GLib.MainLoop().run, daemon=True).start()
                    threading.Thread(target=self._calendar_loop, daemon=True).start()
                else:
                    send({"type": "log", "level": "warn",
                          "message": "calendar: install gir1.2-ecal-2.0 to show events"})
        self._stop.set()
        self._wake.set()
        self._calendar_wake.set()


if __name__ == "__main__":
    Backend().run()
