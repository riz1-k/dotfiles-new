local function apply_orng_light_overrides()
  local bg_alt = "#f3eadf"
  local fg = "#1f2328"
  local muted = "#4b5563"
  local orange = "#c2410c"
  local orange_dark = "#9a3412"
  local green = "#116329"
  local blue = "#0550ae"
  local purple = "#6f42c1"
  local red = "#b42318"
  local cyan = "#0e7490"

  local highlights = {
    Normal = { fg = fg, bg = "NONE" },
    NormalFloat = { fg = fg, bg = "NONE" },
    NormalNC = { fg = fg, bg = "NONE" },
    EndOfBuffer = { fg = "#9ca3af", bg = "NONE" },
    LineNr = { fg = "#6b7280", bg = "NONE" },
    CursorLineNr = { fg = orange, bg = "NONE", bold = true },
    SignColumn = { bg = "NONE" },
    FoldColumn = { bg = "NONE" },
    NonText = { fg = "#9ca3af", bg = "NONE" },
    StatusLine = { fg = fg, bg = bg_alt },
    StatusLineNC = { fg = muted, bg = bg_alt },
    WinBar = { fg = fg, bg = "NONE" },
    WinBarNC = { fg = muted, bg = "NONE" },

    Comment = { fg = muted },
    Constant = { fg = orange },
    String = { fg = green },
    Character = { fg = green },
    Number = { fg = orange_dark },
    Boolean = { fg = orange_dark },
    Float = { fg = orange_dark },
    Identifier = { fg = fg },
    Function = { fg = blue },
    Statement = { fg = orange, bold = true },
    Conditional = { fg = orange, bold = true },
    Repeat = { fg = orange, bold = true },
    Keyword = { fg = orange, bold = true },
    Operator = { fg = orange_dark },
    Type = { fg = cyan },
    Special = { fg = purple },
    Error = { fg = red },

    ["@variable"] = { fg = fg },
    ["@variable.builtin"] = { fg = blue },
    ["@constant"] = { fg = orange_dark },
    ["@constant.builtin"] = { fg = orange_dark },
    ["@string"] = { fg = green },
    ["@string.escape"] = { fg = purple },
    ["@number"] = { fg = orange_dark },
    ["@boolean"] = { fg = orange_dark },
    ["@function"] = { fg = blue },
    ["@function.builtin"] = { fg = blue, bold = true },
    ["@method"] = { fg = blue },
    ["@property"] = { fg = green },
    ["@field"] = { fg = green },
    ["@parameter"] = { fg = purple },
    ["@keyword"] = { fg = orange, bold = true },
    ["@keyword.function"] = { fg = orange, bold = true },
    ["@keyword.operator"] = { fg = orange_dark },
    ["@keyword.import"] = { fg = orange, bold = true },
    ["@keyword.return"] = { fg = orange, bold = true },
    ["@operator"] = { fg = orange_dark },
    ["@type"] = { fg = cyan },
    ["@type.builtin"] = { fg = cyan },
    ["@punctuation.delimiter"] = { fg = muted },
    ["@punctuation.bracket"] = { fg = muted },

    ["@lsp.type.variable"] = { fg = fg },
    ["@lsp.type.parameter"] = { fg = purple },
    ["@lsp.type.property"] = { fg = green },
    ["@lsp.type.function"] = { fg = blue },
    ["@lsp.type.method"] = { fg = blue },
    ["@lsp.type.type"] = { fg = cyan },
    ["@lsp.type.interface"] = { fg = cyan },
    ["@lsp.type.enumMember"] = { fg = orange_dark },
  }

  for group, opts in pairs(highlights) do
    vim.api.nvim_set_hl(0, group, opts)
  end
end

local function apply_colorscheme()
  if vim.o.background == "light" then
    require("orng").setup({
      variant = "light",
      transparent = true,
      italic_comment = false,
    })
    if vim.g.colors_name ~= "orng-light" then
      vim.cmd.colorscheme("orng")
    end
    apply_orng_light_overrides()
  elseif vim.g.colors_name ~= "ayu" then
    vim.cmd.colorscheme("ayu-dark")
  end
end

return {
  {
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
    end,
  },
  {
    "roerohan/orng.nvim",
    name = "orng",
    priority = 999,
    config = function()
      apply_colorscheme()

      vim.api.nvim_create_autocmd("ColorScheme", {
        pattern = "*",
        callback = function()
          vim.schedule(apply_colorscheme)
        end,
      })
    end,
  },
}
