// The theme and background pickers: Omarchy's carousel, as a full-screen overlay.
//
// The selected item's preview is shown large in the middle, with its neighbours as
// slices either side. ←/→ (or Tab, the wheel, a click) move, typing filters by
// name, Backspace edits the filter, Enter applies, Esc clears the filter and then
// closes, and Delete removes a theme rice installed (after a confirmation).
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Shell from 'gi://Shell';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const SIDE = 3;                         // slices each side of the selection
const SLICE_WIDTH = [0.17, 0.115, 0.075];   // of the selected card's width
const SLICE_HEIGHT = [0.86, 0.75, 0.64];
const SLICE_OPACITY = [235, 165, 95];
const FADE_MS = 130;

export class Carousel {
    // opts: {kind, rows, selectedKey, key(row), label(row), detail(row), image(row),
    //        canDelete(row), onActivate(row), onDelete(row) -> Promise, onClosed(),
    //        hint, empty}
    constructor(opts) {
        this._opts = opts;
        this._rows = opts.rows ?? [];
        this._filter = '';
        this._confirm = null;
        this._sel = 0;
        this._scroll = 0;
    }

    get isOpen() {
        return Boolean(this.actor);
    }

    open() {
        const monitor = Main.layoutManager.primaryMonitor;
        this.actor = new St.Widget({
            style_class: 'rice-picker',
            reactive: true,
            can_focus: true,
            x: monitor.x, y: monitor.y, width: monitor.width, height: monitor.height,
            layout_manager: new Clutter.BinLayout(),
            opacity: 0,
        });
        Main.uiGroup.add_child(this.actor);

        const box = new St.BoxLayout({
            orientation: Clutter.Orientation.VERTICAL,
            style_class: 'rice-picker-box',
            x_align: Clutter.ActorAlign.CENTER,
            y_align: Clutter.ActorAlign.CENTER,
        });
        this.actor.add_child(box);

        const header = new St.BoxLayout({style_class: 'rice-picker-header', x_align: Clutter.ActorAlign.CENTER});
        this._heading = new St.Label({style_class: 'rice-picker-heading', text: this._opts.heading ?? '',
            y_align: Clutter.ActorAlign.CENTER});
        this._filterLabel = new St.Label({style_class: 'rice-picker-filter', visible: false,
            y_align: Clutter.ActorAlign.CENTER});
        this._count = new St.Label({style_class: 'rice-picker-subtitle', y_align: Clutter.ActorAlign.CENTER});
        header.add_child(this._heading);
        header.add_child(this._filterLabel);
        header.add_child(this._count);
        box.add_child(header);

        const width = Math.round(Math.min(monitor.width * 0.5, 1120));
        const height = Math.round(width * 9 / 16);
        this._track = new St.BoxLayout({style_class: 'rice-picker-track', x_align: Clutter.ActorAlign.CENTER,
            height});
        box.add_child(this._track);
        this._slots = [];
        for (let i = -SIDE; i <= SIDE; i++) {
            const d = Math.abs(i);
            const slot = new St.Button({
                style_class: `rice-picker-card${d === 0 ? ' rice-picker-selected' : ''}`,
                y_align: Clutter.ActorAlign.CENTER,
                width: d === 0 ? width : Math.round(width * SLICE_WIDTH[d - 1]),
                height: d === 0 ? height : Math.round(height * SLICE_HEIGHT[d - 1]),
                can_focus: false,
            });
            slot.set_pivot_point(0.5, 0.5);
            slot._offset = i;
            slot.connect('clicked', () => {
                if (!slot._row)
                    return;
                if (slot._offset === 0)
                    this._activate();
                else
                    this._move(slot._offset);
            });
            this._track.add_child(slot);
            this._slots.push(slot);
        }

        this._title = new St.Label({style_class: 'rice-picker-title', x_align: Clutter.ActorAlign.CENTER});
        this._detail = new St.Label({style_class: 'rice-picker-subtitle', x_align: Clutter.ActorAlign.CENTER});
        this._hint = new St.Label({style_class: 'rice-picker-hint', x_align: Clutter.ActorAlign.CENTER,
            text: this._opts.hint ?? ''});
        box.add_child(this._title);
        box.add_child(this._detail);
        box.add_child(this._hint);

        this.actor.connect('key-press-event', (_a, event) => this._onKey(event));
        this.actor.connect('scroll-event', (_a, event) => this._onScroll(event));
        this.actor.connect('button-release-event', (_a, event) => {
            if (global.stage.get_event_actor(event) === this.actor)
                this.close();
            return Clutter.EVENT_STOP;
        });

        this._grab = Main.pushModal(this.actor, {actionMode: Shell.ActionMode.SYSTEM_MODAL});
        this.actor.grab_key_focus();
        this._select(this._opts.selectedKey);
        this._render();
        this.actor.ease({opacity: 255, duration: FADE_MS, mode: Clutter.AnimationMode.EASE_OUT_QUAD});
        return true;
    }

    // New rows (the list refreshes in the background): keep the selection by key.
    setRows(rows) {
        const current = this._filtered()[this._sel];
        this._rows = rows;
        if (!this.actor)
            return;
        this._select(current ? this._opts.key(current) : this._opts.selectedKey);
        this._render();
    }

    close(then = null) {
        if (!this.actor)
            return;
        const actor = this.actor;
        if (this._grab) {
            Main.popModal(this._grab);
            this._grab = null;
        }
        actor.reactive = false;
        actor.ease({
            opacity: 0,
            duration: FADE_MS,
            mode: Clutter.AnimationMode.EASE_IN_QUAD,
            onStopped: () => {
                this._teardown();
                then?.();
                this._opts.onClosed?.();
            },
        });
    }

    destroy() {
        this._teardown();
    }

    _teardown() {
        if (this._grab) {
            Main.popModal(this._grab);
            this._grab = null;
        }
        this.actor?.destroy();
        this.actor = null;
        this._slots = [];
    }

    // ---- state -----------------------------------------------------------------

    _filtered() {
        const f = this._filter.toLowerCase();
        if (!f)
            return this._rows;
        return this._rows.filter(r =>
            this._opts.label(r).toLowerCase().includes(f) || this._opts.key(r).toLowerCase().includes(f));
    }

    _select(key) {
        const i = this._filtered().findIndex(r => this._opts.key(r) === key);
        this._sel = Math.max(0, i);
    }

    _move(delta) {
        const n = this._filtered().length;
        if (n === 0)
            return;
        this._confirm = null;
        // Wrap around, like flicking through a deck.
        this._sel = ((this._sel + delta) % n + n) % n;
        this._render();
        const card = this._slots[SIDE];
        card.remove_all_transitions();
        card.set_scale(0.965, 0.965);
        card.ease({scale_x: 1, scale_y: 1, duration: 140, mode: Clutter.AnimationMode.EASE_OUT_QUAD});
    }

    _setFilter(text) {
        const current = this._filtered()[this._sel];
        this._filter = text;
        this._confirm = null;
        const list = this._filtered();
        const keep = current ? list.indexOf(current) : -1;
        this._sel = keep >= 0 ? keep : 0;
        this._render();
    }

    _activate() {
        const row = this._filtered()[this._sel];
        if (!row)
            return;
        if (this._confirm) {
            const target = this._confirm;
            this._confirm = null;
            this._hint.text = 'Removing…';
            this._opts.onDelete(target).then(rows => {
                if (rows)
                    this.setRows(rows);
                this._render();
            }).catch(e => {
                this._hint.text = `Couldn't remove: ${e.message}`;
            });
            return;
        }
        // Close first, so the switch's screen snapshot doesn't catch the picker.
        this.close(() => this._opts.onActivate(row));
    }

    _askDelete() {
        const row = this._filtered()[this._sel];
        if (!row || !this._opts.canDelete?.(row))
            return;
        this._confirm = row;
        this._render();
    }

    // ---- input -------------------------------------------------------------------

    _onKey(event) {
        const sym = event.get_key_symbol();
        const state = event.get_state();
        const shift = (state & Clutter.ModifierType.SHIFT_MASK) !== 0;
        switch (sym) {
        case Clutter.KEY_Left:
        case Clutter.KEY_Up:
        case Clutter.KEY_ISO_Left_Tab:
            this._move(-1);
            return Clutter.EVENT_STOP;
        case Clutter.KEY_Tab:
            this._move(shift ? -1 : 1);
            return Clutter.EVENT_STOP;
        case Clutter.KEY_Right:
        case Clutter.KEY_Down:
            this._move(1);
            return Clutter.EVENT_STOP;
        case Clutter.KEY_Home:
            this._move(-this._sel);
            return Clutter.EVENT_STOP;
        case Clutter.KEY_End:
            this._move(this._filtered().length - 1 - this._sel);
            return Clutter.EVENT_STOP;
        case Clutter.KEY_Return:
        case Clutter.KEY_KP_Enter:
        case Clutter.KEY_ISO_Enter:
            this._activate();
            return Clutter.EVENT_STOP;
        case Clutter.KEY_Escape:
            if (this._confirm) {
                this._confirm = null;
                this._render();
            } else if (this._filter) {
                this._setFilter('');
            } else {
                this.close();
            }
            return Clutter.EVENT_STOP;
        case Clutter.KEY_BackSpace:
            if (this._filter)
                this._setFilter(this._filter.slice(0, -1));
            return Clutter.EVENT_STOP;
        case Clutter.KEY_Delete:
        case Clutter.KEY_KP_Delete:
            this._askDelete();
            return Clutter.EVENT_STOP;
        }
        if (state & (Clutter.ModifierType.CONTROL_MASK | Clutter.ModifierType.MOD1_MASK | Clutter.ModifierType.MOD4_MASK))
            return Clutter.EVENT_STOP;
        const ch = event.get_key_unicode();
        if (ch && (GLib.unichar_isgraph(ch) || ch === ' ') && this._filter.length < 40)
            this._setFilter(this._filter + ch);
        return Clutter.EVENT_STOP;
    }

    _onScroll(event) {
        switch (event.get_scroll_direction()) {
        case Clutter.ScrollDirection.UP:
        case Clutter.ScrollDirection.LEFT:
            this._move(-1);
            break;
        case Clutter.ScrollDirection.DOWN:
        case Clutter.ScrollDirection.RIGHT:
            this._move(1);
            break;
        case Clutter.ScrollDirection.SMOOTH: {
            const [dx, dy] = event.get_scroll_delta();
            this._scroll += dx + dy;
            if (Math.abs(this._scroll) >= 1) {
                this._move(this._scroll > 0 ? 1 : -1);
                this._scroll = 0;
            }
            break;
        }
        }
        return Clutter.EVENT_STOP;
    }

    // ---- drawing -------------------------------------------------------------------

    _render() {
        if (!this.actor)
            return;
        const list = this._filtered();
        const n = list.length;
        this._sel = Math.min(this._sel, Math.max(0, n - 1));

        this._filterLabel.visible = this._filter !== '';
        this._filterLabel.text = this._filter;
        this._count.text = n ? `${this._sel + 1} / ${n}` : '';

        // The list wraps; with few items, each one appears once (spares go right).
        const left = Math.min(SIDE, Math.floor((n - 1) / 2));
        const right = Math.min(SIDE, n - 1 - left);
        for (const slot of this._slots) {
            const off = slot._offset;
            const shown = n > 0 && (off === 0 || (off < 0 ? -off <= left : off <= right));
            const row = shown ? list[((this._sel + off) % n + n) % n] : null;
            slot._row = row;
            slot.reactive = Boolean(row);
            slot.opacity = row ? (off === 0 ? 255 : SLICE_OPACITY[Math.abs(off) - 1]) : 0;
            const image = row ? this._opts.image(row) : null;
            slot.style = image ? `background-image: url("${GLib.filename_to_uri(image, null)}");` : null;
        }

        const row = list[this._sel];
        if (this._confirm) {
            this._title.text = `Remove ${this._opts.label(this._confirm)}?`;
            this._detail.text = this._opts.detail?.(this._confirm) ?? '';
            this._hint.text = 'Enter to remove  ·  Esc to keep it';
            this._hint.add_style_class_name('rice-picker-confirm');
            return;
        }
        this._hint.remove_style_class_name('rice-picker-confirm');
        this._hint.text = this._opts.hint ?? '';
        this._title.text = row ? this._opts.label(row) : (this._rows.length ? 'Nothing matches' : (this._opts.empty ?? 'Loading…'));
        this._detail.text = row ? this._opts.detail?.(row) ?? '' : '';
    }
}
