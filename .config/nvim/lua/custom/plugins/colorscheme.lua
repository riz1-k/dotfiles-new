return {
  "Shatur/neovim-ayu",
  name = "ayu",
  priority = 1000,
  opts = {
    mirage = false,
    terminal = true,
    spell = false,
    overrides = {},
  },
  config = function(_, opts)
    require("ayu").setup(opts)
    vim.cmd.colorscheme "ayu-dark"
  end,
}
