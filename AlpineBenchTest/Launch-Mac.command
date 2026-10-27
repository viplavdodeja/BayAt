#!/bin/sh
cd "$(dirname "$0")" || exit 1
if [ -x .venv/bin/python ]; then
  .venv/bin/python -m app.main
elif [ -x /opt/homebrew/bin/python3.14 ]; then
  /opt/homebrew/bin/python3.14 -m app.main
else
  python3 -m app.main
fi
status=$?
if [ "$status" -ne 0 ]; then
  printf '\nUnable to launch. Check that Python 3 and Tkinter are installed. Press Enter to close.\n'
  read -r response
fi
exit "$status"
