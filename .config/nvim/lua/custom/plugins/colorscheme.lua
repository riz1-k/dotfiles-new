local function apply_colorscheme()
  vim.g.everforest_background = vim.o.background == "dark" and "hard" or "medium"

  if vim.g.colors_name ~= "everforest" then
    vim.cmd.colorscheme("everforest")
  end
end

return {
  {
    "sainnhe/everforest",
    name = "everforest",
    priority = 1000,
    lazy = false,
    init = function()
      vim.o.background = vim.o.background == "light" and "light" or "dark"
      vim.g.everforest_enable_italic = 1
      vim.g.everforest_better_performance = 1
      apply_colorscheme()

      vim.api.nvim_create_autocmd("OptionSet", {
        pattern = "background",
        callback = function()
          vim.schedule(apply_colorscheme)
        end,
      })
    end,
  },
}
