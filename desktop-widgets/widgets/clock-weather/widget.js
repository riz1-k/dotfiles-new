import {connect, ding} from './host.js';

const $ = id => document.getElementById(id);
const pad = n => String(n).padStart(2, '0');

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;
const AHEAD_HOURS = 6;              // forecast columns, and the span of the event track under them
const TRACK_LANES = 2;              // overlapping events stack this deep on the track
const JOIN_LEAD = 10 * MINUTE;      // when a meeting's Join button shows up
const BACKGROUND = 3 * HOUR;        // a live event this long (office hours) yields the focus card
const FOCUS_AHEAD = 18 * HOUR;      // how far ahead the focus card looks for what's next
const IDLE_RESET = 45 * 1000;       // browsing the calendar drifts back to today after this
const REMINDER_DAYS = 7;            // how far ahead the agenda lists reminders
const MAX_REMINDERS = 3;            // before "Show all", room permitting
const MIN_EVENT_ROWS = 3;           // reminders shrink before today's events drop below this
const UNDO_DELAY = 5 * 1000;        // a ticked-off task waits this long before it's saved

// WMO weather codes, as used by Open-Meteo.
const DESCRIPTIONS = {
    0: 'Clear', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast', 45: 'Fog', 48: 'Fog',
    51: 'Light drizzle', 53: 'Drizzle', 55: 'Heavy drizzle', 56: 'Freezing drizzle', 57: 'Freezing drizzle',
    61: 'Light rain', 63: 'Rain', 65: 'Heavy rain', 66: 'Freezing rain', 67: 'Freezing rain',
    71: 'Light snow', 73: 'Snow', 75: 'Heavy snow', 77: 'Snow grains',
    80: 'Light showers', 81: 'Showers', 82: 'Heavy showers', 85: 'Snow showers', 86: 'Snow showers',
    95: 'Thunderstorm', 96: 'Thunderstorm, hail', 99: 'Thunderstorm, hail',
};

function iconKind(code) {
    if (code === 0)
        return 'clear';
    if (code <= 2)
        return 'partly';
    if (code === 45 || code === 48)
        return 'fog';
    if (code >= 51 && code <= 57)
        return 'drizzle';
    if ((code >= 61 && code <= 67) || (code >= 80 && code <= 82))
        return 'rain';
    if ((code >= 71 && code <= 77) || code === 85 || code === 86)
        return 'snow';
    if (code >= 95)
        return 'thunder';
    return 'cloudy';
}

// Weather icons are drawn inline so they take the rice colors from style.css.
const CLOUD = '<circle cx="8" cy="15" r="4"/><circle cx="12.5" cy="11" r="5.5"/>' +
    '<circle cx="17" cy="15" r="4"/><rect x="8" y="13" width="9" height="6"/>';
let maskCount = 0;

function cloud(transform = '') {
    return `<g transform="${transform}"><g class="halo">${CLOUD}</g><g class="cloud">${CLOUD}</g></g>`;
}

function sun(cx, cy, r, inner, outer) {
    const rays = Array.from({length: 8}, (_, i) => {
        const a = (i * Math.PI) / 4;
        const point = d => `${(cx + Math.cos(a) * d).toFixed(2)} ${(cy + Math.sin(a) * d).toFixed(2)}`;
        return `M${point(inner)}L${point(outer)}`;
    }).join('');
    return `<circle class="sun" cx="${cx}" cy="${cy}" r="${r}"/><path class="sun rays" d="${rays}"/>`;
}

function moon(cx, cy, r) {
    const id = `moon-${maskCount++}`;
    return `<mask id="${id}"><rect width="24" height="24" fill="#fff"/>` +
        `<circle cx="${cx + r * 0.55}" cy="${cy - r * 0.55}" r="${r * 0.8}" fill="#000"/></mask>` +
        `<circle class="moon" cx="${cx}" cy="${cy}" r="${r}" mask="url(#${id})"/>`;
}

function icon(code, isDay) {
    const kind = iconKind(code);
    const raised = 'translate(0 -2.5)';
    const parts = {
        clear: () => (isDay ? sun(12, 12, 4.5, 7, 9.5) : moon(12, 12, 7.5)),
        partly: () => (isDay ? sun(8.5, 8.5, 3.3, 5.3, 7.3) : moon(9, 8.5, 5)) +
            cloud('translate(3.5 3.5) scale(0.85)'),
        cloudy: () => cloud(),
        fog: () => '<path class="fog" d="M4 8.5h16M2.5 12.5h19M5 16.5h14"/>',
        drizzle: () => `${cloud(raised)}<path class="rain" d="M8.5 19.5l-.4 1M12.5 19.5l-.4 1M16.5 19.5l-.4 1"/>`,
        rain: () => `${cloud(raised)}<path class="rain" d="M8.5 19l-1 3M12.5 19l-1 3M16.5 19l-1 3"/>`,
        snow: () => `${cloud(raised)}<g class="snow"><circle cx="8" cy="20.5" r="1.2"/>` +
            '<circle cx="12" cy="21.5" r="1.2"/><circle cx="16" cy="20.5" r="1.2"/></g>',
        thunder: () => `${cloud(raised)}<path class="bolt" d="M13.2 14.5l-4 5.5h3l-1.2 3.8 4.6-6h-3.1z"/>`,
    };
    return `<svg viewBox="0 0 24 24">${parts[kind]()}</svg>`;
}

const VIDEO_ICON = '<svg viewBox="0 0 16 16"><rect x="1.5" y="4" width="9" height="8" rx="2"/>' +
    '<path d="M10.5 7.2 14.5 5v6l-4-2.2z"/></svg>';
const BELL_ICON = '<svg viewBox="0 0 16 16"><path d="M4 11.2V7.3a4 4 0 0 1 8 0v3.9l1.2 1.4H2.8z"/>' +
    '<path d="M6.6 14.2a1.5 1.5 0 0 0 2.8 0"/></svg>';
const WARN_ICON = '<svg viewBox="0 0 16 16"><path d="M8 2.3 14.4 13.4H1.6z"/><path d="M8 6.6v3M8 11.5v.1"/></svg>';
const CHECK_ICON = '<svg viewBox="0 0 16 16"><path d="M4.6 8.4 7 10.7l4.5-5.2"/></svg>';

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className)
        node.className = className;
    if (text !== undefined)
        node.textContent = text;
    return node;
}

let state = null;
let clock = {use24h: true, showSeconds: false, firstWeekday: 0};

function formatHourMinute(ms) {
    const date = new Date(ms);
    if (clock.use24h)
        return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
    return `${date.getHours() % 12 || 12}:${pad(date.getMinutes())}`;
}

function formatHour(ms) {
    const hour = new Date(ms).getHours();
    if (clock.use24h)
        return `${pad(hour)}:00`;
    return `${hour % 12 || 12} ${hour < 12 ? 'AM' : 'PM'}`;
}

function formatDuration(ms) {
    const minutes = Math.max(1, Math.round(ms / MINUTE));
    const hours = Math.floor(minutes / 60);
    if (!hours)
        return `${minutes}m`;
    return minutes % 60 ? `${hours}h ${minutes % 60}m` : `${hours}h`;
}

function startOfDay(ms) {
    return new Date(ms).setHours(0, 0, 0, 0);
}

function addDays(ms, days) {
    const date = new Date(ms);
    return new Date(date.getFullYear(), date.getMonth(), date.getDate() + days).getTime();
}

const daysBetween = (from, to) => Math.round((startOfDay(to) - startOfDay(from)) / DAY);
const weekday = ms => new Date(ms).toLocaleDateString(undefined, {weekday: 'short'});
const shortDate = ms => new Date(ms).toLocaleDateString(undefined, {month: 'short', day: 'numeric'});

function dayName(day, now) {
    const days = daysBetween(now, day);
    if (days === 0)
        return 'Today';
    if (days === 1)
        return 'Tomorrow';
    if (days === -1)
        return 'Yesterday';
    return new Date(day).toLocaleDateString(undefined, {weekday: 'long', month: 'short', day: 'numeric'});
}

/* What the calendar shows: the week around `anchor`, or its whole month when expanded,
 * and optionally one selected day whose events the agenda lists. This week, collapsed and
 * with nothing selected, is "home". */
const view = {anchor: 0, selected: null, expanded: false};
let remindersOpen = false;
let idleTimer = 0;

function weekStart(day) {
    return addDays(startOfDay(day), -((new Date(day).getDay() - clock.firstWeekday + 7) % 7));
}

function atHome() {
    return view.selected === null && !view.expanded && !remindersOpen &&
        weekStart(view.anchor) === weekStart(Date.now());
}

function resetView() {
    view.anchor = startOfDay(Date.now());
    view.selected = null;
    view.expanded = false;
    remindersOpen = false;
}

// Any interaction restarts the countdown back to today.
function touch() {
    clearTimeout(idleTimer);
    if (!atHome())
        idleTimer = setTimeout(goHome, IDLE_RESET);
}

function goHome() {
    const back = Math.sign(startOfDay(Date.now()) - view.anchor);
    resetView();
    clearTimeout(idleTimer);
    renderCalendar(back);
    renderAgenda();
}

/* Events. The backend pushes the current month's (state.events); other months are asked
 * for when the calendar shows them, and kept until the next push. */
const monthCache = new Map();

function monthRange(year, month) {
    // The grid starts up to a week before the 1st and runs six weeks.
    return {start: new Date(year, month, -6).getTime(), end: new Date(year, month, 43).getTime()};
}

function requestEvents(start, end) {
    if (ding)
        return ding.backendRequest('events', {start, end});
    return Promise.resolve(fakeEvents(start, end));
}

function monthEvents(year, month) {
    const now = new Date();
    if (year === now.getFullYear() && month === now.getMonth())
        return state?.events ?? null;
    const key = `${year}-${month}`;
    if (!monthCache.has(key)) {
        monthCache.set(key, null);
        const {start, end} = monthRange(year, month);
        requestEvents(start, end).then(events => {
            monthCache.set(key, events ?? []);
            const anchor = new Date(view.anchor);
            if (anchor.getFullYear() === year && anchor.getMonth() === month) {
                renderCalendar();
                renderAgenda();
            }
        }).catch(e => {
            monthCache.delete(key);
            ding?.log(`events failed: ${e?.message ?? e}`);
        });
    }
    return monthCache.get(key);
}

function anchorEvents() {
    const anchor = new Date(view.anchor);
    return monthEvents(anchor.getFullYear(), anchor.getMonth());
}

function overlapping(events, start, end) {
    return (events ?? []).filter(e => e.start < end && Math.max(e.end, e.start + 1) > start);
}

/* Tasks. Open Google Tasks with a due date come with the events; ticking one off waits a
 * few seconds for an Undo before it goes to Google. */
const ticking = new Map();   // task key -> the timer that saves it, while Undo is offered
const ticked = new Set();    // saved as done, hidden until the backend stops listing them

const taskKey = t => `${t.list}/${t.uid}`;

function openTasks() {
    return (state?.tasks ?? []).filter(t => !ticked.has(taskKey(t)));
}

function setTaskDone(task, done) {
    if (ding)
        return ding.backendRequest('setTaskDone', {list: task.list, uid: task.uid, done});
    fakeDone.add(taskKey(task));
    return Promise.resolve(true);
}

function toggleTask(key) {
    if (ticking.has(key)) {
        clearTimeout(ticking.get(key));
        ticking.delete(key);
        renderAgenda();
        return;
    }
    const task = state?.tasks?.find(t => taskKey(t) === key);
    if (!task)
        return;
    ticking.set(key, setTimeout(() => {
        ticking.delete(key);
        ticked.add(key);
        renderCalendar();
        renderAgenda();
        setTaskDone(task, true).catch(e => {
            ticked.delete(key);
            ding?.log(`setTaskDone failed: ${e?.message ?? e}`);
            renderCalendar();
            renderAgenda();
        });
    }, UNDO_DELAY));
    touch();
    renderAgenda();
}

// Day (local midnight) -> the colors of what's on it worth a dot: one-off events and tasks
// due. Repeating events (the daily standup, the gym) would dot nearly every day and say nothing.
function busyDays(events) {
    const days = new Map();
    const mark = (day, color = 'var(--muted)') => {
        const colors = days.get(day) ?? [];
        if (!colors.includes(color))
            colors.push(color);
        days.set(day, colors);
    };
    for (const t of openTasks())
        mark(t.due, t.color);
    for (const e of (events ?? []).filter(e => !e.recurring)) {
        const end = Math.max(e.end, e.start + 1);  // an event ending at midnight doesn't touch the next day
        for (let day = startOfDay(e.start), n = 0; day < end && n < 62; day = addDays(day, 1), n++)
            mark(day, e.color);
    }
    return days;
}

/* Reminders: tasks with a due date, and all-day events (the "Reminder: …" and "⚠️ …" notes,
 * birthdays, trips). They have a day rather than a time, so they say how far off they are. */
const REMINDER_PREFIX = /^\s*(?:reminder|remind me|to-?do|to do)\s*[:\-–—]\s*/i;
const WARN_PREFIX = /^\s*(?:⚠|❗|‼)️?\s*/;

function reminderTitle(title) {
    const warn = WARN_PREFIX.test(title);
    let bare = title.replace(WARN_PREFIX, '').replace(REMINDER_PREFIX, '');
    if (bare !== title)
        bare = bare.charAt(0).toUpperCase() + bare.slice(1);
    return {warn, title: bare || title};
}

// Tasks due in [start, end) (and every overdue one, with overdue) and the all-day events
// that touch it. Overdue first, then by day, tasks before events on the same day; events
// that began before the range (the conference already on) come last, as old news.
function reminders(events, start, end, overdue) {
    const items = openTasks().filter(t => t.due < end && (overdue || t.due >= start))
        .map(t => ({task: t, day: t.due, title: t.title, color: t.color, url: t.url}));
    for (const e of overlapping(events, start, end).filter(e => e.allDay))
        items.push({event: e, day: Math.max(startOfDay(e.start), start), title: e.title, color: e.color, url: e.url});
    const ongoing = item => Boolean(item.event) && item.event.start < start;
    return items.sort((a, b) => ongoing(a) - ongoing(b) || a.day - b.day ||
        Boolean(a.event) - Boolean(b.event) || a.title.localeCompare(b.title));
}

// One phrase for when: "8d overdue", "Today", "Tomorrow", "Mon", "Oct 30", "Until Sat".
function reminderWhen(item, now) {
    const days = daysBetween(now, item.day);
    const last = item.event ? startOfDay(item.event.end - 1) : item.day;
    if (last > item.day && days <= 0)
        return {text: `Until ${daysBetween(now, last) < 7 ? weekday(last) : shortDate(last)}`, tone: ''};
    if (days < 0)
        return {text: days === -1 ? 'Yesterday' : `${-days}d overdue`, tone: 'overdue'};
    if (days === 0)
        return {text: 'Today', tone: 'today'};
    if (days === 1)
        return {text: 'Tomorrow', tone: ''};
    return {text: days < 7 ? weekday(item.day) : shortDate(item.day), tone: ''};
}

function reminderRow(item, now, withWhen = true) {
    const {title, warn} = reminderTitle(item.title);
    const row = el('div', `row reminder ${item.task ? 'task' : 'allday'}`);
    row.dataset.day = item.day;
    row.style.setProperty('--c', item.color ?? 'var(--muted)');
    row.classList.toggle('alert', warn);
    row.title = [item.title, item.task?.listName ?? item.event?.calendar].filter(Boolean).join(' · ');
    if (item.url) {
        row.dataset.url = item.url;
        row.tabIndex = 0;
    }

    const when = reminderWhen(item, now);
    if (when.tone)
        row.classList.add(when.tone);
    let mark;
    let side = el('span', `small side ${when.tone}`, withWhen ? when.text : '');
    if (item.task) {
        const key = taskKey(item.task);
        const done = ticking.has(key);
        row.classList.toggle('done', done);
        row.dataset.task = key;
        mark = el('button', 'mark check');
        mark.innerHTML = CHECK_ICON;
        mark.setAttribute('aria-label', done ? `Undo “${title}”` : `Mark “${title}” done`);
        if (done) {
            side = el('button', 'undo small', 'Undo');
            side.title = 'Keep this task open';
        }
    } else {
        mark = el('span', 'mark glyph');
        mark.innerHTML = warn ? WARN_ICON : BELL_ICON;
    }
    row.append(mark, el('span', 'name', title), side);
    return row;
}

function eventRow(e, now) {
    const row = el('div', 'row event');
    row.dataset.day = startOfDay(e.start);
    row.style.setProperty('--c', e.color ?? 'var(--muted)');
    row.title = [e.title, e.location, e.calendar].filter(Boolean).join(' · ');
    if (e.url) {
        row.dataset.url = e.url;
        row.tabIndex = 0;
    }
    const live = e.start <= now && e.end > now;
    row.classList.toggle('live', live);
    row.classList.toggle('past', e.end <= now);

    const what = el('span', 'what');
    what.append(el('span', 'name', e.title));
    if (e.meeting) {
        const video = el('span', 'video');
        video.innerHTML = VIDEO_ICON;
        what.append(video);
    }
    if (e.location)
        what.append(el('span', 'where', e.location));

    let side;
    if (e.meeting && e.end > now && e.start - now <= JOIN_LEAD) {
        side = el('button', 'join', 'Join');
        side.dataset.url = e.meeting;
        side.title = e.meeting;
    } else if (live) {
        side = el('span', 'mono small note', `${formatDuration(e.end - now)} left`);
    } else if (e.start > now && e.start - now <= HOUR) {
        side = el('span', 'mono small note', `in ${formatDuration(e.start - now)}`);
    } else {
        side = el('span', 'mono small muted', formatDuration(e.end - e.start));
    }
    row.append(el('span', 'dot'), el('span', 'mono small when', formatHourMinute(e.start)), what, side);
    if (live) {
        const progress = el('i', 'progress');
        const fill = el('i');
        fill.style.width = `${((now - e.start) / (e.end - e.start)) * 100}%`;
        progress.append(fill);
        row.append(progress);
    }
    return row;
}

function sectionHead(label, aside, className = '') {
    const head = el('div', `section-head ${className}`);
    head.append(el('span', 'label', label));
    if (aside)
        head.append(aside);
    return head;
}

/* Header: the clock, and the weather now. */
function renderClock(now) {
    let hours = now.getHours();
    let suffix = '';
    if (!clock.use24h) {
        suffix = hours < 12 ? 'AM' : 'PM';
        hours = hours % 12 || 12;
    }
    const seconds = clock.showSeconds ? `:${pad(now.getSeconds())}` : '';
    $('time').textContent = `${clock.use24h ? pad(hours) : hours}:${pad(now.getMinutes())}${seconds}`;
    $('suffix').textContent = suffix;
    $('date').textContent = now.toLocaleDateString(undefined, {weekday: 'long', month: 'long', day: 'numeric'});
}

function hourColumn(h, index) {
    const column = el('div', 'hour');
    const wx = el('span', 'wx');
    wx.innerHTML = icon(h.code, h.isDay);
    column.append(
        el('span', index ? 'mono small muted' : 'small now-label', index ? formatHour(h.time) : 'Now'),
        wx,
        el('span', 'mono temp', `${Math.round(h.temp)}°`),
        el('span', 'mono small rain', h.rain >= 10 ? `${h.rain}%` : ''));
    return column;
}

function renderWeather() {
    const w = state?.weather;
    document.querySelector('.card').classList.toggle('stale', Boolean(state?.error && w));
    if (!w) {
        $('current-desc').textContent = state?.error ?? 'Loading weather…';
        return;
    }
    const {current, today} = w;
    const now = Date.now();
    $('current-icon').innerHTML = icon(current.code, current.isDay);
    $('current-temp').textContent = `${Math.round(current.temp)}°`;
    $('current-desc').textContent = DESCRIPTIONS[current.code] ?? '—';
    // The sun event still to come today: sunset by day, sunrise before dawn.
    const sunEvent = now < today.sunrise ? `↑ ${formatHourMinute(today.sunrise)}`
        : now < today.sunset ? `↓ ${formatHourMinute(today.sunset)}` : '';
    $('current-meta').textContent = state.error
        ? `Offline · ${formatHourMinute(state.updatedAt)}`
        : [`H ${Math.round(today.max)}° L ${Math.round(today.min)}°`, sunEvent].filter(Boolean).join(' · ');
    $('current-meta').title = `${state.place} · feels like ${Math.round(current.feels)}° · ` +
        `sunrise ${formatHourMinute(today.sunrise)}, sunset ${formatHourMinute(today.sunset)}`;

    $('hourly').replaceChildren(...w.hourly.filter(h => h.time > now - HOUR).slice(0, AHEAD_HOURS).map(hourColumn));
}

/* The focus card: what's on now, or next. A long live block (office hours) is background,
 * so the next real thing takes the card; a meeting about to start takes it from anything. */
let focused = null;

function focusEvent(now) {
    const timed = (state?.events ?? []).filter(e => !e.allDay && e.end > now && e.start < now + FOCUS_AHEAD);
    const live = timed.filter(e => e.start <= now).sort((a, b) => b.start - a.start);
    const next = timed.filter(e => e.start > now).sort((a, b) => a.start - b.start)[0];
    const current = live.find(e => e.end - e.start < BACKGROUND);
    if (next && (next.start - now <= JOIN_LEAD || !current))
        return current && next.start - now > JOIN_LEAD ? current : next;
    return current ?? live[0] ?? null;
}

function renderFocus(now) {
    const e = focusEvent(now);
    focused = e;
    const card = $('focus');
    card.hidden = !e;
    if (!e)
        return;
    const live = e.start <= now;
    const days = daysBetween(now, e.start);
    card.style.setProperty('--c', e.color ?? 'var(--accent)');
    card.classList.toggle('live', live);
    card.title = [e.title, e.location, e.calendar].filter(Boolean).join(' · ');
    if (e.url) {
        card.dataset.url = e.url;
        card.tabIndex = 0;
    } else {
        delete card.dataset.url;
        card.removeAttribute('tabindex');
    }

    const kicker = el('div', 'kicker');
    kicker.append(el('span', 'label', live ? 'Now' : days ? dayName(e.start, now) : 'Next'),
        el('span', 'mono countdown', live ? `${formatDuration(e.end - now)} left`
            : days ? formatHourMinute(e.start) : `in ${formatDuration(e.start - now)}`));

    const title = el('div', 'focus-title');
    title.append(el('span', 'name', e.title));
    if (e.meeting) {
        const video = el('span', 'video');
        video.innerHTML = VIDEO_ICON;
        title.append(video);
    }

    const meta = el('div', 'meta small');
    meta.append(el('span', 'mono', `${formatHourMinute(e.start)}–${formatHourMinute(e.end)}`),
        el('span', 'where', [e.location, e.calendar].filter(Boolean).join(' · ')));

    const body = el('div', 'focus-body');
    body.append(kicker, title, meta);
    const parts = [body];
    if (e.meeting && e.start - now <= JOIN_LEAD) {
        const join = el('button', 'join', 'Join');
        join.dataset.url = e.meeting;
        join.title = e.meeting;
        parts.push(join);
    }
    if (live) {
        const progress = el('i', 'progress');
        const fill = el('i');
        fill.style.width = `${((now - e.start) / (e.end - e.start)) * 100}%`;
        progress.append(fill);
        parts.push(progress);
    }
    card.replaceChildren(...parts);
}

/* The event track: the next six hours on the forecast's axis, where each column is centered
 * on its hour, starting with the current one. Just the shape of what's coming; the focus
 * card and the agenda have the names. */
function renderTrack(now) {
    const track = $('track');
    const start = new Date(now).setMinutes(0, 0, 0) - HOUR / 2;
    const end = start + AHEAD_HOURS * HOUR;
    const x = ms => ((Math.min(Math.max(ms, start), end) - start) / (end - start)) * 100;

    const timed = overlapping(state?.events, start, end).filter(e => !e.allDay)
        .sort((a, b) => a.start - b.start || (b.end - b.start) - (a.end - a.start));
    const laneEnds = [];
    const bars = [];
    for (const e of timed) {
        let lane = laneEnds.findIndex(laneEnd => laneEnd <= e.start);
        if (lane === -1) {
            if (laneEnds.length === TRACK_LANES)
                continue;
            lane = laneEnds.push(0) - 1;
        }
        laneEnds[lane] = e.end;
        const left = x(e.start);
        const bar = el('i', 'bar');
        bar.style.cssText = `left:${left}%;width:calc(${Math.max(x(e.end) - left, 1)}% - 2px);top:${lane * 8}px`;
        bar.style.setProperty('--c', e.color ?? 'var(--muted)');
        bar.style.setProperty('--elapsed', `${Math.min(Math.max((now - e.start) / (e.end - e.start), 0), 1) * 100}%`);
        bar.classList.toggle('focused', e === focused);
        bar.classList.toggle('background', e.end - e.start >= BACKGROUND);
        bar.title = `${e.title} · ${formatHourMinute(e.start)}–${formatHourMinute(e.end)}`;
        if (e.url)
            bar.dataset.url = e.url;
        bars.push(bar);
    }
    track.hidden = !state?.events;
    track.style.height = `${Math.max(laneEnds.length, 1) * 8 - 2}px`;
    const nowLine = el('i', 'now-line');
    nowLine.style.left = `${x(now)}%`;
    track.replaceChildren(...bars, nowLine);
}

/* The calendar: this week as a strip, or the month. */
function dayCell(date, {month, withWeekday}) {
    const day = date.getTime();
    const today = startOfDay(Date.now());
    const cell = el('button', 'day');
    cell.dataset.day = day;
    cell.classList.toggle('other', month !== undefined && date.getMonth() !== month);
    cell.classList.toggle('today', day === today);
    cell.classList.toggle('past', day < today);
    cell.classList.toggle('selected', day === view.selected);
    if (withWeekday)
        cell.append(el('span', 'weekday', date.toLocaleDateString(undefined, {weekday: 'narrow'})));
    cell.append(el('span', 'mono number', String(date.getDate())));
    cell.setAttribute('aria-label', date.toLocaleDateString(undefined, {weekday: 'long', month: 'long', day: 'numeric'}));
    cell.setAttribute('aria-pressed', String(day === view.selected));
    return cell;
}

function replay(node, className) {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches)
        return;
    node.classList.remove('from-left', 'from-right', 'fade-in');
    void node.offsetWidth;  // restart the animation
    node.classList.add(className);
}

function renderCalendar(direction = 0) {
    const anchor = new Date(view.anchor);
    const year = anchor.getFullYear();
    const month = anchor.getMonth();
    const busy = busyDays(monthEvents(year, month));

    const cells = [];
    if (view.expanded) {
        const lead = (new Date(year, month, 1).getDay() - clock.firstWeekday + 7) % 7;
        for (let i = 0; i < 7; i++) {
            const weekdayDate = new Date(2026, 0, 4 + ((clock.firstWeekday + i) % 7));  // 4 Jan 2026 is a Sunday
            cells.push(el('span', 'weekday', weekdayDate.toLocaleDateString(undefined, {weekday: 'narrow'})));
        }
        for (let i = 0; i < 42; i++)
            cells.push(dayCell(new Date(year, month, 1 - lead + i), {month}));
    } else {
        const first = weekStart(view.anchor);
        for (let i = 0; i < 7; i++)
            cells.push(dayCell(new Date(addDays(first, i)), {withWeekday: true}));
    }
    for (const cell of cells.filter(c => c.classList.contains('day'))) {
        const dots = el('span', 'dots');
        for (const color of busy.get(Number(cell.dataset.day))?.slice(0, 3) ?? []) {
            const dot = el('i');
            dot.style.setProperty('--c', color);
            dots.append(dot);
        }
        cell.append(dots);
    }

    $('month').textContent = anchor.toLocaleDateString(undefined, {month: 'long', year: 'numeric'});
    $('month-toggle').setAttribute('aria-expanded', String(view.expanded));
    $('month-toggle').title = view.expanded ? 'Show this week' : 'Show the month';
    $('prev').setAttribute('aria-label', view.expanded ? 'Previous month' : 'Previous week');
    $('next').setAttribute('aria-label', view.expanded ? 'Next month' : 'Next week');
    const grid = $('calendar');
    grid.classList.toggle('month', view.expanded);
    grid.classList.toggle('week', !view.expanded);
    grid.replaceChildren(...cells);
    if (direction)
        replay(grid, direction > 0 ? 'from-right' : 'from-left');
    $('today').hidden = atHome();
}

/* The agenda: reminders, then the rest of today and the days after, filling the card;
 * or everything on a selected day. */
function renderAgenda() {
    const now = Date.now();
    const events = state?.events;
    $('agenda').hidden = !events;
    if (!events)
        return;

    const today = startOfDay(now);
    const tomorrow = addDays(today, 1);
    const blocks = [];
    let notes;

    if (view.selected === null) {
        notes = reminders(events, today, addDays(today, REMINDER_DAYS), true);
        const rest = overlapping(events, now, tomorrow).filter(e => !e.allDay && e !== focused);
        const todayLeft = overlapping(events, now, tomorrow).filter(e => !e.allDay && e.start > now).length;
        blocks.push({
            kind: 'today',
            head: sectionHead('Today', el('span', 'small muted', todayLeft ? `${todayLeft} to go` : 'Done')),
            rows: rest.length ? rest.map(e => eventRow(e, now))
                : [el('div', 'row empty small muted', focused ? 'Nothing else today' : 'Nothing else today — enjoy')],
        });
        // Then the days after, as far as the card has room (fitAgenda trims the rest).
        // All-day events in the coming week are already among the reminders.
        for (let day = tomorrow, n = 0; n < 14; day = addDays(day, 1), n++) {
            const dayEvents = events.filter(e => e.start >= day && e.start < addDays(day, 1) &&
                !(e.allDay && day < addDays(today, REMINDER_DAYS)) && e !== focused);
            if (!dayEvents.length)
                continue;
            blocks.push({
                kind: 'later',
                head: sectionHead(dayName(day, now)),
                rows: dayEvents.map(e => (e.allDay
                    ? reminderRow({event: e, day, title: e.title, color: e.color, url: e.url}, now, false)
                    : eventRow(e, now))),
            });
        }
    } else {
        const day = view.selected;
        const dayEvents = anchorEvents();
        if (!dayEvents) {
            notes = [];
            blocks.push({kind: 'one-day', head: sectionHead(dayName(day, now)), rows: [el('div', 'row empty small muted', 'Loading…')]});
        } else {
            notes = reminders(dayEvents, day, addDays(day, 1), false);
            const timed = overlapping(dayEvents, day, addDays(day, 1)).filter(e => !e.allDay);
            const count = timed.length + notes.length;
            const back = el('button', 'small link', 'Back to today');
            back.dataset.home = '1';
            blocks.push({
                kind: 'one-day',
                head: sectionHead(dayName(day, now), el('span', 'small muted', count ? `${count} item${count === 1 ? '' : 's'}` : 'Free day'), 'day-head'),
                rows: timed.length ? timed.map(e => eventRow(e, now))
                    : [el('div', 'row empty small muted', notes.length ? 'No events' : 'Nothing scheduled')],
                after: back,
            });
        }
    }

    if (notes.length) {
        const limit = remindersOpen || view.selected !== null ? Infinity : MAX_REMINDERS;
        const toggle = el('button', 'small link');
        toggle.dataset.toggle = 'reminders';
        blocks.unshift({
            kind: 'reminders',
            head: sectionHead('Reminders', toggle),
            rows: notes.map(item => reminderRow(item, now)),
            limit,
            total: notes.length,
            toggle,
        });
    }

    const list = $('agenda-list');
    list.replaceChildren(...blocks.map(block => {
        const section = el('section', `agenda-section ${block.kind}`);
        section.append(block.head, ...block.rows.slice(0, block.limit ?? Infinity));
        if (block.after)
            section.append(block.after);
        block.node = section;
        return section;
    }));
    fitAgenda(blocks);

    const key = `${view.selected}`;
    if (key !== agendaKey && agendaKey !== null)
        replay($('agenda-body'), 'fade-in');
    agendaKey = key;
}

let agendaKey = null;

// Fills the card and drops what doesn't fit: later days first, then today's events down to
// a few, then reminders down to one, then the rest of today. What's hidden is counted.
function fitAgenda(blocks) {
    const body = $('agenda-body');
    const overflows = () => body.scrollHeight > body.clientHeight + 1;
    const rowsOf = kind => blocks.filter(b => b.kind === kind)
        .flatMap(b => [...b.node.querySelectorAll(':scope > .row')]);
    const notes = blocks.find(b => b.kind === 'reminders');
    const today = blocks.find(b => b.kind === 'today');
    let hiddenToday = 0;

    while (overflows()) {
        const later = rowsOf('later');
        if (later.length) {
            const row = later[later.length - 1];
            const section = row.parentElement;
            row.remove();
            if (!section.querySelector('.row'))
                section.remove();
            continue;
        }
        const todayRows = rowsOf('today').filter(r => r.classList.contains('event'));
        const noteRows = rowsOf('reminders');
        if (todayRows.length > MIN_EVENT_ROWS || (todayRows.length > 1 && (noteRows.length <= 1 || remindersOpen))) {
            todayRows[todayRows.length - 1].remove();
            hiddenToday++;
            continue;
        }
        if (noteRows.length > 1 && !remindersOpen) {
            noteRows[noteRows.length - 1].remove();
            continue;
        }
        break;
    }

    if (notes) {
        const shown = notes.node.querySelectorAll(':scope > .row').length;
        notes.toggle.textContent = remindersOpen ? 'Show less' : shown < notes.total ? `+${notes.total - shown} more` : '';
        notes.toggle.hidden = !remindersOpen && shown >= notes.total;
        notes.node.querySelector('.section-head').append(notes.toggle);
    }
    if (today && hiddenToday) {
        const more = el('button', 'more small', `+${hiddenToday} more today`);
        more.dataset.day = startOfDay(Date.now());
        today.node.append(more);
        // The button itself may not fit; make room for it.
        while (overflows() && rowsOf('today').filter(r => r.classList.contains('event')).length > 1) {
            const rows = rowsOf('today').filter(r => r.classList.contains('event'));
            rows[rows.length - 1].remove();
            more.textContent = `+${++hiddenToday} more today`;
        }
    }
    body.classList.toggle('scrolls', view.selected !== null || remindersOpen);
    updateScrollHint();
}

function updateScrollHint() {
    const body = $('agenda-body');
    body.classList.toggle('more-below', body.scrollTop + body.clientHeight < body.scrollHeight - 1);
}

/* Navigation */
function shift(delta) {
    if (view.expanded) {
        const anchor = new Date(view.anchor);
        view.anchor = new Date(anchor.getFullYear(), anchor.getMonth() + delta, 1).getTime();
        // Back on the current month, its week of interest is today's.
        const now = new Date();
        if (new Date(view.anchor).getMonth() === now.getMonth() && new Date(view.anchor).getFullYear() === now.getFullYear())
            view.anchor = startOfDay(now);
    } else {
        view.anchor = addDays(view.anchor, 7 * delta);
    }
    view.selected = null;
    touch();
    renderCalendar(delta);
    renderAgenda();
}

function toggleMonth() {
    view.expanded = !view.expanded;
    // Collapsing shows the week of the selected day, or of the month's first day.
    if (!view.expanded && view.selected !== null)
        view.anchor = view.selected;
    touch();
    renderCalendar();
    replay($('calendar'), 'fade-in');
    renderAgenda();
}

// Clicking the selected day again goes back to the agenda's usual view.
function selectDay(day, toggle = true) {
    const delta = Math.sign(weekStart(day) - weekStart(view.anchor));
    const sameMonth = new Date(day).getMonth() === new Date(view.anchor).getMonth();
    view.selected = toggle && view.selected === day ? null : day;
    view.anchor = day;
    touch();
    renderCalendar(view.expanded && sameMonth ? 0 : delta);
    renderAgenda();
}

function open(url) {
    if (ding)
        ding.backendRequest('open', {url}).catch(e => ding.log(`open failed: ${e?.message ?? e}`));
    else
        window.open(url, '_blank');
}

$('prev').addEventListener('click', () => shift(-1));
$('next').addEventListener('click', () => shift(1));
$('today').addEventListener('click', goHome);
$('month-toggle').addEventListener('click', toggleMonth);

$('calendar').addEventListener('click', event => {
    const cell = event.target.closest('.day');
    if (cell)
        selectDay(Number(cell.dataset.day));
});

let lastWheel = 0;
$('calendar').addEventListener('wheel', event => {
    event.preventDefault();
    if (Math.abs(event.deltaY) < 4 || event.timeStamp - lastWheel < 250)
        return;
    lastWheel = event.timeStamp;
    shift(Math.sign(event.deltaY));
}, {passive: false});

// Before the document's link handler: the row around a checkbox opens the task.
$('agenda-list').addEventListener('click', event => {
    const button = event.target.closest('.check, .undo, [data-toggle], [data-home], .more');
    if (!button)
        return;
    event.stopPropagation();
    if (button.dataset.toggle) {
        remindersOpen = !remindersOpen;
        touch();
        renderAgenda();
    } else if (button.dataset.home) {
        goHome();
    } else if (button.classList.contains('more')) {
        selectDay(Number(button.dataset.day), false);
    } else {
        toggleTask(button.closest('[data-task]').dataset.task);
    }
});

$('agenda-body').addEventListener('scroll', () => {
    updateScrollHint();
    touch();
});

document.addEventListener('click', event => {
    const target = event.target.closest('[data-url]');
    if (target) {
        event.preventDefault();
        open(target.dataset.url);
    }
});

document.addEventListener('keydown', event => {
    if (event.key === 'Escape')
        goHome();
    else if ((event.key === 'Enter' || event.key === ' ') && event.target.dataset?.url)
        open(event.target.dataset.url);
});

// The agenda is fitted to the card, so refit when the widget is resized.
let resizeFrame = 0;
addEventListener('resize', () => {
    cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(renderAgenda);
});

// The agenda is fitted with the bundled fonts' metrics, so fit again once they're in.
document.fonts?.ready.then(() => renderAgenda());

// Don't jump back to today under the pointer.
document.addEventListener('pointermove', () => idleTimer && touch());

let renderedDay = null;
let renderedHour = null;
let renderedMinute = null;

function render(snapshot) {
    state = snapshot;
    clock = snapshot.clock ?? clock;
    for (const key of ticked) {
        if (!state.tasks?.some(t => taskKey(t) === key))
            ticked.delete(key);
    }
    monthCache.clear();
    renderWeather();
    renderCalendar();
    renderedMinute = null;
    tick();
}

function tick() {
    const now = new Date();
    renderClock(now);
    const day = now.toDateString();
    if (day !== renderedDay) {
        if (renderedDay !== null && atHome())
            resetView();  // past midnight, home follows the new day
        renderedDay = day;
        renderCalendar();
    }
    // Drops hours that have passed between backend refreshes.
    if (now.getHours() !== renderedHour) {
        renderedHour = now.getHours();
        renderWeather();
    }
    // Countdowns, progress and the now line move every minute.
    const minute = Math.floor(now.getTime() / MINUTE);
    if (minute !== renderedMinute) {
        renderedMinute = minute;
        renderFocus(now.getTime());
        renderTrack(now.getTime());
        renderAgenda();
    }
}

function scheduleTick() {
    const interval = clock.showSeconds ? 1000 : MINUTE;
    setTimeout(() => {
        tick();
        scheduleTick();
    }, interval - (Date.now() % interval) + 5);
}

resetView();
tick();
scheduleTick();

/* Preview data (no Gtk4-DING): a plausible week around today, relative to now so the
 * live, soon and Join states all show. */
function fakeEvents(from, to) {
    const midnight = startOfDay(Date.now());
    const url = 'https://calendar.google.com/calendar/event?eid=preview';
    const at = (day, hour, hours, title, calendar, color, extra = {}) => {
        const start = addDays(midnight, day) + hour * HOUR;
        return {start, end: start + hours * HOUR, allDay: false, title, calendar, color, url,
            location: null, meeting: null, recurring: true, ...extra};
    };
    const allDay = (day, days, title, calendar, color) => ({start: addDays(midnight, day),
        end: addDays(midnight, day + days), allDay: true, title, calendar, color, url, location: null, meeting: null});

    const events = [];
    for (let day = -45; day < 75; day++) {
        const weekdayNumber = new Date(addDays(midnight, day)).getDay();
        if (weekdayNumber === 0) {
            events.push(at(day, 10, 3, 'Side project hack', '💡Side Project', '#7bd148'));
            continue;
        }
        if (weekdayNumber === 6) {
            events.push(at(day, 6.5, 1.5, 'Long run', '💪 Workout', '#cc163b'));
            continue;
        }
        if (weekdayNumber % 2)
            events.push(at(day, 6, 2.5, 'MMA Training', '💪 Workout', '#cc163b'));
        events.push(at(day, 9.5, 8.5, 'Office work', '🏢 Work', '#f67f1e', {location: 'Bagmane Tech Park'}),
            at(day, 12, 0.5, 'Internal standup', 'LILLY', '#fa573c'),
            at(day, 17.5, 0.25, 'Client standup', 'LILLY', '#fa573c', {meeting: 'https://meet.google.com/abc-defg-hij'}));
        if (weekdayNumber === 4)
            events.push(at(day, 20, 1, 'Rust course', '📈 extra learning', '#9a9cff'));
    }
    const soon = Math.ceil((Date.now() + 8 * MINUTE) / (5 * MINUTE)) * 5 * MINUTE;
    events.push({start: soon, end: soon + 45 * MINUTE, allDay: false, title: 'Design review with Courtney',
        calendar: '👨‍💻 Freelance', color: '#ffad46', url, location: null, meeting: 'https://us02web.zoom.us/j/81234567890', recurring: false});
    events.push(allDay(0, 3, 'Q4 planning week', '🏢 Work', '#f67f1e'),
        allDay(12, 1, 'Bus to Calicut', 'rizwan.k.off@gmail.com', '#b99aff'),
        allDay(19, 1, 'Mom’s birthday', 'Birthdays & Anniversaries', '#ffbe6f'),
        allDay(1, 1, 'Reminder: finish CATS PRD ASG → Karpenter migration (ASG decom Mon 19 Oct)', 'LILLY', '#fa573c'),
        allDay(4, 1, '⚠️ CATS PRD ASG decommissioned today – migrate to Karpenter', 'LILLY', '#fa573c'));
    return overlapping(events, from, to).sort((a, b) => a.start - b.start || b.allDay - a.allDay);
}

const fakeDone = new Set();

function fakeTasks() {
    const midnight = startOfDay(Date.now());
    const task = (day, title, list = 'My Tasks') => ({uid: title, list, listName: list, title,
        due: addDays(midnight, day), color: '#62a0ea', url: 'https://tasks.google.com/task/preview'});
    return [task(-8, 'Remind to pay the monthly pay'), task(0, 'Renew the bike insurance'),
        task(3, 'Send the invoice to Courtney', 'Freelance')].filter(t => !fakeDone.has(taskKey(t)));
}

function fakeWeather() {
    const start = new Date().setMinutes(0, 0, 0);
    const codes = [2, 3, 80, 61, 95, 3, 1, 0, 0, 0, 0, 0];
    const midnight = startOfDay(Date.now());
    const {start: from, end: to} = monthRange(new Date().getFullYear(), new Date().getMonth());
    return {
        place: 'Bengaluru',
        error: null,
        updatedAt: Date.now(),
        clock: {use24h: true, showSeconds: false, firstWeekday: 0},
        events: fakeEvents(from, to),
        tasks: fakeTasks(),
        weather: {
            current: {temp: 27.4, feels: 28.9, humidity: 62, wind: 14, code: 2, isDay: true},
            today: {max: 29.6, min: 20.1, rain: 70, sunrise: midnight + 6.15 * HOUR, sunset: midnight + 18.05 * HOUR},
            hourly: codes.map((code, i) => {
                const time = start + i * HOUR;
                const h = new Date(time).getHours();
                return {time, code, temp: 27 - i * 0.7, isDay: h >= 6 && h < 18, rain: [10, 20, 60, 80, 70, 30][i] ?? 0};
            }),
        },
    };
}

connect({event: 'weather', request: 'getWeather', render, fake: fakeWeather, fakeIntervalMs: 15 * 60 * 1000});
