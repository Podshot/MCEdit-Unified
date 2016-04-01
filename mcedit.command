#!/bin/bash

ask() {
    # http://djm.me/ask
    while true; do
 
        if [ "${2:-}" = "R" ]; then
            default=Y
        elif [ "${2:-}" = "enter" ]; then
            default=Y
        elif [ "${2:-}" = "Y" ]; then
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
if ! type "python2" > /dev/null; then
    # Just let all command line parameter be sent to the program.
    python -B mcedit.py    
else
    python2 -B mcedit.py
fi
echo "-------------------------"
if ask "Press R to restart MCEdit, any other key to exit:"; then
	clear
	bash mcedit.command
else
    echo "Quitting"
fi
