"""Run from the portable application folder: python -m app.main."""
import sys


def main():
    try:
        import tkinter
        if tkinter.TkVersion < 8.6:
            print("This Python uses outdated Tk, which can show a blank window on modern macOS. Use Python with Tk 8.6 or newer. On this Mac, run python3 -m app.main after installing python-tk@3.14. Do not use /usr/bin/python3.", file=sys.stderr)
            return 1
        from .wizard import Wizard
    except ModuleNotFoundError as error:
        if error.name not in {"tkinter", "_tkinter"}:
            raise
        print("This Python installation is missing Tkinter. Install Python with Tcl/Tk support, then launch again. See README.md.", file=sys.stderr)
        return 1
    Wizard().mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
