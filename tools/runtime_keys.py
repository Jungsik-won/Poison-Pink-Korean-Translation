#!/usr/bin/env python3
"""Send held macOS key events only to this project's isolated PCSX2 process."""
import argparse
import configparser
import ctypes
import time
from pathlib import Path

KEYS = {'start':109, 'circle':103, 'cross':111, 'up':126, 'down':125,
        'left':123, 'right':124, 'screenshot':100, 'save':122, 'load':99, 'pause':49,
        'triangle':96, 'square':97, 'l1':101, 'r1':98}

PAD_BINDINGS = {'start': ('Start', 'F10'), 'circle': ('Circle', 'F11'),
                'cross': ('Cross', 'F12'), 'up': ('Up', 'Up'),
                'down': ('Down', 'Down'), 'left': ('Left', 'Left'),
                'right': ('Right', 'Right'), 'triangle': ('Triangle', 'F5'),
                'square': ('Square', 'F6'), 'l1': ('L1', 'F9'), 'r1': ('R1', 'F7')}


def validate_bindings(config, keys):
    """A game action must never also change the renderer/aspect or load a state."""
    for key in keys:
        if key not in PAD_BINDINGS:
            continue
        pad, button = PAD_BINDINGS[key]
        expected = 'Keyboard/' + button
        actual = config.get('Pad1', pad, fallback='')
        if actual.strip() != expected:
            raise ValueError(f'{key} input mapping differs from the project configuration')
        for action, binding in config.items('Hotkeys'):
            if binding.strip() == expected:
                raise ValueError(f'{key} conflicts with emulator hotkey {action}')


def send(pid, keys):
    proc = ctypes.CDLL('/usr/lib/libproc.dylib')
    buf = ctypes.create_string_buffer(4096)
    proc.proc_pidpath.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
    if proc.proc_pidpath(pid, buf, len(buf)) <= 0:
        raise ValueError('Cannot identify process executable')
    expected = Path(__file__).resolve().parents[1] / 'build/runtime/PCSX2-v2.6.3.app/Contents/MacOS/PCSX2'
    if Path(buf.value.decode()).resolve() != expected:
        raise ValueError('Refusing input to a different application')
    config = configparser.ConfigParser(interpolation=None, strict=False)
    config.optionxform = str
    config.read(expected.parents[3] / 'inis/PCSX2.ini')
    validate_bindings(config, keys)
    cg = ctypes.CDLL('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')
    cf = ctypes.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
    cg.CGEventCreateKeyboardEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint16, ctypes.c_bool]
    cg.CGEventCreateKeyboardEvent.restype = ctypes.c_void_p
    cg.CGEventPostToPid.argtypes = [ctypes.c_int, ctypes.c_void_p]
    cf.CFRelease.argtypes = [ctypes.c_void_p]
    for key in keys:
        for down in (True, False):
            event = cg.CGEventCreateKeyboardEvent(None, KEYS[key], down)
            if not event:
                raise ValueError('Failed to create key event')
            cg.CGEventPostToPid(pid, event)
            cf.CFRelease(event)
            time.sleep(0.25 if down else 0.75)
        print(key, flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid',type=int,required=True)
    parser.add_argument('keys',choices=list(KEYS),nargs='+')
    args=parser.parse_args()
    send(args.pid,args.keys)
