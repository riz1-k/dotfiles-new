return {
  {
    "kepano/flexoki-neovim",
    name = "flexoki",
    priority = 1000,
  },
  {
    "LazyVim/LazyVim",
    opts = {
      colorscheme = "flexoki-light",
      -- rice: tweaks on top of the scheme, re-applied after it loads.
      -- Flexoki's tx-3 comments (#b7b5ac) are too faint on paper.
      highlights = {
        Comment = { fg = "#878580", italic = true },
        ["@comment"] = { link = "Comment" },
        LineNr = { fg = "#b7b5ac" },
        CursorLineNr = { fg = "#bc5215", bold = true },
        WinSeparator = { fg = "#dad8ce" },
      },
    },
  },
}
