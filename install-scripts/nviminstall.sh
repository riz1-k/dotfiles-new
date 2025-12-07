#!/bin/bash

# essentials
sudo apt-get install -y ninja-build gettext cmake curl build-essential ripgrep

# neovim
git clone https://github.com/neovim/neovim.git ~/neovim
cd ~/neovim
git checkout stable
make CMAKE_BUILD_TYPE=RelWithDebInfo
sudo make install

nvim
