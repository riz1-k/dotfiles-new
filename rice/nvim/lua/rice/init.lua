-- rice for Neovim: the colorscheme follows `rice theme set`.
--
-- The current theme's neovim.lua (a LazyVim-style spec, staged by rice in
-- ~/.local/state/rice/current/theme) names the colorscheme plugin, its opts and
-- the colorscheme. Every theme's plugin is handed to lazy.nvim as a lazy spec, so
-- they're installed once and loaded only when their theme is picked. Running
-- instances watch theme.generation and switch live.
--
-- A neovim.lua is loaded with no globals: theme files are plain tables, and one
-- that tries to run code just fails to load. Themes installed with git are
-- skipped altogether (rice never stages their .lua files either).
local M = {}

local uv = vim.uv or vim.loop
local home = vim.env.HOME
local state = (vim.env.XDG_STATE_HOME or (home .. "/.local/state")) .. "/rice/current"
local config = (vim.env.XDG_CONFIG_HOME or (home .. "/.config")) .. "/rice/themes"
local data = (vim.env.XDG_DATA_HOME or (home .. "/.local/share")) .. "/rice/themes"
local stock = vim.fn.fnamemodify(debug.getinfo(1, "S").source:sub(2), ":p:h:h:h:h") .. "/themes"

-- The fallback when a theme's colorscheme isn't available: aether built from the palette.
local AETHER = { "omacom/aether.nvim", branch = "v3", name = "aether" }
local AETHER_KEYS = {
  bg = "background", dark_bg = "dark_background", darker_bg = "darker_background",
  lighter_bg = "lighter_background", fg = "foreground", dark_fg = "dark_foreground",
  light_fg = "light_foreground", bright_fg = "bright_foreground", muted = "muted",
  red = "red", yellow = "yellow", orange = "orange", green = "green", cyan = "cyan",
  blue = "blue", magenta = "magenta", brown = "brown", bright_red = "bright_red",
  bright_yellow = "bright_yellow", bright_green = "bright_green", bright_cyan = "bright_cyan",
  bright_blue = "bright_blue", bright_magenta = "bright_magenta", accent = "accent",
  cursor = "cursor", foreground = "foreground", background = "background",
  selection = "selection", selection_foreground = "selection_foreground",
  selection_background = "selection_background",
}

-- Only these keys of a theme's plugin spec reach lazy.nvim; opts are applied by
-- rice when the theme is picked, so two themes sharing a plugin don't merge theirs.
local SPEC_KEYS = { "name", "branch", "tag", "version", "commit", "main", "submodules", "build" }

local function read(path)
  local f = io.open(path, "r")
  if not f then
    return nil
  end
  local text = f:read("*a")
  f:close()
  return text
end

local function exists(path)
  return uv.fs_stat(path) ~= nil
end

local function load_spec(path)
  local chunk = loadfile(path)
  if not chunk then
    return nil
  end
  setfenv(chunk, {})
  local ok, spec = pcall(chunk)
  if not ok or type(spec) ~= "table" then
    return nil
  end
  if type(spec[1]) == "string" then
    spec = { spec } -- a single spec rather than a list
  end
  return spec
end

local function plugin_name(spec)
  return spec.name or spec[1]:match("[^/]+$"):gsub("%.git$", "")
end

-- {plugins = {spec...}, colorscheme = "x", highlights = {...}}
local function split(spec)
  local out = { plugins = {} }
  for _, s in ipairs(spec or {}) do
    if type(s) == "table" and type(s[1]) == "string" then
      if s[1] == "LazyVim/LazyVim" then
        local opts = type(s.opts) == "table" and s.opts or {}
        out.colorscheme = type(opts.colorscheme) == "string" and opts.colorscheme or nil
        out.highlights = type(opts.highlights) == "table" and opts.highlights or nil
      elseif s[1]:match("^[%w._-]+/[%w._-]+$") then
        table.insert(out.plugins, s)
      end
    end
  end
  return out
end

local function theme_files()
  local files = {}
  for _, root in ipairs({ stock, data, config }) do
    local handle = uv.fs_scandir(root)
    while handle do
      local name, kind = uv.fs_scandir_next(handle)
      if not name then
        break
      end
      local dir = root .. "/" .. name
      if (kind == "directory" or kind == "link") and not exists(dir .. "/.git") and exists(dir .. "/neovim.lua") then
        table.insert(files, dir .. "/neovim.lua")
      end
    end
  end
  table.insert(files, state .. "/theme/neovim.lua")
  return files
end

-- Lazy specs for every theme's colorscheme plugin (and aether), for lazy.setup.
function M.plugins()
  local seen, specs = {}, {}
  local function add(s)
    if seen[s[1]] then
      return
    end
    seen[s[1]] = true
    local spec = { s[1], lazy = true }
    for _, key in ipairs(SPEC_KEYS) do
      if type(s[key]) == "string" or type(s[key]) == "boolean" then
        spec[key] = s[key]
      end
    end
    table.insert(specs, spec)
  end
  add(AETHER)
  for _, path in ipairs(theme_files()) do
    for _, s in ipairs(split(load_spec(path)).plugins) do
      add(s)
    end
  end
  return specs
end

-- ---- the palette -----------------------------------------------------------------

local colors_cache
-- The current theme's resolved palette (colors.json): background, accent, ui_* ...
function M.colors()
  if not colors_cache then
    local ok, decoded = pcall(vim.json.decode, read(state .. "/theme/colors.json") or "")
    colors_cache = ok and type(decoded) == "table" and decoded or {}
  end
  return colors_cache
end

-- ---- applying ----------------------------------------------------------------------

local function lazy_plugin(spec)
  local ok, cfg = pcall(require, "lazy.core.config")
  if not ok then
    return nil
  end
  local plugin = cfg.plugins[plugin_name(spec)]
  if plugin then
    return plugin
  end
  for _, p in pairs(cfg.plugins) do
    if p[1] == spec[1] then
      return p
    end
  end
end

local function load_plugin(spec, opts)
  local plugin = lazy_plugin(spec)
  if not plugin then
    return false
  end
  if not plugin._.installed then
    return false
  end
  local loader = require("lazy.core.loader")
  loader.load(plugin, { cmd = "rice" })
  if type(opts) == "table" and next(opts) then
    local main = loader.get_main(plugin)
    local ok, mod = pcall(require, main)
    if ok and type(mod) == "table" and type(mod.setup) == "function" then
      pcall(mod.setup, opts)
    end
  end
  return true
end

local function aether(colors)
  local palette = {}
  for key, name in pairs(AETHER_KEYS) do
    palette[key] = colors[name]
  end
  return load_plugin(AETHER, { colors = palette }) and pcall(vim.cmd.colorscheme, "aether")
end

local warned = {}
local applied

function M.apply()
  local generation = vim.trim(read(state .. "/theme.generation") or "")
  applied = generation
  colors_cache = nil
  local colors = M.colors()
  local theme = split(load_spec(state .. "/theme/neovim.lua"))

  if colors.mode == "light" or colors.mode == "dark" then
    vim.o.background = colors.mode
  end
  local missing = {}
  for _, s in ipairs(theme.plugins) do
    if not load_plugin(s, s.opts) then
      table.insert(missing, s[1])
    end
  end
  local ok = theme.colorscheme and pcall(vim.cmd.colorscheme, theme.colorscheme)
  if not ok then
    if #missing > 0 and not warned[missing[1]] then
      warned[missing[1]] = true
      vim.notify(("rice: %s isn't installed yet; restart Neovim to install it (using the palette meanwhile)")
        :format(table.concat(missing, ", ")), vim.log.levels.WARN)
    end
    if not (next(colors) and aether(colors)) then
      pcall(vim.cmd.colorscheme, "default")
    end
  end
  for group, hl in pairs(theme.highlights or {}) do
    pcall(vim.api.nvim_set_hl, 0, group, hl)
  end
  vim.api.nvim_exec_autocmds("User", { pattern = "RiceTheme", modeline = false })
end

local function check()
  local generation = vim.trim(read(state .. "/theme.generation") or "")
  if generation ~= applied then
    M.apply()
  end
end

local timer
local function watch()
  vim.fn.mkdir(state, "p")
  local watcher = uv.new_fs_event()
  if not watcher then
    return
  end
  -- The directory, not the file: rice replaces theme.generation atomically.
  watcher:start(state, {}, function(_, fname)
    if fname and not fname:find("^theme%.generation") then
      return
    end
    if timer then
      timer:stop()
    else
      timer = uv.new_timer()
    end
    timer:start(120, 0, vim.schedule_wrap(check))
  end)
end

function M.setup()
  M.apply()
  watch()
  vim.api.nvim_create_autocmd("FocusGained", {
    group = vim.api.nvim_create_augroup("rice-theme", { clear = true }),
    callback = check,
  })
  vim.api.nvim_create_user_command("RiceApply", M.apply, { desc = "Re-apply the rice theme" })
end

return M
