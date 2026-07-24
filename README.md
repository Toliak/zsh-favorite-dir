# zsh-favorite-dir

A Zsh widget that lets you quickly jump to saved directories using a  
terminal UI written in Python (3.3+) – **no curses**.

The project is an example of building an interactive ZLE widget with  
only Python’s standard library and raw ANSI escapes.

![screenshot](https://via.placeholder.com/600x300?text=Example+UI+screenshot)

## Overview

Store your directories as subfolders (or symlinks) inside `~/Q` and  
jump to them with `Ctrl+Q`. The built‑in selector shows the list,  
supports searching, and leaves your command line untouched.

**Features**

- Pure Python, zero dependencies
- Search and optional descriptions
- Scrollbar for long lists
- Preserves your Zsh buffer

## Requirements

- Python 3.3 or later
- Zsh (tested with 5.x)
- Unix‑like system (Linux, macOS)

## Installation

1. Place the scripts, e.g. in `~/.zsh/`:

   ```bash
   mkdir -p ~/.zsh
   cp zsh_favorite_dir.zsh ~/.zsh/
   cp zsh_favorite_dir.py ~/.zsh/zsh_favorite_dir.py
   ```

2. Source the Zsh file from `~/.zshrc`:

   ```bash
   source ~/.zsh/zsh_favorite_dir.zsh
   ```

3. Reload: `source ~/.zshrc`

## Directory Setup

Create `~/Q` and add symlinks to your favourite directories:

```bash
mkdir -p ~/Q
ln -s /path/to/projects ~/Q/projects
ln -s /path/to/dotfiles ~/Q/dotfiles
```

All non‑hidden subdirectories appear in the selector.

### Descriptions (optional)

Put a `.list` file in `~/Q` to label your entries:

```
# ~/Q/.list
projects: Work projects and repos
dotfiles: My configuration files
music: Local music collection
```

Format: `directory_name: description`. Missing entries show “No description”.

## Usage

Press `Ctrl+Q` (default) to open the overlay.

- **↑/↓**, **j/k**, **PageUp/PageDown**, **J/K** – move selection
- **Enter** – cd into the chosen directory, restore any saved command line
- **ESC**, **Ctrl+C** or **q** – cancel

### Search

Press `/` then type to filter entries. Selection jumps to the  
first name that **starts with** your query, otherwise to a  
matching name or description. **Backspace** edits the query,  
**ESC** clears it and exits search mode.

## How It Works

1. ZLE calls the `zsh_favorite_dir` function.
2. The Python script opens `/dev/tty` directly for raw input/output.
3. It draws the UI using ANSI sequences, handles keyboard input, and  
   prints the selected real path to stdout.
4. The Zsh function `pushd`s to that directory, then uses  
   `zle push-line` and `zle accept-line` to update the prompt  
   while restoring any previously typed text.

> `accept-line` is used because some themes do not update the  
> working directory without a full prompt redraw.

## Customisation

**Change the data directory** – edit `Q_DIR` at the top of  
`zsh_favorite_dir.py`:

```python
Q_DIR = os.path.join(os.path.expanduser('~'), "MyBookmarks")
```

**Change the keybinding** – modify `bindkey` in  
`zsh_favorite_dir.zsh`, e.g. for `Ctrl+F`:

```zsh
bindkey '^F' zsh_favorite_dir
```
