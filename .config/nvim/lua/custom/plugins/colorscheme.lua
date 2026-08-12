local function apply_colorscheme()
  local colorscheme = vim.o.background == "light" and "catppuccin-latte" or "catppuccin-macchiato"

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
        dark = "macchiato",
      },
    },
    config = function(_, opts)
      require("catppuccin").setup(opts)
      apply_colorscheme()
    end,
  },
}
