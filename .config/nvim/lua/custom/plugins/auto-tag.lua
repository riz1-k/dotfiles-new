return {
  'windwp/nvim-ts-autotag',

  config = function()
    -- import nvim-ts-autotag plugin
    local autotag = require 'nvim-ts-autotag'

    autotag.setup {
      setup = {
        enable = true, -- Enable this plugin (Can be enabled/disabled later via commands)
        filetypes = { -- Filetypes to enable this plugin for
          'html',
          'javascript',
          'javascriptreact',
          'typescript',
          'typescriptreact',
        },
      },
      opts = {
        enable_close = true, -- Auto close tags
        enable_rename = true, -- Auto rename pairs of tags
        enable_close_on_slash = false, -- Auto close on trailing </
      },
    }
  end,
}
