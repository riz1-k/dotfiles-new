return { -- Highlight, edit, and navigate code
  'nvim-treesitter/nvim-treesitter',
  branch = 'main',
  lazy = false,
  build = ':TSUpdate',
  opts = {
    ensure_installed = {
      'json', 'javascript', 'typescript', 'tsx', 'html', 'css', 'bash', 'lua',
      'python', 'toml',
    },
  },
  config = function(_, opts)
    local treesitter = require 'nvim-treesitter'
    treesitter.setup {}

    local available = treesitter.get_available()
    local installing = {}

    local function enable(buf)
      if not vim.api.nvim_buf_is_loaded(buf) then
        return
      end
      local lang = vim.treesitter.language.get_lang(vim.bo[buf].filetype)
      if not lang then
        return
      end
      local ok, parser = pcall(vim.treesitter.get_parser, buf, lang)
      if ok and parser then
        vim.treesitter.start(buf, lang)
        vim.bo[buf].indentexpr = "v:lua.require'nvim-treesitter'.indentexpr()"
        return true
      end
    end

    local function install(languages)
      local missing = vim.tbl_filter(function(lang)
        return not installing[lang]
      end, languages)
      if #missing == 0 then
        return
      end
      for _, lang in ipairs(missing) do
        installing[lang] = true
      end
      treesitter.install(missing):await(vim.schedule_wrap(function(err)
        for _, lang in ipairs(missing) do
          installing[lang] = nil
        end
        if err then
          vim.notify(tostring(err), vim.log.levels.ERROR)
        end
        for _, buf in ipairs(vim.api.nvim_list_bufs()) do
          enable(buf)
        end
      end))
    end

    vim.api.nvim_create_autocmd('FileType', {
      group = vim.api.nvim_create_augroup('custom-treesitter', { clear = true }),
      callback = function(event)
        local lang = vim.treesitter.language.get_lang(vim.bo[event.buf].filetype)
        if not lang then
          return
        end
        if not enable(event.buf) and vim.list_contains(available, lang) then
          install { lang }
        end
      end,
    })

    install(opts.ensure_installed)
    -- Folding is provided by nvim-ufo's Treesitter provider.
  end,
}
