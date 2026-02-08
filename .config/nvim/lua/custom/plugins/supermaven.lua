return {
  'supermaven-inc/supermaven-nvim',
  event = 'InsertEnter',
  enabled = true,
  config = function()
    require('supermaven-nvim').setup {
      keymaps = {
        accept_suggestion = '<Tab>',
      },
      condition = function()
        return vim.bo.filetype ~= 'markdown'
      end,
    }
  end,
}
