return {
  {
    "mason-org/mason.nvim",
    opts = function(_, opts)
      opts.ensure_installed = opts.ensure_installed or {}
      vim.list_extend(opts.ensure_installed, {
        "eslint-lsp",
        "eslint_d",
        "pyright",
        "ruff",
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
          map("gd", Snacks.picker.lsp_definitions, "[G]oto [D]efinition")
          map("gr", Snacks.picker.lsp_references, "[G]oto [R]eferences")
          map("gi", Snacks.picker.lsp_implementations, "[G]oto [I]mplementation")
          map("<leader>D", Snacks.picker.lsp_type_definitions, "Type [D]efinition")
          map("<leader>ds", Snacks.picker.lsp_symbols, "[D]ocument [S]ymbols")
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
      local capabilities = vim.lsp.protocol.make_client_capabilities()
      capabilities.general = capabilities.general or {}
      capabilities.general.positionEncodings = { "utf-16" }

      require("mason-lspconfig").setup({
        ensure_installed = {
          "html",
          "cssls",
          "tailwindcss",
          "lua_ls",
          "vtsls",
          "eslint",
          "biome",
          "pyright",
          "ruff",
        },
        automatic_enable = false,
        automatic_installation = true,
      })

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

      vim.api.nvim_create_autocmd("BufWritePre", {
        pattern = { "*.py", "*.pyi" },
        callback = function()
          require("conform").format({
            async = false,
            lsp_fallback = false,
            timeout_ms = 2000,
          })
        end,
      })

      local function setup(server, config)
        config = config or {}
        config.capabilities = vim.tbl_deep_extend("force", {}, capabilities, config.capabilities or {})
        config.offset_encoding = "utf-16"
        vim.lsp.config(server, config)
        vim.lsp.enable(server)
      end

      setup("html")

      setup("cssls")

      setup("tailwindcss", {
        filetypes = {
          "html",
          "css",
          "javascript",
          "javascriptreact",
          "typescript",
          "typescriptreact",
        },
      })

      setup("lua_ls", {
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

      setup("vtsls", {
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

      setup("biome", {
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

      setup("eslint", {
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

      setup("pyright", {
        settings = {
          python = {
            analysis = {
              typeCheckingMode = "basic",
            },
          },
        },
      })

      setup("ruff", {
        on_attach = function(client)
          client.server_capabilities.documentFormattingProvider = false
        end,
      })
    end,
  },
}
