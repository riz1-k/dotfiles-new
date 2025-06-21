return {
  -- Comments
  {
    "echasnovski/mini.comment",
    version = false,
    event = "VeryLazy",
    config = function()
      local MiniComment = require "mini.comment"
      MiniComment.setup {
        mappings = {
          comment_line = "<Leader>/",
          comment_visual = "<Leader>/",
        },
      }
    end,
  },
  -- File explorer (this works properly with oil unlike nvim-tree)
  {
    "echasnovski/mini.files",
    event = { "BufReadPre", "BufNewFile" },
    config = function()
      local MiniFiles = require "mini.files"
      MiniFiles.setup {
        mappings = {
          go_in = "<CR>", -- Map both Enter and L to enter directories or open files
          go_in_plus = "L",
          go_out = "-",
          go_out_plus = "H",
        },
      }
      vim.keymap.set("n", "<leader>ee", "<cmd>lua MiniFiles.open()<CR>", { desc = "Toggle mini file explorer" }) -- toggle file explorer
      vim.keymap.set("n", "<leader>ef", function()
        MiniFiles.open(vim.api.nvim_buf_get_name(0), false)
        MiniFiles.reveal_cwd()
      end, { desc = "Toggle into currently opened file" })
    end,
  },
}
