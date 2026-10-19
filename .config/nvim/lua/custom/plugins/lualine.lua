return {
  "nvim-lualine/lualine.nvim",
  dependencies = { "nvim-tree/nvim-web-devicons" },
  config = function()
    local lualine = require "lualine"
    local lazy_status = require "lazy.status" -- to configure lazy pending updates count
    -- Vesper in dark mode, Flexoki Light in light mode (see colorscheme.lua)
    local palettes = {
      dark = {
        bg = "#101010",
        fg = "#a0a0a0",
        on_accent = "#101010",
        orange = "#ffc799",
        blue = "#aca1cf",
        green = "#99ffe4",
        red = "#ff8080",
      },
      light = {
        bg = "#fffcf0",
        fg = "#6f6e69",
        on_accent = "#fffcf0",
        orange = "#bc5215",
        blue = "#5e409d",
        green = "#24837b",
        red = "#af3029",
      },
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
      return palettes[vim.o.background] or palettes.dark
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

    -- rebuild the theme when the colorscheme flips with GNOME's light/dark
    vim.api.nvim_create_autocmd("ColorScheme", {
      group = vim.api.nvim_create_augroup("custom-lualine-theme", { clear = true }),
      callback = function()
        opts.options.theme = make_theme(colors())
        lualine.setup(opts)
      end,
    })
  end,
}
