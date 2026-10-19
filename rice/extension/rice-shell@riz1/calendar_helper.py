"""Upcoming timed events for the Rice Bar capsule.

Reads the calendars switched on in GNOME Calendar from Evolution Data Server,
like the clock widget does, and skips cancelled events and ones you declined
(the top bar's own calendar server shows those). Prints one JSON object per
line, {"events": [{"title", "start", "end"}]} with times in ms since the epoch,
every minute, and exits when the extension closes stdin.
"""
import datetime
import json
import re
import sys
import threading
import urllib.parse

try:
    import gi
    gi.require_version("ECal", "2.0")
    gi.require_version("EDataServer", "1.2")
    gi.require_version("ICalGLib", "3.0")
    from gi.repository import ECal, EDataServer, GLib, ICalGLib
except (ImportError, ValueError):
    ECal = None

REFRESH_SECONDS = 60
HOURS_AHEAD = 24


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


def google_calendar_id(source):
    """The calendar id of a Google CalDAV calendar, else None."""
    if not source.has_extension(EDataServer.SOURCE_EXTENSION_WEBDAV_BACKEND):
        return None
    uri = source.get_extension(EDataServer.SOURCE_EXTENSION_WEBDAV_BACKEND).dup_uri()
    if not uri or uri.get_host() != "apidata.googleusercontent.com":
        return None
    match = re.match(r"/caldav/v2/([^/]+)/", uri.get_path())
    return urllib.parse.unquote(match.group(1)) if match else None


class Calendars:
    def __init__(self):
        self._registry = EDataServer.SourceRegistry.new_sync(None)
        self._clients = {}  # source uid -> (ECal.Client, the account's email)

    def _client(self, source):
        uid = source.get_uid()
        if uid not in self._clients:
            client = ECal.Client.connect_sync(source, ECal.ClientSourceType.EVENTS, 10, None)
            _, email = client.get_backend_property_sync(ECal.BACKEND_PROPERTY_CAL_EMAIL_ADDRESS, None)
            self._clients[uid] = (client, (email or "").lower())
        return self._clients[uid]

    def events(self, start, end):
        events = []
        for source in self._registry.list_enabled(EDataServer.SOURCE_EXTENSION_CALENDAR):
            if not source.get_extension(EDataServer.SOURCE_EXTENSION_CALENDAR).get_selected():
                continue

            def add(icomp, instance_start, instance_end, *_):
                if (not instance_start.is_date() and icomp.get_status() != ICalGLib.PropertyStatus.CANCELLED
                        and not declined(icomp, me)):
                    begin = ical_ms(instance_start)
                    events.append({
                        "title": icomp.get_summary() or "(No title)",
                        "start": begin,
                        "end": ical_ms(instance_end) if instance_end else begin,
                    })
                return True

            try:
                client, email = self._client(source)
                # On a Google secondary calendar the reply that counts is the calendar's own.
                calendar_id = google_calendar_id(source)
                me = calendar_id.lower() if calendar_id else email
                client.generate_instances_sync(start, end, None, add)
            except GLib.Error as e:
                self._clients.pop(source.get_uid(), None)
                print(f"calendar {source.get_display_name()}: {e.message}", file=sys.stderr, flush=True)
        events.sort(key=lambda e: e["start"])
        return events


def main():
    stop = threading.Event()

    def watch_stdin():
        sys.stdin.read()
        stop.set()

    threading.Thread(target=watch_stdin, daemon=True).start()

    calendars = None
    if ECal:
        try:
            calendars = Calendars()
        except GLib.Error as e:
            print(f"no calendars: {e.message}", file=sys.stderr, flush=True)

    while not stop.is_set():
        events = []
        if calendars:
            now = datetime.datetime.now()
            start = int((now - datetime.timedelta(hours=1)).timestamp())
            events = calendars.events(start, start + (HOURS_AHEAD + 1) * 3600)
        sys.stdout.write(json.dumps({"events": events}) + "\n")
        sys.stdout.flush()
        stop.wait(REFRESH_SECONDS)


if __name__ == "__main__":
    main()
