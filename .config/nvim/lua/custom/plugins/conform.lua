return {
  "stevearc/conform.nvim",
  lazy = false,
  config = function()
    local util = require("conform.util")

    require("conform").setup({
      formatters_by_ft = {
        javascript = { "biome" },
        javascriptreact = { "biome" },
        typescript = { "biome" },
        typescriptreact = { "biome" },
        json = { "biome" },
        jsonc = { "biome" },

        html = { "prettier" },
        css = { "prettier" },
        scss = { "prettier" },
        markdown = {},
        yaml = { "prettier" },
        vue = { "prettier" },
        svelte = { "prettier" },
        lua = { "stylua" },
      },
      formatters = {
        biome = {
          command = util.from_node_modules("biome"),
          cwd = util.root_file({ "biome.json", "biome.jsonc", "package.json" }),
          args = {
            "check",
            "--write",
            "--unsafe",
            "--stdin-file-path",
            "$FILENAME",
          },
          stdin = true,
        },
      },
    })

    -- Manual format keymap
    vim.keymap.set({ "n", "v" }, "<leader>mp", function()
      require("conform").format({
        lsp_fallback = true,
        async = false,
        timeout_ms = 1000,
      })
    end, { desc = "Format file or range (in visual mode)" })
  end,
}
