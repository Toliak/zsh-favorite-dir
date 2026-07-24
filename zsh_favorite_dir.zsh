__ZSH_FAV_DIR_SCRIPT_DIR="${0:A:h}"

# Define the widget function
zsh_fav_dir() {
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
zle -N zsh_fav_dir

# Bind to keyboard shortcut (e.g., Ctrl+Q)
bindkey '^Q' zsh_fav_dir