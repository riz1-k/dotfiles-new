-- Upstream's spec is for aether v2 (bg_dark, fg_dark, comment...), which v3 ignores
-- and then fills with its dark defaults. rice: the v3 keys from the palette, with
-- upstream's own Neovim choices carried over: sidebars on the page (bg_dark), near-black
-- secondary text (fg_dark) and its pink-red orange.
return {
  {
    "omacom/aether.nvim",
    branch = "v3",
    name = "aether",
    priority = 1000,
    opts = {
      colors = {
        bg = "#f3e4cb",
        dark_bg = "#f3e4cb",
        darker_bg = "#dac9b0",
        lighter_bg = "#f3e4cb",

        fg = "#4d2e1a",
        dark_fg = "#080503",
        light_fg = "#4d2e1a",
        bright_fg = "#4d2e1a",
        muted = "#9f8253",

        red = "#a4373c",
        yellow = "#a8611f",
        orange = "#d2656a",
        green = "#a46d2d",
        cyan = "#755833",
        blue = "#a32f1a",
        magenta = "#9c3521",
        brown = "#543110",

        bright_red = "#d2656a",
        bright_yellow = "#e48e3e",
        bright_green = "#d89b55",
        bright_cyan = "#b8884c",
        bright_blue = "#e84d31",
        bright_magenta = "#de553a",

        accent = "#a32f1a",
        cursor = "#4d2e1a",
        foreground = "#4d2e1a",
        background = "#f3e4cb",
        selection = "#dfceb6",
        selection_foreground = "#f3e4cb",
        selection_background = "#a32f1a",
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
