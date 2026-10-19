// Todos and notes in a Markdown file (notesfile.py).
import {ding, el, log, onEvent, registerFake, request as send} from './api.js';

const UNDO_MS = 6000;
const URL_PATTERN = /(https?:\/\/[^\s<>()]+[^\s<>().,;:!?'"])|(`[^`]+`)/g;

const $ = id => document.getElementById(id);

let notes = null;         // the backend's last snapshot
let kind = 'task';        // what the add field adds
let inlineEdit = null;    // {item, input} while an item is being edited
let deferred = null;      // a snapshot that arrived during an inline edit
let toastTimer = 0;

// ---- keyboard ---------------------------------------------------------------
//
// A pinned widget sits in a dock-type window that never gets keyboard focus.
// While you type, Gtk4-DING's pinned edit mode turns it into a normal window
// on top that does, and desktop shortcuts stand down; we hand it back as soon
// as you leave the field, press Escape or click elsewhere.

let hostEditing = false;
let wantFocus = null;

function claimKeyboard(target) {
    wantFocus = target;
    if (!ding || hostEditing)
        return;
    ding.beginPinnedEdit(true);
    setTimeout(() => {
        if (hostEditing && !document.hasFocus())
            log('notes: pinned edit mode is on but the window has no keyboard focus');
    }, 1500);
}

function releaseKeyboard() {
    wantFocus = null;
    if (ding && hostEditing)
        ding.beginPinnedEdit(false);
}

function onHostState(state) {
    const was = hostEditing;
    hostEditing = !!state.widgetEditMode;
    if (hostEditing && !was && wantFocus?.isConnected) {
        // The window only now takes keyboard focus; put the caret back.
        wantFocus.focus();
        const end = wantFocus.value.length;
        wantFocus.setSelectionRange(end, end);
    } else if (!hostEditing && was) {
        wantFocus = null;
        if (inlineEdit)
            finishInlineEdit(true);
        if (document.activeElement === $('add-input'))
            $('add-input').blur();
    }
}

// Asked for on the click itself: until the window has keyboard focus, the
// page gets no focus events, so waiting for one would wait forever.
document.addEventListener('pointerdown', e => {
    if (e.target.matches('input'))
        claimKeyboard(e.target);
});

document.addEventListener('focusin', e => {
    if (e.target.matches('input'))
        claimKeyboard(e.target);
});

// Clicking anywhere outside the widget ends typing.
window.addEventListener('blur', () => {
    if (!hostEditing)
        return;
    if (inlineEdit)
        finishInlineEdit(true);
    releaseKeyboard();
});

// ---- backend ----------------------------------------------------------------

async function call(method, params) {
    try {
        const result = await request(method, params);
        if (result && result.items)
            render(result);
        return result;
    } catch (e) {
        showToast(e?.message ?? String(e), {error: true});
        return null;
    }
}

function request(method, params) {
    return send(method, params);
}

// ---- rendering --------------------------------------------------------------

// Links open in the browser and `code` gets a chip; everything else is plain text.
function richText(text) {
    const parts = [];
    let last = 0;
    for (const match of text.matchAll(URL_PATTERN)) {
        parts.push(text.slice(last, match.index));
        if (match[1]) {
            const link = el('a', '', shortUrl(match[1]));
            link.dataset.url = match[1];
            link.title = match[1];
            parts.push(link);
        } else {
            parts.push(el('code', '', match[2].slice(1, -1)));
        }
        last = match.index + match[0].length;
    }
    parts.push(text.slice(last));
    return parts;
}

function shortUrl(url) {
    const bare = url.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '');
    return bare.length > 36 ? `${bare.slice(0, 35)}…` : bare;
}

function itemRow(item) {
    const row = el('div', `item ${item.kind}${item.done ? ' done' : ''}`);
    row.dataset.line = item.line;

    const mark = el('button', 'mark');
    mark.type = 'button';
    if (item.kind === 'task') {
        mark.append(el('i', 'box'));
        mark.title = item.done ? 'Mark as not done' : 'Mark as done';
        mark.addEventListener('click', () => {
            row.classList.toggle('done');  // answer the click now; the backend confirms
            call('toggle', {line: item.line, raw: item.raw});
        });
    } else {
        mark.append(el('i', 'bullet'));
        mark.tabIndex = -1;
        mark.style.cursor = 'default';
    }

    const text = el('span', 'text');
    text.append(...richText(item.text));
    text.title = item.text;
    text.addEventListener('click', e => {
        const link = e.target.closest('a');
        if (link) {
            call('openUrl', {url: link.dataset.url});
            return;
        }
        startInlineEdit(row, item);
    });

    const remove = el('button', 'delete');
    remove.type = 'button';
    remove.title = 'Delete';
    remove.innerHTML = '<svg viewBox="0 0 10 10"><path d="M2 2l6 6M8 2 2 8"/></svg>';
    remove.addEventListener('click', () => call('delete', {line: item.line, raw: item.raw}));

    row.append(mark, text, remove);
    return row;
}

function render(snapshot) {
    if (inlineEdit) {
        deferred = snapshot;
        return;
    }
    notes = snapshot;
    const list = $('notes-list');
    const scroll = list.scrollTop;

    const open = [];
    const done = [];
    let heading = null;
    for (const item of snapshot.items) {
        if (item.kind === 'heading') {
            heading = item;
            continue;
        }
        if (item.done) {
            done.push(item);
            continue;
        }
        // A heading shows only above open items, and a title heading on line one not at all.
        if (heading && heading.line > 0) {
            open.push(heading);
        }
        heading = null;
        open.push(item);
    }

    const rows = open.map(item => item.kind === 'heading'
        ? el('div', 'label', item.text)
        : itemRow(item));

    if (done.length) {
        const label = el('div', 'label', `Done · ${done.length}`);
        const clear = el('button', '', 'Clear');
        clear.type = 'button';
        clear.title = 'Remove done todos from the file';
        clear.addEventListener('click', () => call('clearDone'));
        label.append(clear);
        rows.push(label, ...done.map(itemRow));
    }


    list.replaceChildren(...rows);
    list.scrollTop = scroll;
    updateFade();

    const todos = snapshot.items.filter(i => i.kind === 'task' && !i.done).length;
    $('notes-count').textContent = todos ? `${todos} to do` : '';
    $('notes-empty').hidden = snapshot.items.length > 0;
    $('open-file').title = `Open ${snapshot.file.replace(/^\/home\/[^/]+/, '~')}`;

    if (snapshot.undo)
        showToast(snapshot.undo, {undo: true});
}

function updateFade() {
    const list = $('notes-list');
    list.classList.toggle('more', list.scrollTop + list.clientHeight < list.scrollHeight - 2);
}

$('notes-list').addEventListener('scroll', updateFade, {passive: true});

// ---- inline editing ---------------------------------------------------------

function startInlineEdit(row, item) {
    if (inlineEdit)
        finishInlineEdit(true);
    const input = el('input', 'editor');
    input.value = item.text;
    input.maxLength = 500;
    row.classList.add('editing');
    row.querySelector('.text').replaceWith(input);
    inlineEdit = {item, input};

    input.addEventListener('keydown', e => {
        if (e.key === 'Enter') {
            e.preventDefault();
            finishInlineEdit(true);
            releaseKeyboard();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            finishInlineEdit(false);
            releaseKeyboard();
        }
    });
    input.addEventListener('blur', () => {
        // Moving to the add field or another item is a save, not a cancel.
        if (inlineEdit?.input === input && document.hasFocus())
            finishInlineEdit(true);
    });
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
    claimKeyboard(input);
}

function finishInlineEdit(save) {
    const {item, input} = inlineEdit;
    inlineEdit = null;
    const text = input.value.trim();
    const pending = deferred ?? notes;
    deferred = null;
    if (save && text !== item.text) {
        // Show the new text straight away; the backend's answer replaces it.
        render({...pending, items: pending.items.map(i => i === item ? {...i, text} : i), undo: null});
        call('edit', {line: item.line, raw: item.raw, text});
    } else {
        render({...pending, undo: null});
    }
}

// ---- adding -----------------------------------------------------------------

function setKind(next) {
    kind = next;
    const mark = $('kind').firstElementChild;
    mark.className = kind === 'task' ? 'box' : 'bullet';
    $('kind').title = kind === 'task' ? 'Todo · click for a note' : 'Note · click for a todo';
    $('add-input').placeholder = kind === 'task' ? 'Add a todo' : 'Add a note';
}

let draftTimer = 0;
function saveDraft() {
    clearTimeout(draftTimer);
    draftTimer = setTimeout(() => request('setDraft', {text: $('add-input').value, kind}).catch(() => {}), 300);
}

$('kind').addEventListener('mousedown', e => e.preventDefault());  // keep the caret in the field
$('kind').addEventListener('click', () => {
    setKind(kind === 'task' ? 'note' : 'task');
    saveDraft();
});

$('add-input').addEventListener('input', e => {
    const input = e.target;
    // Markdown habits: "- " starts a note, "[] " or "[ ] " a todo.
    const prefix = input.value.match(/^(?:[-*] (?!\[)|\[ ?\] )/);
    if (prefix) {
        setKind(prefix[0].startsWith('[') ? 'task' : 'note');
        input.value = input.value.slice(prefix[0].length);
    }
    saveDraft();
});

$('add-input').addEventListener('keydown', e => {
    if (e.key === 'Escape') {
        e.preventDefault();
        $('add-input').blur();
        releaseKeyboard();
    } else if (e.key === 'Backspace' && !e.target.value && kind === 'note') {
        setKind('task');
    }
});

$('add').addEventListener('submit', async e => {
    e.preventDefault();
    const input = $('add-input');
    const text = input.value.trim();
    if (!text)
        return;
    input.value = '';
    const added = kind;
    setKind('task');
    saveDraft();
    // Stay in the field, so a few todos go in one after another.
    if (await call('add', {text, kind: added}))
        $('notes-list').scrollTop = 0;
});

$('open-file').addEventListener('click', () => call('openFile'));

// ---- toast ------------------------------------------------------------------

function showToast(text, {undo = false, error = false} = {}) {
    clearTimeout(toastTimer);
    $('toast-text').textContent = text;
    $('toast').classList.toggle('error', error);
    $('toast-action').hidden = !undo;
    $('toast').hidden = false;
    toastTimer = setTimeout(hideToast, undo ? UNDO_MS : 4000);
}

function hideToast() {
    $('toast').hidden = true;
}

$('toast-action').addEventListener('click', () => {
    hideToast();
    call('undo');
});

// ---- start ------------------------------------------------------------------

function restore(snapshot) {
    const draft = snapshot.draft;
    if (draft?.text) {
        $('add-input').value = draft.text;
        setKind(draft.kind === 'note' ? 'note' : 'task');
    }
    render({...snapshot, undo: null});
    // Gtk4-DING can reload the page while it switches layers for typing; pick up where we were.
    if (hostEditing) {
        claimKeyboard($('add-input'));
        $('add-input').focus();
    }
}

registerFake((method, params) => fakeBackend(method, params));

export function start() {
    if (ding) {
        hostEditing = !!ding.getHostState?.()?.widgetEditMode;
        ding.onHostStateChanged(onHostState);
    }
    onEvent('notes', payload => render({...payload, undo: null}));
    request('getNotes')
        .then(restore)
        .catch(e => log(`getNotes failed: ${e?.message ?? e}`));
}

// ---- preview data (opened outside Gtk4-DING) ----------------------------------

function fakeBackend(method, params = {}) {
    const state = fakeBackend.state ??= {
        lines: [
            '- [ ] Renew passport photos',
            '- [ ] Email Priya about the invoice',
            '- Wi-Fi at the office: `articys-5g`',
            '- [ ] Read https://github.com/smedius/gtk4-ding/issues/42',
            '- [x] Order coffee filters',
        ],
        undo: null,
    };
    const parse = (line, i) => {
        const task = line.match(/^- \[([ x])\] (.*)$/);
        return task ? {kind: 'task', done: task[1] === 'x', text: task[2], line: i, raw: line}
            : {kind: 'note', text: line.replace(/^- /, ''), line: i, raw: line};
    };
    const before = [...state.lines];
    let label = null;
    if (method === 'add')
        state.lines.unshift(params.kind === 'task' ? `- [ ] ${params.text}` : `- ${params.text}`);
    else if (method === 'toggle')
        state.lines[params.line] = params.raw.includes('[x]') ? params.raw.replace('[x]', '[ ]') : params.raw.replace('[ ]', '[x]');
    else if (method === 'edit')
        state.lines[params.line] = params.raw.replace(/(\] |- )(?!\[).*$/, `$1${params.text}`);
    else if (method === 'delete')
        state.lines.splice(params.line, 1), label = 'Deleted';
    else if (method === 'clearDone')
        state.lines = state.lines.filter(l => !l.startsWith('- [x]')), label = 'Cleared';
    else if (method === 'undo' && state.undo)
        state.lines = state.undo;
    else if (method !== 'getNotes')
        return Promise.resolve(null);
    state.undo = label ? before : null;
    return Promise.resolve({file: '/home/riz1/Notes/inbox.md', name: 'inbox.md',
        items: state.lines.map(parse), undo: label, draft: {text: '', kind: 'task'}});
}

start();
