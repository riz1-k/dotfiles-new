"""Backend for the GitHub widget.

Asks the GitHub CLI (already logged in, so no token handling here) for the
open pull requests in each configured section (see DEFAULT_SECTIONS), with their
CI and review state, and for what needs you: open pull requests waiting on your
review plus unread @mentions. Links are opened from here, in the browser named by the
`browser` config (a desktop file id, Island by default; empty means the default
browser): Gtk4-DING asks for confirmation every time a widget opens a link itself.

Gtk4-DING starts this when the widget appears and talks to it with one JSON
object per line: hello/request/shutdown arrive on stdin, and response/event
messages go back on stdout.
"""
import datetime
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.parse

DEFAULT_REFRESH_SECONDS = 120
MIN_REFRESH_SECONDS = 60
MAX_ITEMS = 8
DEFAULT_BROWSER = "island-browser.desktop"
# Unread @mentions need every unread notification (hundreds of stale review
# requests sit in front of them), so they are counted less often than the lists.
MENTIONS_EVERY_SECONDS = 600

# Each section is one list in the widget: open pull requests in `repos`, minus
# `excludeAuthors`, narrowed by
#   "bases": [...]         targeting one of these branches
#   "review": true         waiting on your review: requested from you personally, not drafts
# or by any of
#   "tagged": true         review requested from you personally (not via a team), or @mentions you
#   "mine": true           opened by you
# A pull request is listed once, in the first section it matches.
DEFAULT_SECTIONS = [
    {"title": "Review", "note": "waiting on you", "review": True,
     "url": "https://github.com/pulls/review-requested", "empty": "Nothing waiting on you"},
    {"title": "Infra", "note": "tagged · yours", "tagged": True, "mine": True,
     "repos": ["EliLillyCo/LRL_light_k8s_infra_apps"]},
    {"title": "Smart Product", "note": "dev · qa · main", "bases": ["dev", "qa", "main"],
     "repos": ["EliLillyCo/smart-product-fe", "EliLillyCo/smart-product-be"],
     "excludeAuthors": ["app/dependabot"]},
]

PR_FIELDS = """
    number title url isDraft updatedAt baseRefName
    author { login }
    repository { name nameWithOwner }
    reviewDecision
    commits(last: 1) { nodes { commit { statusCheckRollup { state } } } }
"""


def section_searches(section):
    """The GitHub searches behind a section, each with the reason its matches are listed."""
    scope = " ".join(["is:open is:pr archived:false",
                      *(f"repo:{r}" for r in section.get("repos", [])),
                      *(f"-author:{a}" for a in section.get("excludeAuthors", []))])
    if section.get("review"):
        return [(f"{scope} draft:false user-review-requested:@me", None)]
    if section.get("bases"):
        # Repeated base: qualifiers are ORed.
        return [(" ".join([scope, *(f"base:{b}" for b in section["bases"])]), None)]
    searches = []
    if section.get("tagged"):
        searches += [(f"{scope} user-review-requested:@me", "review requested"),
                     (f"{scope} mentions:@me", "mentioned")]
    if section.get("mine"):
        searches.append((f"{scope} author:@me", None))
    return searches or [(scope, None)]


def build_query(sections):
    searches = "".join(
        f"""
  s{i}_{j}: search(query: {json.dumps(query + " sort:updated-desc")}, type: ISSUE, first: {MAX_ITEMS}) {{
    issueCount
    nodes {{ ... on PullRequest {{ {PR_FIELDS} }} }}
  }}"""
        for i, section in enumerate(sections)
        for j, (query, _) in enumerate(section_searches(section)))
    return f"query {{\n  viewer {{ login }}{searches}\n}}"

_write_lock = threading.Lock()


def send(message):
    with _write_lock:
        sys.stdout.write(json.dumps(message) + "\n")
        sys.stdout.flush()


class GhError(Exception):
    pass


def gh_text(*args):
    try:
        result = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=30,
                                stdin=subprocess.DEVNULL)
    except FileNotFoundError:
        raise GhError("GitHub CLI (gh) isn't installed") from None
    except subprocess.TimeoutExpired:
        raise GhError("GitHub didn't respond") from None
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "auth login" in stderr or "401" in stderr:
            raise GhError("Not logged in: run gh auth login")
        raise GhError(stderr.splitlines()[-1] if stderr else f"gh exited with {result.returncode}")
    return result.stdout


def gh(*args):
    return json.loads(gh_text(*args))


def gh_accounts():
    # Select only public account metadata: never send tokens to the widget.
    return gh("auth", "status", "--hostname", "github.com", "--json", "hosts", "--jq",
              '[.hosts["github.com"][] | {login, active, state}]')


def token_override():
    return next((name for name in ("GH_TOKEN", "GITHUB_TOKEN") if os.environ.get(name)), None)


def count_unread_notifications():
    # GitHub returns at most 50 notifications per page. With one per page, the
    # "last" page link gives the unread count in a single request.
    headers, _, body = re.split(r"(\r?\n){2}", gh_text("api", "--hostname", "github.com", "--include",
                                                   "notifications?per_page=1"), maxsplit=1)
    match = re.search(r'[?&]page=(\d+)>; rel="last"', headers)
    return int(match.group(1)) if match else len(json.loads(body or "[]"))


def count_unread_mentions():
    reasons = gh_text("api", "--hostname", "github.com", "--paginate", "notifications?per_page=100",
                      "--jq", ".[] | .reason")
    return reasons.split().count("mention")


def to_ms(iso):
    return int(datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)


def pull_request(node):
    commits = node.get("commits", {}).get("nodes") or [{}]
    rollup = (commits[0].get("commit") or {}).get("statusCheckRollup") or {}
    return {
        "repo": node["repository"]["name"],
        "fullRepo": node["repository"]["nameWithOwner"],
        "number": node["number"],
        "title": node["title"],
        "url": node["url"],
        "draft": node["isDraft"],
        "base": node.get("baseRefName"),
        "updatedAt": to_ms(node["updatedAt"]),
        "author": (node.get("author") or {}).get("login", "ghost"),
        "checks": rollup.get("state"),
        "review": node.get("reviewDecision"),
    }


def fetch(sections, mentions):
    data = gh("api", "--hostname", "github.com", "graphql", "-f", f"query={build_query(sections)}")["data"]
    login = data["viewer"]["login"]
    results = []
    shown = set()  # listed by an earlier section
    review_requests = 0
    for i, section in enumerate(sections):
        searches = section_searches(section)
        items, seen, total = [], set(), 0
        for j, (_, reason) in enumerate(searches):
            found = data[f"s{i}_{j}"]
            total += found["issueCount"]
            for node in found["nodes"]:
                if not node:
                    continue
                if node["url"] in seen:  # matched by an earlier search too
                    total -= 1
                    continue
                seen.add(node["url"])
                if node["url"] in shown:
                    continue
                pr = pull_request(node)
                items.append(dict(pr, reason=reason, mine=pr["author"] == login))
        shown.update(seen)
        if section.get("review"):
            review_requests = total
        items.sort(key=lambda pr: pr["updatedAt"], reverse=True)
        results.append({
            "title": section.get("title", "Pull requests"),
            "note": section.get("note", ""),
            "url": section.get("url") or "https://github.com/pulls?q=" + urllib.parse.quote(
                searches[0][0] if len(searches) == 1 else f"{searches[0][0].rsplit(' ', 1)[0]} involves:@me"),
            "showBase": bool(section.get("bases")),
            "empty": section.get("empty") or ("Nothing tagged to you" if section.get("tagged") and not section.get("mine")
                                              else "No open pull requests"),
            "total": total,
            "items": items[:MAX_ITEMS],
        })
    return {
        "login": login,
        "notifications": count_unread_notifications(),
        # What the bell counts: open pull requests waiting on your review, and unread @mentions.
        "needsYou": {"reviews": review_requests, "mentions": mentions},
        "sections": results,
    }


def find_desktop_file(app_id):
    data_dirs = [os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")]
    data_dirs += (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")
    for data_dir in data_dirs:
        path = os.path.join(data_dir, "applications", app_id)
        if data_dir and os.path.isfile(path):
            return path
    return None


def open_url(url, browser):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "github.com":
        raise ValueError(f"not a GitHub link: {url}")
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


class Backend:
    def __init__(self):
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._lock = threading.Lock()
        self._refresh_seconds = DEFAULT_REFRESH_SECONDS
        self._browser = DEFAULT_BROWSER
        self._sections = DEFAULT_SECTIONS
        self._state = {"data": None, "error": None, "updatedAt": 0,
                       "accounts": [], "activeLogin": None, "accountError": None, "switchingTo": None}
        self._pending_login = None
        self._thread = None
        self._mentions = None
        self._mentions_at = 0

    def snapshot(self):
        with self._lock:
            return dict(self._state)

    def _queue_switch(self, login):
        # The refresh worker alone runs gh, so switching cannot split a refresh
        # across two accounts. Reply immediately while it finishes any current read.
        with self._lock:
            if self._state["switchingTo"]:
                raise ValueError("An account switch is already in progress")
            if token_override():
                raise ValueError(f"Unset {token_override()} to switch saved gh accounts")
            if not isinstance(login, str) or not any(a["login"] == login for a in self._state["accounts"]):
                raise ValueError("Choose an account saved in gh auth status")
            if login == self._state["activeLogin"]:
                return
            self._pending_login = login
            self._state["switchingTo"] = login
            self._state["error"] = None
        self._wake.set()

    def _set_account(self, login):
        # Also handles switches made in a terminal between widget refreshes.
        with self._lock:
            if login == self._state["activeLogin"]:
                return
            self._state.update(activeLogin=login, data=None, updatedAt=0)
            self._mentions = None
            self._mentions_at = 0

    def _refresh(self):
        with self._lock:
            switching_to = self._pending_login
            self._pending_login = None
        if switching_to:
            try:
                gh_text("auth", "switch", "--hostname", "github.com", "--user", switching_to)
            except GhError as e:
                with self._lock:
                    self._state.update(error=f"Couldn't switch account: {e}", switchingTo=None)
                return
            self._set_account(switching_to)
            with self._lock:
                self._state["accounts"] = [dict(a, active=a["login"] == switching_to)
                                            for a in self._state["accounts"]]
            send({"type": "event", "name": "github", "payload": self.snapshot()})

        try:
            accounts = gh_accounts()
            active = next((a["login"] for a in accounts if a["active"]), None)
            self._set_account(active)
            override = token_override()
            with self._lock:
                self._state.update(accounts=accounts, accountError=(
                    f"Unset {override} to switch saved gh accounts" if override else None))
            # Make the selector usable even if fetching the lists fails.
            send({"type": "event", "name": "github", "payload": self.snapshot()})
        except (GhError, ValueError, KeyError, TypeError) as e:
            with self._lock:
                self._state["accountError"] = f"Couldn't list gh accounts: {e}"

        if not self._mentions_at or time.monotonic() - self._mentions_at >= MENTIONS_EVERY_SECONDS:
            try:
                self._mentions = count_unread_mentions()
                self._mentions_at = time.monotonic()
            except GhError as e:
                send({"type": "log", "level": "warn", "message": f"github mentions: {e}"})
        try:
            data = fetch(self._sections, self._mentions)
        except (GhError, OSError, ValueError, KeyError, TypeError) as e:
            # Keep the last good lists; the widget shows the error above them.
            message = str(e) if isinstance(e, GhError) else "Couldn't read GitHub's reply"
            with self._lock:
                self._state["error"] = message
                if switching_to:
                    self._state["switchingTo"] = None
            send({"type": "log", "level": "warn", "message": f"github: {e}"})
            return
        with self._lock:
            # If a terminal switched accounts during the request, discard cached
            # mentions and avoid attaching them to a different viewer.
            if self._state["activeLogin"] != data["login"]:
                self._mentions = None
                self._mentions_at = 0
                data["needsYou"]["mentions"] = None
            self._state.update(data=data, activeLogin=data["login"], error=None,
                               updatedAt=int(time.time() * 1000))
            if switching_to:
                self._state["switchingTo"] = None

    def _refresh_loop(self):
        while not self._stop.is_set():
            self._wake.clear()
            self._refresh()
            send({"type": "event", "name": "github", "payload": self.snapshot()})
            self._wake.wait(self._refresh_seconds)

    def _handle(self, message):
        kind = message.get("type")
        if kind == "hello":
            config = message.get("config") or {}
            seconds = float(config.get("refreshSec", DEFAULT_REFRESH_SECONDS))
            self._refresh_seconds = max(MIN_REFRESH_SECONDS, seconds)
            self._browser = config.get("browser", DEFAULT_BROWSER)
            self._sections = config.get("sections") or DEFAULT_SECTIONS
        elif kind == "request":
            method = message.get("method")
            params = message.get("params") or {}
            reply = {"type": "response", "id": message.get("id"), "ok": True}
            try:
                if method == "open":
                    open_url(str(params.get("url", "")), self._browser)
                    reply["result"] = True
                elif method in ("getState", "refresh"):
                    if method == "refresh":
                        self._wake.set()
                    reply["result"] = self.snapshot()
                elif method == "switchAccount":
                    self._queue_switch(params.get("login"))
                    reply["result"] = self.snapshot()
                else:
                    raise ValueError(f"unknown method {method!r}")
            except (ValueError, OSError) as e:
                reply = {"type": "response", "id": message.get("id"), "ok": False, "error": str(e)}
            send(reply)
        elif kind == "shutdown":
            self._stop.set()
            self._wake.set()

    def run(self):
        while not self._stop.is_set():
            line = sys.stdin.readline()
            if not line:  # host closed our stdin
                break
            try:
                self._handle(json.loads(line))
            except (ValueError, AttributeError):
                continue
            # Start fetching once hello has set the refresh interval.
            if not self._thread:
                self._thread = threading.Thread(target=self._refresh_loop, daemon=True)
                self._thread.start()
        self._stop.set()
        self._wake.set()


if __name__ == "__main__":
    Backend().run()
