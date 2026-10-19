-- Vesper in GNOME dark mode, Flexoki Light in light mode.
-- theme-sync (~/dotfiles/theme-sync) writes the mode to this file; running
-- instances watch it and switch live.
local mode_file = vim.fn.expand("~/.local/state/theme-sync/mode")
local schemes = { dark = "vesper", light = "flexoki-light" }

local function read_mode()
  local f = io.open(mode_file, "r")
  if not f then
    return "dark"
  end
  local mode = vim.trim(f:read("*a") or "")
  f:close()
  return schemes[mode] and mode or "dark"
end

-- Tweaks on top of the stock schemes, re-applied after every :colorscheme
local overrides = {
  light = {
    -- Flexoki's tx-3 comments (#b7b5ac) are too faint on paper
    Comment = { fg = "#878580", italic = true },
    ["@comment"] = { link = "Comment" },
    LineNr = { fg = "#b7b5ac" },
    CursorLineNr = { fg = "#bc5215", bold = true },
    WinSeparator = { fg = "#dad8ce" },
  },
  dark = {},
}

local applied
local function apply_colorscheme()
  local mode = read_mode()
  if applied == mode then
    return
  end
  applied = mode
  vim.o.background = mode
  pcall(vim.cmd.colorscheme, schemes[mode])
  for group, hl in pairs(overrides[mode]) do
    vim.api.nvim_set_hl(0, group, hl)
  end
end

local function watch_mode()
  local watcher = vim.uv.new_fs_event()
  if not watcher then
    return
  end
  -- watch the directory: theme-sync replaces the file atomically
  watcher:start(vim.fn.fnamemodify(mode_file, ":h"), {}, function(_, fname)
    if fname == "mode" then
      vim.schedule(apply_colorscheme)
    end
  end)
end

return {
  {
    "datsfilipe/vesper.nvim",
    priority = 1000,
    lazy = false,
  },
  {
    "kepano/flexoki-neovim",
    name = "flexoki",
    priority = 1000,
    lazy = false,
  },
  {
    "sonph/onehalf",
    priority = 1001,
    lazy = false,
    config = function(plugin)
      vim.opt.rtp:append(plugin.dir .. "/vim")
    end,
  },
  {
    "sainnhe/everforest",
    priority = 1000,
    lazy = false,
    config = function()
      vim.g.everforest_background = "medium"
    end,
  },
  {
    "folke/tokyonight.nvim",
    priority = 1000,
    lazy = false,
    opts = {
      style = "storm",
      styles = {
        comments = { italic = false },
        keywords = { italic = false },
        functions = {},
        variables = {},
      },
    },
  },
  {
    "loctvl842/monokai-pro.nvim",
    priority = 1000,
    lazy = false,
    opts = {
      filter = "pro",
      styles = {
        comment = { italic = false },
        keyword = { italic = false },
        type = { italic = false },
        storageclass = { italic = false },
        structure = { italic = false },
        parameter = { italic = false },
        annotation = { italic = false },
        tag_attribute = { italic = false },
      },
      override = function()
        return {
          ["@keyword.function"] = { italic = false },
          ["@keyword.type"] = { italic = false },
          ["@type.builtin"] = { italic = false },
          ["@variable.builtin"] = { italic = false },
        }
      end,
    },
    config = function(_, opts)
      require("monokai-pro").setup(opts)
      apply_colorscheme()
      watch_mode()
    end,
  },
}
