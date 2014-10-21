#!/bin/bash

ask() {
    # http://djm.me/ask
    while true; do
 
        if [ "${2:-}" = "R" ]; then
            default=Y
        else
            default=N
        fi
 
        # Ask the question
        read -p "$1 " REPLY
 
        # Default?
        if [ -z "$REPLY" ]; then
            REPLY=$default
        fi
 
        # Check if the reply is valid
        case "$REPLY" in
            R*|r*) return 0 ;;
                *) return 1 ;;
        esac
 
    done
}


cd "$(dirname "$0")"
python -B mcedit.py
echo "-------------------------"
if ask "Press R or Enter to restart MCEdit any other key to exit:"; then
	clear
	bash mcedit.command
else
    echo "Quitting"
fi