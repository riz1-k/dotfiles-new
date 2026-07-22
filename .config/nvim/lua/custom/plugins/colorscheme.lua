local function apply_gruvbox_material_light_overrides()
  local bg_alt = "#f9f5d7"
  local fg = "#282828"
  local muted = "#7c6f64"
  local green = "#79740e"
  local blue = "#076678"
  local purple = "#8f3f71"
  local red = "#9d0006"
  local cyan = "#427b58"
  local orange = "#af3a03"

  local highlights = {
    Normal = { fg = fg, bg = "NONE" },
    NormalFloat = { fg = fg, bg = "NONE" },
    NormalNC = { fg = fg, bg = "NONE" },
    EndOfBuffer = { fg = "#bdae93", bg = "NONE" },
    LineNr = { fg = "#a89984", bg = "NONE" },
    CursorLineNr = { fg = orange, bg = "NONE", bold = true },
    SignColumn = { bg = "NONE" },
    FoldColumn = { bg = "NONE" },
    NonText = { fg = "#bdae93", bg = "NONE" },
    StatusLine = { fg = fg, bg = bg_alt },
    StatusLineNC = { fg = muted, bg = bg_alt },
    WinBar = { fg = fg, bg = "NONE" },
    WinBarNC = { fg = muted, bg = "NONE" },

    Comment = { fg = muted },
    Constant = { fg = orange },
    String = { fg = green },
    Character = { fg = green },
    Number = { fg = purple },
    Boolean = { fg = purple },
    Float = { fg = purple },
    Identifier = { fg = fg },
    Function = { fg = blue },
    Statement = { fg = orange, bold = true },
    Conditional = { fg = orange, bold = true },
    Repeat = { fg = orange, bold = true },
    Keyword = { fg = orange, bold = true },
    Operator = { fg = orange },
    Type = { fg = cyan },
    Special = { fg = purple },
    Error = { fg = red },

    ["@variable"] = { fg = fg },
    ["@variable.builtin"] = { fg = blue },
    ["@constant"] = { fg = purple },
    ["@constant.builtin"] = { fg = purple },
    ["@string"] = { fg = green },
    ["@string.escape"] = { fg = purple },
    ["@number"] = { fg = purple },
    ["@boolean"] = { fg = purple },
    ["@function"] = { fg = blue },
    ["@function.builtin"] = { fg = blue, bold = true },
    ["@method"] = { fg = blue },
    ["@property"] = { fg = green },
    ["@field"] = { fg = green },
    ["@parameter"] = { fg = purple },
    ["@keyword"] = { fg = orange, bold = true },
    ["@keyword.function"] = { fg = orange, bold = true },
    ["@keyword.operator"] = { fg = orange },
    ["@keyword.import"] = { fg = orange, bold = true },
    ["@keyword.return"] = { fg = orange, bold = true },
    ["@operator"] = { fg = orange },
    ["@type"] = { fg = cyan },
    ["@type.builtin"] = { fg = cyan },
    ["@punctuation.delimiter"] = { fg = muted },
    ["@punctuation.bracket"] = { fg = muted },

    ["@property.json"] = { fg = blue },
    ["@field.json"] = { fg = blue },
    ["@string.json"] = { fg = green },
    ["@string.special.json"] = { fg = purple },
    ["@number.json"] = { fg = purple },
    ["@boolean.json"] = { fg = purple },
    ["@punctuation.delimiter.json"] = { fg = muted },
    ["@punctuation.bracket.json"] = { fg = muted },

    ["@lsp.type.variable"] = { fg = fg },
    ["@lsp.type.parameter"] = { fg = purple },
    ["@lsp.type.property"] = { fg = green },
    ["@lsp.type.function"] = { fg = blue },
    ["@lsp.type.method"] = { fg = blue },
    ["@lsp.type.type"] = { fg = cyan },
    ["@lsp.type.interface"] = { fg = cyan },
    ["@lsp.type.enumMember"] = { fg = purple },
  }

  for group, opts in pairs(highlights) do
    vim.api.nvim_set_hl(0, group, opts)
  end
end

local function apply_colorscheme()
  if vim.o.background == "light" then
    if vim.g.colors_name ~= "gruvbox-material" then
      vim.cmd.colorscheme("gruvbox-material")
    end
    apply_gruvbox_material_light_overrides()
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
        Normal = { fg = "#9aa3b2", bg = "None" },
        NormalFloat = { fg = "#9aa3b2", bg = "None" },
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
    "sainnhe/gruvbox-material",
    name = "gruvbox-material",
    priority = 999,
    config = function()
      vim.g.gruvbox_material_background = "hard"
      vim.g.gruvbox_material_foreground = "material"
      vim.g.gruvbox_material_transparent_background = true
      vim.g.gruvbox_material_better_performance = true

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
