import St from 'gi://St';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

export default class AnimationSpeedExtension extends Extension {
    enable() {
        this._settings = St.Settings.get();
        this._previousFactor = this._settings.slow_down_factor;
        this._settings.slow_down_factor = 0.5;
    }

    disable() {
        if (this._settings) {
            this._settings.slow_down_factor = this._previousFactor;
            this._settings = null;
        }
    }
}
