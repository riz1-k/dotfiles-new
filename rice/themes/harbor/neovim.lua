-- Upstream's aether v3 colours. rice: the repo is omacom/aether.nvim (the URL rice
-- already loads), without the config function (rice applies opts and the colorscheme
-- itself) and with selection_foreground from colors.toml. Upstream's on_highlights
-- function becomes plain highlights below, which rice re-applies after the scheme.
return {
  {
    "omacom/aether.nvim",
    branch = "v3",
    name = "aether",
    priority = 1000,
    opts = {
      colors = {
        bg = "#dfe4c4",
        dark_bg = "#dfe4c4",
        darker_bg = "#d8d9b8",
        lighter_bg = "#ecebbd",

        fg = "#1c2d28",
        dark_fg = "#253631",
        light_fg = "#858f8b",
        bright_fg = "#acb3b1",
        muted = "#606c68",

        -- upstream's stronger syntax colours for the light background
        red = "#9d2e3a",
        orange = "#9d4b25",
        yellow = "#8f5424",
        green = "#4a6a4a",
        cyan = "#256b7a",
        blue = "#386593",
        magenta = "#5a4a7a",
        brown = "#835665",

        bright_red = "#b03743",
        bright_yellow = "#955121",
        bright_green = "#466b46",
        bright_cyan = "#286b75",
        bright_blue = "#3c6499",
        bright_magenta = "#695998",

        accent = "#3a6a9a",
        cursor = "#1c2d28",
        foreground = "#1c2d28",
        background = "#dfe4c4",
        selection = "#c8d4a8",
        selection_foreground = "#0b1210",
        selection_background = "#5e81ac",
      },
    },
  },
  {
    "LazyVim/LazyVim",
    opts = {
      colorscheme = "aether",
      highlights = {
        -- a soft cursor line and visual selection, word occurrences and matching
        -- brackets on solid tones rather than aether's computed blends
        CursorLine = { bg = "#ecebbd" },
        Visual = { bg = "#c8d4a8" },
        MatchParen = { bg = "#c8d4a8", bold = true },
        LspReferenceText = { bg = "#d3d9b0" },
        LspReferenceRead = { bg = "#d3d9b0" },
        LspReferenceWrite = { bg = "#d3d9b0" },
        IlluminatedWordText = { bg = "#d3d9b0" },
        IlluminatedWordRead = { bg = "#d3d9b0" },
        IlluminatedWordWrite = { bg = "#d3d9b0" },
        -- brackets in a warm tone instead of the muted one
        ["@punctuation.bracket"] = { fg = "#8f5424" },
        ["@punctuation.special"] = { fg = "#8f5424" },
        -- keywords in the palette's blue (aether renders them lilac), exceptions purple
        Keyword = { fg = "#386593" },
        Conditional = { fg = "#386593" },
        Repeat = { fg = "#386593" },
        Statement = { fg = "#386593" },
        Include = { fg = "#386593" },
        StorageClass = { fg = "#386593" },
        ["@keyword"] = { fg = "#386593" },
        ["@keyword.function"] = { fg = "#386593" },
        ["@keyword.operator"] = { fg = "#386593" },
        ["@keyword.return"] = { fg = "#386593" },
        ["@keyword.conditional"] = { fg = "#386593" },
        ["@keyword.repeat"] = { fg = "#386593" },
        ["@keyword.import"] = { fg = "#386593" },
        ["@keyword.coroutine"] = { fg = "#386593" },
        ["@conditional"] = { fg = "#386593" },
        ["@repeat"] = { fg = "#386593" },
        ["@include"] = { fg = "#386593" },
        Exception = { fg = "#5a4a7a" },
        ["@keyword.exception"] = { fg = "#5a4a7a" },
        ["@exception"] = { fg = "#5a4a7a" },
      },
    },
  },
}
