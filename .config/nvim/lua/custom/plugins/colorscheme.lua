local function apply_colorscheme()
  vim.o.background = "dark"
  local colorscheme = "vesper"

  if vim.g.colors_name ~= colorscheme then
    vim.cmd.colorscheme(colorscheme)
  end
end

return {
  {
    "datsfilipe/vesper.nvim",
    priority = 1000,
    lazy = false,
  },
  {
    "sonph/onehalf",
    priority = 1001,
    lazy = false,
    config = function(plugin)
      vim.opt.rtp:append(plugin.dir .. "/vim")
    end,
  },
  {
    "sainnhe/everforest",
    priority = 1000,
    lazy = false,
    config = function()
      vim.g.everforest_background = "medium"
    end,
  },
  {
    "folke/tokyonight.nvim",
    priority = 1000,
    lazy = false,
    opts = {
      style = "storm",
      styles = {
        comments = { italic = false },
        keywords = { italic = false },
        functions = {},
        variables = {},
      },
    },
  },
  {
    "loctvl842/monokai-pro.nvim",
    priority = 1000,
    lazy = false,
    opts = {
      filter = "pro",
      styles = {
        comment = { italic = false },
        keyword = { italic = false },
        type = { italic = false },
        storageclass = { italic = false },
        structure = { italic = false },
        parameter = { italic = false },
        annotation = { italic = false },
        tag_attribute = { italic = false },
      },
      override = function()
        return {
          ["@keyword.function"] = { italic = false },
          ["@keyword.type"] = { italic = false },
          ["@type.builtin"] = { italic = false },
          ["@variable.builtin"] = { italic = false },
        }
      end,
    },
    config = function(_, opts)
      require("monokai-pro").setup(opts)
      apply_colorscheme()
    end,
  },
}
