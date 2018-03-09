#!/bin/bash
cd $(dirname $(readlink $0))
echo "Starting MCEdit..."
f=
if [ -f "mcedit.py" ]
then
    f="mcedit.py"
elif [ -f "mcedit.pyc" ]
then
    f="mcedit.pyc"
elif [ -f "mcedit" ]
then
    f="mcedit"
else
    echo "MCEdit program not found."
    echo "Check your installation and retry."
    exit 1
fi
python2 $f "${@}"
status=$?
read -n 1 -p "Press any key to close."
echo ""
exit $status

