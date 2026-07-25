fav_dir_add() {
    # Usage: fav_dir_add <path> [description]
    local target="$1"
    local desc="$2"
    local q_dir="$HOME/Q"
    local list_file="$q_dir/.list"

    # Validate input
    if [[ -z "$target" ]]; then
        echo "Usage: fav_dir_add <path> [description]" >&2
        return 1
    fi

    local abs_path
    abs_path=$(cd -- "$target" 2>/dev/null && pwd -P) || {
        echo "Error: path does not exist or is not accessible: $target" >&2
        return 1
    }

    # Must be a directory
    if [[ ! -d "$abs_path" ]]; then
        echo "Error: not a directory: $abs_path" >&2
        return 1
    fi

    command mkdir -p /tmp/govno

    # Ensure ~/Q exists
    mkdir -p "$q_dir" || {
        echo "Error: cannot create $q_dir" >&2
        return 1
    }

    # Basename for the symlink
    local dirname
    dirname=$(basename "$abs_path")
    local symlink="$q_dir/$dirname"

    # Check for existing symlink/directory
    if [[ -e "$symlink" || -L "$symlink" ]]; then
        echo "Error: '$symlink' already exists (remove it first)" >&2
        return 1
    fi

    # Create symlink
    ln -s "$abs_path" "$symlink" || {
        echo "Error: failed to create symlink" >&2
        return 1
    }

    echo "Added: '$dirname' -> '$abs_path'"

    if [[ -n "$desc" ]]; then
        echo "$dirname: $desc" >> "$list_file"
        echo "Description saved."
    fi
}

__ZSH_FAV_DIR_SCRIPT_DIR="${0:A:h}"

# Define the widget function
zsh_fav_dir_widget() {
    zle -I

    # 1. Check if python3 command is available
    if ! command -v python3 >/dev/null 2>&1; then
        echo -e "\033[31mError: python3 is not installed or not in PATH.\033[0m"
        # zle redisplay
        return 1
    fi

    # Call the python script to pick a path
    local target
    local exit_code
    target=$(python3 "$__ZSH_FAV_DIR_SCRIPT_DIR"/zsh_favorite_dir.py)
    exit_code="$?"

    if [ "$exit_code" -ne "0" ]; then
        zle redisplay
        return
    fi

    # 1. Update your directory state silently
    pushd "$target" > /dev/null
    set-pwd 2>/dev/null || true

    # 3. Save text to stack and clear current line
    zle push-line

    # 4. Trigger a fake "Enter" on the empty line to drop down 
    # to a new prompt. Zsh will instantly auto-pop your text back.
    zle accept-line
}

# Register it with ZLE (Zsh Line Editor)
zle -N zsh_fav_dir_widget

# Bind to keyboard shortcut (e.g., Ctrl+Q)
bindkey '^Q' zsh_fav_dir_widget