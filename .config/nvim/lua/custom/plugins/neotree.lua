return {
  "nvim-neo-tree/neo-tree.nvim",
  branch = "v3.x",
  event = "VeryLazy",
  dependencies = {
    "nvim-lua/plenary.nvim",
    "nvim-tree/nvim-web-devicons", -- not strictly required, but recommended
    "MunifTanjim/nui.nvim",
  },
  config = function()
    require("neo-tree").setup {
      close_if_last_window = true,    -- Close Neo-tree if it is the last window
      popup_border_style = "rounded", -- Style of the popup border
      window = {
        position = "right",           -- Set NeoTree to the right
        width = 40,                   -- You can adjust the width as needed
        mapping_options = {
          noremap = true,
          nowait = true,
        },
        mappings = {},
      },
      filesystem = {
        filtered_items = {
          visible = false, -- when true, they will just be displayed differently than normal items
          hide_dotfiles = true,
          hide_gitignored = true,
        },
        follow_current_file = {
          enabled = true, -- This will find and focus the file in the active buffer every time
          leave_dirs_open = false,
        },
      },
      buffers = {
        follow_current_file = {
          enabled = true,
          leave_dirs_open = false,
        },
      },
      git_status = {
        window = {
          position = "float",
        },
      },
    }

    -- Key mapping to toggle NeoTree
    local keymap = vim.keymap
    keymap.set("n", "<leader>ex", "<cmd>Neotree toggle<CR>", {
      desc = "Toggle file explorer",
    })
  end,
}
