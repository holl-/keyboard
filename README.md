
win-raw-in
========

Enumerate raw input devices and receive input events with device ID on Windows.

Win-raw-in works by hooking into a window procedure to intercept events.
This requires your application to open a window and obtain the corresponding hwnd.
This can be done using `ctypes` or `win32gui` or using a high-level library such as `tkinter` (see example below).

For more documentation, see the [🔗 API](https://holl-.github.io/win-raw-in/winrawin/).

## Installation

Get the latest stable version with pip:

```bash
pip install win-raw-in
```


Get the latest (possible unstable) version:

```bash
pip install git+https://github.com/holl-/win-raw-in.git
```

## Examples

### List input devices

This example uses [`list_devices()`](https://holl-.github.io/win-raw-in/winrawin/#winrawin.list_devices) to enumerate all raw input devices registered with Windows.
Each device is an instance of [`RawInputDevice`](https://holl-.github.io/win-raw-in/winrawin/#winrawin.RawInputDevice).

```python
import winrawin

for device in winrawin.list_devices():
    if isinstance(device, winrawin.Mouse):
        print(f"{device.mouse_type} name='{device.path}'")
    if isinstance(device, winrawin.Keyboard):
        print(f"{device.keyboard_type} with {device.num_keys} keys name='{device.path}'")
```

### Listen to input events

This example uses `tkinter` to open a window and retrieve the hwnd.
Then, [`hook_raw_input_for_window()`](https://holl-.github.io/win-raw-in/winrawin/#winrawin.hook_raw_input_for_window) is used to intercept [`RawInputEvents`](https://holl-.github.io/win-raw-in/winrawin/#winrawin.RawInputEvent).

```python
import winrawin
import tkinter as tk

def handle_event(e: winrawin.RawInputEvent):
    if e.event_type == 'move':
        pass  # don't print mouse move events
    elif e.event_type == 'down':
        print(f"Pressed {e.name} on {e.device_type} {e.device.handle}")
    else:
        print(e)

window = tk.Tk()
winrawin.hook_raw_input_for_window(window.winfo_id(), handle_event)
window.mainloop()
```

For a more interactive demo, see [tk_device_monitor.py](examples/tk_device_monitor.py).


## Related Packages

This package was inspired by the [keyboard](https://github.com/boppreh/keyboard/tree/windows-device-id) package.
Unfortunately, `keyboard` does not distinguish between multiple input devices on Windows.
