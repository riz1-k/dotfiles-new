return {
  "nvim-telescope/telescope.nvim",
  branch = "0.1.x",
  dependencies = {
    "nvim-lua/plenary.nvim",
    { "nvim-telescope/telescope-fzf-native.nvim", build = "make" },
    "nvim-tree/nvim-web-devicons",
  },
  config = function()
    local telescope = require "telescope"
    local actions = require "telescope.actions"
    local sorters = require "telescope.sorters"

    vim.api.nvim_set_keymap("n", "<C-p>", "<cmd>Telescope find_files<CR>", { noremap = true, silent = true })

    telescope.setup {
      pickers = {
        buffers = {
          show_all_buffers = true,
          sort_lastused = true,
          theme = "dropdown",
        },
      },
      defaults = {
        path_display = { "smart" },
        mappings = {
          i = {
            ["<C-k>"] = actions.move_selection_previous, -- move to prev result
            ["<C-j>"] = actions.move_selection_next, -- move to next result
            ["<C-q>"] = actions.send_selected_to_qflist + actions.open_qflist,
          },
        },
        initial_mode = "insert",
        selection_strategy = "reset",
        sorting_strategy = "ascending",
        layout_strategy = "horizontal",
        layout_config = {
          prompt_position = "top",
          horizontal = {
            mirror = false,
          },
          vertical = {
            mirror = false,
          },
        },
        file_sorter = sorters.get_fuzzy_file,
        file_ignore_patterns = { "gtk/**/*", "node_modules", ".git", "pdf_viewer" },
        generic_sorter = sorters.get_generic_fuzzy_sorter,
      },
    }

    telescope.load_extension "fzf"

    -- set keymaps
    local keymap = vim.keymap -- for conciseness

    keymap.set("n", "<leader>ff", "<cmd>Telescope find_files<cr>", { desc = "Fuzzy find files in cwd" })
    keymap.set("n", "<leader>fw", "<cmd>Telescope live_grep<cr>", { desc = "Find string in cwd" })
    keymap.set("n", "<leader>fc", "<cmd>Telescope grep_string<cr>", { desc = "Find string under cursor in cwd" })
    keymap.set("n", "<leader>fb", "<cmd>Telescope buffers<cr>", { desc = "Find buffer" })
    keymap.set("n", "<leader>fu", "<cmd>Telescope colorscheme<cr>", { desc = "Find colorscheme" })
  end,
}
