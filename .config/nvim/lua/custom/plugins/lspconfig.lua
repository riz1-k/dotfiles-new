return {
  {
    "mason-org/mason.nvim",
    opts = function(_, opts)
      opts.ensure_installed = opts.ensure_installed or {}
      vim.list_extend(opts.ensure_installed, {
        "eslint-lsp", -- ESLint Language Server
        "eslint_d",   -- ESLint daemon for faster formatting
      })
    end,
  },
  {
    "neovim/nvim-lspconfig",
    event = { "BufReadPre", "BufNewFile" },
    config = function()
      vim.api.nvim_create_autocmd("LspAttach", {
        callback = function(event)
          local map = function(keys, func, desc, mode)
            mode = mode or "n"
            vim.keymap.set(mode, keys, func, { buffer = event.buf, desc = "LSP: " .. desc })
          end
          map("gd", require("telescope.builtin").lsp_definitions, "[G]oto [D]efinition")
          map("gr", require("telescope.builtin").lsp_references, "[G]oto [R]eferences")
          map("gI", require("telescope.builtin").lsp_implementations, "[G]oto [I]mplementation")
          map("<leader>D", require("telescope.builtin").lsp_type_definitions, "Type [D]efinition")
          map("<leader>ds", require("telescope.builtin").lsp_document_symbols, "[D]ocument [S]ymbols")
          map("<leader>ca", vim.lsp.buf.code_action, "[C]ode [A]ction", { "n", "x" })
          map("gD", vim.lsp.buf.declaration, "[G]oto [D]eclaration")
        end
      })
    end
  },
  {
    "mason-org/mason-lspconfig.nvim",
    dependencies = {
      "mason-org/mason.nvim",
      "neovim/nvim-lspconfig",
    },
    event = { "BufReadPre", "BufNewFile" },
    config = function()
      -- Setup mason-lspconfig first
      require("mason-lspconfig").setup({
        -- Automatically install these language servers if not already installed
        ensure_installed = {
          "html",        -- HTML Language Server
          "cssls",       -- CSS Language Server
          "tailwindcss", -- Tailwind CSS Language Server
          "lua_ls",      -- Lua Language Server
          "vtsls",       -- TypeScript/JavaScript Language Server
          "eslint",      -- ESLint
          "biome",       -- Biome
        },

        -- Disable automatic enabling to avoid conflicts
        automatic_enable = false,
        automatic_installation = true,
      })

      -- Async format after save (non-blocking)
      vim.api.nvim_create_autocmd("BufWritePost", {
        pattern = { "*.js", "*.jsx", "*.ts", "*.tsx", "*.json", "*.html", "*.css", "*.scss", "*.md", "*.yaml", "*.yml", "*.vue", "*.svelte", "*.go" },
        callback = function()
          require("conform").format({
            async = true,
            lsp_fallback = true,
            timeout_ms = 2000,
          })
        end,
      })

      -- Now manually setup each server
      local lspconfig = require("lspconfig")

      -- HTML Language Server
      lspconfig.html.setup({})

      -- CSS Language Server
      lspconfig.cssls.setup({})

      -- Tailwind CSS Language Server
      lspconfig.tailwindcss.setup({
        filetypes = {
          "html",
          "css",
          "javascript",
          "javascriptreact",
          "typescript",
          "typescriptreact",
        },
      })

      -- Lua Language Server
      lspconfig.lua_ls.setup({
        settings = {
          Lua = {
            runtime = {
              version = "LuaJIT",
            },
            diagnostics = {
              globals = { "vim" },
            },
            workspace = {
              library = vim.api.nvim_get_runtime_file("", true),
              checkThirdParty = false,
            },
            telemetry = {
              enable = false,
            },
          },
        },
      })

      -- VTSLS (TypeScript/JavaScript Language Server)
      lspconfig.vtsls.setup({
        settings = {
          typescript = {
            preferences = {
              includePackageJsonAutoImports = "auto",
            },
          },
          javascript = {
            preferences = {
              includePackageJsonAutoImports = "auto",
            },
          },
        },
      })

      -- Biome
      lspconfig.biome.setup({
        settings = {
          biome = {
            lsp = {
              formatOnSave = true,
              showReferences = true,
              showSignatures = true,
              signatureHelpOnSelect = true,
            },
          },
        },
      })


      -- ESLint Language Server
      lspconfig.eslint.setup({
        filetypes = {
          "javascript",
          "javascriptreact",
          "typescript",
          "typescriptreact",
        },
        settings = {
          codeActionOnSave = {
            enable = true,
            mode = "all"
          },
          format = true,
          run = "onType",
          validate = "on",
        },
      })
    end,
  },
}
