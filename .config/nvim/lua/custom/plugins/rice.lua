-- The colorscheme follows rice (~/dotfiles/rice): `rice theme set` stages the
-- theme's neovim.lua and running instances switch live (see rice/nvim/lua/rice).
-- Every theme's colorscheme plugin is a lazy spec, loaded when its theme is picked.
local dir = vim.fn.expand("~/dotfiles/rice/nvim")
if not (vim.uv or vim.loop).fs_stat(dir) then
  local exe = vim.fn.exepath("rice")
  dir = exe ~= "" and vim.fn.fnamemodify(vim.fn.resolve(exe), ":h:h") .. "/nvim" or dir
end
package.path = ("%s/lua/?.lua;%s/lua/?/init.lua;%s"):format(dir, dir, package.path)
local ok, rice = pcall(require, "rice")
if not ok then
  vim.notify("rice: " .. tostring(rice), vim.log.levels.WARN)
  return {}
end

-- Settings for schemes that some themes use (merged with the themes' specs).
local specs = {
  {
    "sonph/onehalf",
    lazy = true,
    config = function(plugin)
      vim.opt.rtp:append(plugin.dir .. "/vim")
    end,
  },
  {
    "sainnhe/everforest",
    lazy = true,
    config = function()
      vim.g.everforest_background = "medium"
    end,
  },
  {
    "folke/tokyonight.nvim",
    lazy = true,
    opts = {
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
    lazy = true,
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
  },
  {
    dir = dir,
    name = "rice",
    lazy = false,
    priority = 1000,
    config = function()
      rice.setup()
    end,
  },
}

return vim.list_extend(specs, rice.plugins())
