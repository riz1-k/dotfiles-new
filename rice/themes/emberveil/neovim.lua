-- Emberveil + Neovim.
--
-- Emberveil does not ship its own editor colorscheme. Neovim uses
-- ashen.nvim (ficcdaf/ashen.nvim), a warm, ember-toned dark theme that pairs
-- with the ember accent of this desktop theme without needing a second
-- palette to keep in sync.
--
-- The plugin and its colorscheme name ("ashen") are Ashen's, not Emberveil's.
-- If you would rather have a colorscheme generated straight from colors.toml,
-- delete this file: Omarchy then regenerates neovim.lua from the palette on
-- every `omarchy theme set`.
return {
    {
        "ficcdaf/ashen.nvim",
        lazy = false,
        priority = 1000,
    },
    {
        "LazyVim/LazyVim",
        opts = {
            colorscheme = "ashen",
        },
    },
}
