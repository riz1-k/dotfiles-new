local wezterm = require 'wezterm'
local act = wezterm.action

local config = {}
local mouse_bindings = {}
local launch_menu = {}

if wezterm.config_builder then
    config = wezterm.config_builder()
end

config.color_scheme = 'Pro'
config.font = wezterm.font('Maple Mono')
config.line_height = 1.4
config.font_size = 11.5
config.launch_menu = launch_menu
config.default_cursor_style = "SteadyBlock"
config.disable_default_key_bindings = true
config.keys = { { key = 'V', mods = 'CTRL', action = act.PasteFrom 'Clipboard' }, }
config.mouse_bindings = mouse_bindings

mouse_bindings = {
    {
        event = { Down = { streak = 3, button = 'Left' } },
        action = wezterm.action.SelectTextAtMouseCursor 'SemanticZone',
        mods = 'NONE',
    },
    {
        event = { Down = { streak = 1, button = "Right" } },
        mods = "NONE",
        action = wezterm.action_callback(function(window, pane)
            local has_selection = window:get_selection_text_for_pane(pane) ~= ""
            if has_selection then
                window:perform_action(act.CopyTo("ClipboardAndPrimarySelection"), pane)
                window:perform_action(act.ClearSelection, pane)
            else
                window:perform_action(act({ PasteFrom = "Clipboard" }), pane)
            end
        end),
    },
}
config.foreground_text_hsb = {
    hue = 1.0,
    saturation = 1.2,
    brightness = 1.5,
}
config.default_domain = 'WSL:Ubuntu'
config.enable_tab_bar = false
config.window_decorations = "RESIZE"
config.window_padding = {
    bottom = 0
}

return config
