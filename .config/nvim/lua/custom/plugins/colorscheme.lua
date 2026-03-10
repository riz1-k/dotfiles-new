return {
  "Shatur/neovim-ayu",
  name = "ayu",
  priority = 1000,
  opts = {
    mirage = false,
    terminal = true,
    spell = false,
    overrides = {
      Normal = { bg = "None" },
      NormalFloat = { bg = "None" },
      ColorColumn = { bg = "None" },
      SignColumn = { bg = "None" },
      Folded = { bg = "None" },
      FoldColumn = { bg = "None" },
      CursorLine = { bg = "None" },
      CursorColumn = { bg = "None" },
      VertSplit = { bg = "None" },
      WinBar = { bg = "None" },
      WinBarNC = { bg = "None" },
    },
  },
  config = function(_, opts)
    require("ayu").setup(opts)
    vim.cmd.colorscheme "ayu-dark"
  end,
}
