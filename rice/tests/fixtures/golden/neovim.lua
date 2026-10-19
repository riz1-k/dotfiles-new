return {
  {
    "omacom/aether.nvim",
    branch = "v3",
    name = "aether",
    priority = 1000,
    opts = {
      colors = {
        bg = "#1b1d22",
        dark_bg = "#14161a",
        darker_bg = "#0e0f11",
        lighter_bg = "#1b1d22",

        fg = "#d8d4c6",
        dark_fg = "#5c6370",
        light_fg = "#d8d4c6",
        bright_fg = "#f2efe4",
        muted = "#5c6370",

        red = "#e06c6c",
        yellow = "#e5c07b",
        orange = "#e5c07b",
        green = "#8cc085",
        cyan = "#5fc4b8",
        blue = "#5fa8d3",
        magenta = "#c48fd6",
        brown = "#73603e",

        bright_red = "#f07f7f",
        bright_yellow = "#f0cf8a",
        bright_green = "#9fd497",
        bright_cyan = "#72d4c8",
        bright_blue = "#72b8e0",
        bright_magenta = "#d3a2e3",

        accent = "#5fa8d3",
        cursor = "#f2efe4",
        foreground = "#d8d4c6",
        background = "#1b1d22",
        selection = "#5fa8d3",
        selection_foreground = "#1b1d22",
        selection_background = "#5fa8d3",
      },
    },
  },
  {
    "LazyVim/LazyVim",
    opts = {
      colorscheme = "aether",
    },
  },
}
