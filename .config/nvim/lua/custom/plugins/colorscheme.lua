local function apply_colorscheme()
  if vim.g.colors_name ~= "catppuccin-mocha" then
    vim.cmd.colorscheme("catppuccin-mocha")
  end
end

return {
  {
    "catppuccin/nvim",
    name = "catppuccin",
    priority = 1000,
    lazy = false,
    opts = {
      flavour = "mocha",
    },
    init = function()
      vim.o.background = "dark"
      apply_colorscheme()
    end,
  },
}
