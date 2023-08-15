
win-raw-in
========

Enumerate raw input devices and receive input events with device ID on Windows.

## Installation

Installation with pip:

```bash
pip install git+https://github.com/holl-/win-raw-in.git
```

## Examples

### List devices

```python
import winrawin

for device in winrawin.list_devices():
    if isinstance(device, winrawin.Mouse):
        print(f"{device.mouse_type} name='{device.name}'")
    if isinstance(device, winrawin.Keyboard):
        print(f"{device.keyboard_type} with {device.num_keys} keys name='{device.name}'")
```

### Raw Input Events

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


## Related Packages

This package was inspired by the [keyboard](https://github.com/boppreh/keyboard/tree/windows-device-id) package.
Unfortunately, it does not distinguish between multiple input devices on Windows.
