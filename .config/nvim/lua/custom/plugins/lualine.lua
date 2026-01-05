return {
  "nvim-lualine/lualine.nvim",
  dependencies = { "nvim-tree/nvim-web-devicons" },
  config = function()
    local lualine = require "lualine"
    local lazy_status = require "lazy.status" -- to configure lazy pending updates count
    local colors = {
      bg = "#0B0E14",
      fg = "#C5C5C5",
      orange = "#FF8F40",
      blue = "#55B4D4",
      green = "#AAD94C",
      red = "#F07178",
    }
    local my_lualine_theme = {
      replace = {
        a = { fg = colors.bg, bg = colors.orange, gui = "bold" },
        b = { fg = colors.fg, bg = colors.bg },
      },
      inactive = {
        a = { fg = colors.fg, bg = colors.bg, gui = "bold" },
        b = { fg = colors.fg, bg = colors.bg },
        c = { fg = colors.fg, bg = colors.bg },
      },
      normal = {
        a = { fg = colors.bg, bg = colors.orange, gui = "bold" },
        b = { fg = colors.fg, bg = colors.bg },
        c = { fg = colors.fg, bg = colors.bg },
      },
      visual = {
        a = { fg = colors.bg, bg = colors.blue, gui = "bold" },
        b = { fg = colors.fg, bg = colors.bg },
      },
      insert = {
        a = { fg = colors.bg, bg = colors.green, gui = "bold" },
        b = { fg = colors.fg, bg = colors.bg },
      },
    }
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
    local branch = { "branch", icon = { "", color = { fg = colors.orange } }, "" }
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

    lualine.setup {
      icons_enabled = true,
      options = {
        theme = my_lualine_theme,
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
            color = { fg = colors.orange },
          },
          -- { "encoding",},
          -- { "fileformat" },
          { "filetype" },
        },
      },
    }
  end,
}
