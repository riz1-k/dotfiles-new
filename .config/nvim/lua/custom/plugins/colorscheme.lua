local function apply_colorscheme()
  local colorscheme = vim.o.background == "light" and "catppuccin-latte" or "dracula"

  if vim.g.colors_name ~= colorscheme then
    vim.cmd.colorscheme(colorscheme)
  end
end

return {
  {
    "catppuccin/nvim",
    name = "catppuccin",
    priority = 1000,
    lazy = false,
    opts = {
      flavour = "auto",
      background = {
        light = "latte",
      },
    },
    config = function(_, opts)
      require("catppuccin").setup(opts)
    end,
  },
  {
    "Mofiqul/dracula.nvim",
    priority = 1001,
    lazy = false,
    config = function()
      require("dracula").setup()
      apply_colorscheme()
    end,
  },
}
