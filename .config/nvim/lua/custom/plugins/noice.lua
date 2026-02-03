return {
  "folke/noice.nvim",
  event = "VeryLazy",
  opts = {
    presets = {
      command_palette = true, 
    },
    views = {
      cmdline_popup = {
        position = {
          row = "50%", 
          col = "50%",
        },
        size = {
          width = 60,
          height = "auto",
        },
      },
      popupmenu = {
        relative = "editor",
        position = {
          row = "66%",
          col = "50%",
        },
        size = {
          width = 60,
          height = 10,
        },
        border = {
          style = "rounded",
          padding = { 0, 1 },
        },
      },
    },
  },
  dependencies = {
    "MunifTanjim/nui.nvim",
  },
}
