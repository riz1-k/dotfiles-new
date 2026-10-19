return {
  "nvim-lualine/lualine.nvim",
  dependencies = { "nvim-tree/nvim-web-devicons" },
  config = function()
    local lualine = require "lualine"
    local lazy_status = require "lazy.status" -- to configure lazy pending updates count
    -- Colours from the current rice theme (see rice.lua); Vesper's until rice has run.
    local vesper = {
      background = "#101010",
      ui_dim = "#a0a0a0",
      ui_on_accent = "#101010",
      accent = "#ffc799",
      blue = "#aca1cf",
      green = "#99ffe4",
      red = "#ff8080",
    }
    local function make_theme(colors)
      return {
        replace = {
          a = { fg = colors.on_accent, bg = colors.orange, gui = "bold" },
          b = { fg = colors.fg, bg = colors.bg },
        },
        inactive = {
          a = { fg = colors.fg, bg = colors.bg, gui = "bold" },
          b = { fg = colors.fg, bg = colors.bg },
          c = { fg = colors.fg, bg = colors.bg },
        },
        normal = {
          a = { fg = colors.on_accent, bg = colors.orange, gui = "bold" },
          b = { fg = colors.fg, bg = colors.bg },
          c = { fg = colors.fg, bg = colors.bg },
        },
        visual = {
          a = { fg = colors.on_accent, bg = colors.blue, gui = "bold" },
          b = { fg = colors.fg, bg = colors.bg },
        },
        insert = {
          a = { fg = colors.on_accent, bg = colors.green, gui = "bold" },
          b = { fg = colors.fg, bg = colors.bg },
        },
      }
    end
    local function colors()
      local ok, rice = pcall(require, "rice")
      local c = ok and rice.colors() or {}
      if not c.background then
        c = vesper
      end
      return {
        bg = c.background,
        fg = c.ui_dim or c.foreground,
        on_accent = c.ui_on_accent or c.background,
        orange = c.accent,
        blue = c.blue,
        green = c.green,
        red = c.red,
      }
    end
    local mode = {
      "mode",
      fmt = function(str)
        -- return ' '
        -- displays only the first character of the mode
        return " " .. str
      end,
    }
    local diff = {
      "diff",
      colored = true,
      symbols = { added = " ", modified = " ", removed = " " }, -- changes diff symbols
      -- cond = hide_in_width,
    }
    local filename = {
      "filename",
      file_status = true,
      path = 0,
    }
    local branch = { "branch", icon = { "", color = function() return { fg = colors().orange } end }, "" }
    -- LSP Diagnostics component
    local diagnostics = {
      "diagnostics",
      sources = { "nvim_lsp", "nvim_diagnostic" },
      sections = { "error", "warn", "info", "hint" },
      symbols = {
        error = " ",
        warn = " ",
        info = " ",
        hint = "󰌵 "
      },
      colored = true,
      update_in_insert = false,
      always_visible = false,
    }

    local opts = {
      icons_enabled = true,
      options = {
        theme = make_theme(colors()),
        component_separators = { left = "|", right = "|" },
        section_separators = { left = "|", right = "" },
      },
      sections = {
        lualine_a = { mode },
        lualine_b = { branch },
        lualine_c = { diff, filename, diagnostics }, -- Added diagnostics here
        lualine_x = {
          {
            -- require("noice").api.statusline.mode.get,
            -- cond = require("noice").api.statusline.mode.has,
            lazy_status.updates,
            cond = lazy_status.has_updates,
            color = function() return { fg = colors().orange } end,
          },
          -- { "encoding",},
          -- { "fileformat" },
          { "filetype" },
        },
      },
    }
    lualine.setup(opts)

    -- rebuild the theme when rice switches themes
    vim.api.nvim_create_autocmd("ColorScheme", {
      group = vim.api.nvim_create_augroup("custom-lualine-theme", { clear = true }),
      callback = function()
        opts.options.theme = make_theme(colors())
        lualine.setup(opts)
      end,
    })
  end,
}
