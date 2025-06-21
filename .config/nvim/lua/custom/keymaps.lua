-- set leader key to space
vim.g.mapleader = " "

local keymap = vim.keymap -- for conciseness

keymap.set("i", "jj", "<ESC>", {
  desc = "Exit insert mode with jj",
})

-- window management
keymap.set("n", "<leader>sv", "<C-w>v", {
  desc = "Split window vertically",
}) -- split window vertically
keymap.set("n", "<leader>sh", "<C-w>s", {
  desc = "Split window horizontally",
}) -- split window horizontally
keymap.set("n", "<leader>se", "<C-w>=", {
  desc = "Make splits equal size",
}) -- make split windows equal width & height
keymap.set("n", "<leader>sx", "<cmd>close<CR>", {
  desc = "Close current split",
}) -- close current split window

vim.keymap.set("n", "<Esc>", "<cmd>nohlsearch<CR>")

-- Diagnostic keymaps
vim.keymap.set("n", "<leader>q", vim.diagnostic.setloclist, {
  desc = "Open diagnostic [Q]uickfix list",
})

-- Exit terminal mode in the builtin terminal with a shortcut that is a bit easier
-- for people to discover. Otherwise, you normally need to press <C-\><C-n>, which
-- is not what someone will guess without a bit more experience.
--
-- NOTE: This won't work in all terminal emulators/tmux/etc. Try your own mapping
-- or just use <C-\><C-n> to exit terminal mode
vim.keymap.set("t", "<Esc><Esc>", "<C-\\><C-n>", {
  desc = "Exit terminal mode",
})

-- TIP: Disable arrow keys in normal mode
-- vim.keymap.set('n', '<left>', '<cmd>echo "Use h to move!!"<CR>')
-- vim.keymap.set('n', '<right>', '<cmd>echo "Use l to move!!"<CR>')
-- vim.keymap.set('n', '<up>', '<cmd>echo "Use k to move!!"<CR>')
-- vim.keymap.set('n', '<down>', '<cmd>echo "Use j to move!!"<CR>')

-- Keybinds to make split navigation easier.
--  Use CTRL+<hjkl> to switch between windows
--
--  See `:help wincmd` for a list of all window commands
vim.keymap.set("n", "<C-h>", "<C-w><C-h>", {
  desc = "Move focus to the left window",
})
vim.keymap.set("n", "<C-l>", "<C-w><C-l>", {
  desc = "Move focus to the right window",
})
vim.keymap.set("n", "<C-j>", "<C-w><C-j>", {
  desc = "Move focus to the lower window",
})
vim.keymap.set("n", "<C-k>", "<C-w><C-k>", {
  desc = "Move focus to the upper window",
})

-- diagnostic keymaps
keymap.set("n", "[d", function()
  vim.diagnostic.goto_prev()
  vim.diagnostic.open_float()
end, {
  desc = "Go to previous diagnostic",
})
keymap.set("n", "]d", function()
  vim.diagnostic.goto_next()
  vim.diagnostic.open_float()
end, {
  desc = "Go to next diagnostic",
})

-- rename keymap, leader + l + r
vim.keymap.set("n", "<leader>lr", "<cmd>lua vim.lsp.buf.rename()<CR>", {
  desc = "Rename symbol under cursor",
})

-- telescrope buffers
keymap.set("n", "<S-h>", function()
  require("telescope.builtin").buffers {
    sort_mru = true,
    sort_lastused = true,
    initial_mode = "normal",
  }
end, {
  desc = "Open telescope buffers",
})

-- buffer keymaps
keymap.set("n", "<leader>bc", "<cmd>bd<CR>", {
  desc = "Close buffer",
})
keymap.set("n", "<leader>bC", "<cmd>bufdo bd<CR>", {
  desc = "Close all buffers",
  noremap = true,
  silent = true,
})

-- split keymaps
keymap.set("n", "<leader>|", "<C-w>v", {
  desc = "Split window vertically",
})
keymap.set("n", "<leader>-", "<C-w>s", {
  desc = "Split window horizontally",
})

-- keybind to format file
