# Pinned demo shell for captures (§5.2). Started with ZDOTDIR=recorder/zsh and the capture HOME.
HISTFILE=/dev/null
HISTSIZE=0
SAVEHIST=0
setopt interactivecomments no_beep
unsetopt correct correct_all

export TERM=xterm-256color
export COLORTERM=truecolor
export PATH="$HOME/bin:$DEMO_TOOL_PATH:/usr/bin:/bin:/usr/sbin:/sbin"

PROMPT='%F{magenta}splunk-demo%f %F{blue}%~%f $ '
RPROMPT=''

cd "$HOME/payments"
