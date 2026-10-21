-- Upstream's aether v3 colours (its own Neovim choices: gold strings, mauve keywords,
-- rose functions, a softer comment taupe, a pale rose visual selection). rice: the repo
-- is omacom/aether.nvim now (the URL rice already loads), magenta for upstream's
-- purple keys, and no config or on_highlights functions: rice applies opts itself and
-- loads this file with no globals. Upstream's on_highlights overrides are the plain
-- highlights table below, which rice re-applies after the colorscheme.
return {
  {
    "omacom/aether.nvim",
    branch = "v3",
    name = "aether",
    priority = 1000,
    opts = {
      transparent = false,
      colors = {
        bg = "#F5E6D3",
        dark_bg = "#ecdcc6",
        darker_bg = "#e3d2bb",
        lighter_bg = "#fdf7ee",

        fg = "#35302a",
        dark_fg = "#6b5e52",
        light_fg = "#2a2620",
        bright_fg = "#2a2620",
        muted = "#8c7458", -- comments (muted taupe)

        red = "#a02b16", -- errors (terracotta red)
        orange = "#9b5625", -- numbers, constants (terracotta orange)
        yellow = "#713a56", -- keywords, types (mauve)
        green = "#76661d", -- strings (gold)
        cyan = "#76634c", -- members, fields (taupe)
        blue = "#9e4f5b", -- functions, methods (rose)
        magenta = "#78292e", -- control keywords (wine)
        brown = "#6e4a3a", -- deprecated, special (brown)

        bright_red = "#a02b16",
        bright_yellow = "#713a56",
        bright_green = "#76661d",
        bright_cyan = "#76634c",
        bright_blue = "#9e4f5b",
        bright_magenta = "#78292e",

        accent = "#9e4f5b",
        cursor = "#9e4f5b",
        foreground = "#35302a",
        background = "#F5E6D3",
        selection = "#ddc3c9",
        selection_foreground = "#35302a",
        selection_background = "#ddc3c9",
      },
    },
  },
  {
    "LazyVim/LazyVim",
    opts = {
      colorscheme = "aether",
      -- rice: upstream's on_highlights, as plain tables.
      highlights = {
        CursorLine = { bg = "#ecdcc6" },
        CursorLineNr = { fg = "#713a56", bold = true },
        LspReferenceText = { bg = "#ddc3c9", fg = "#2a2620" },
        LspReferenceRead = { bg = "#ddc3c9", fg = "#2a2620" },
        LspReferenceWrite = { bg = "#ddc3c9", fg = "#2a2620" },
        -- brackets: rose-black, distinct from the gold strings
        ["@punctuation.bracket"] = { fg = "#33252b" },
        ["@punctuation.special"] = { fg = "#33252b" },
        -- keywords mauve rather than aether's bright_purple; exceptions wine
        Keyword = { fg = "#713a56" },
        Conditional = { fg = "#713a56" },
        Repeat = { fg = "#713a56" },
        Statement = { fg = "#713a56" },
        Include = { fg = "#713a56" },
        StorageClass = { fg = "#713a56" },
        ["@keyword"] = { fg = "#713a56" },
        ["@keyword.function"] = { fg = "#713a56" },
        ["@keyword.operator"] = { fg = "#713a56" },
        ["@keyword.return"] = { fg = "#713a56" },
        ["@keyword.conditional"] = { fg = "#713a56" },
        ["@keyword.repeat"] = { fg = "#713a56" },
        ["@keyword.import"] = { fg = "#713a56" },
        ["@keyword.coroutine"] = { fg = "#713a56" },
        ["@conditional"] = { fg = "#713a56" },
        ["@repeat"] = { fg = "#713a56" },
        ["@include"] = { fg = "#713a56" },
        Exception = { fg = "#78292e" },
        ["@keyword.exception"] = { fg = "#78292e" },
        ["@exception"] = { fg = "#78292e" },
      },
    },
  },
}
