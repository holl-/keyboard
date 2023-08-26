import time
from dataclasses import dataclass
from typing import Optional, Sequence

from ._win_raw_input import *
from .usb_ids import parse_vid_pid, lookup_product


@dataclass
class RawInputDevice:
    """
    Base class for input devices.

    There are three types of raw input devices:

    * `Mouse`
    * `Keyboard`
    * `HID`

    Some devices cannot be identified, e.g. events caused by software.
    Then the devices stores an invalid handle and has `path=None`.
    """

    handle: int
    """Windows handle for the device. This is valid only in the current session. For a unique identifier, use `path`."""
    path: Optional[str]
    """Unique device identifier. This string typically includes vendor and product id."""
    vendor_id: int
    """USB vendor id"""
    vendor_name: Optional[str]
    """Vendor name or `None` if unknown."""
    product_id: int
    """USB product id"""
    product_name: str
    """Product name or `None` if unknown."""

    def is_connected(self):
        """
        Checks whether the handle associated with this device is still valid.
        If not, the device has most likely been disconnected.
        """
        return is_connected(self.handle)


@dataclass
class Keyboard(RawInputDevice):
    """
    Keyboards send events when a key is pressed, released or while a key is being held.
    All events have either `event_type='down'` for key pressed/held or `event_type='up'` for key released.
    The `RawInputEvent.code` denotes the scan code and `RawInputEvent.name` the human-readable name of the key.
    If a keypad key is pressed, the `RawInputEvent.device_type` is set to `'keypad'`.

    This class inherits the method `RawInputDevice.is_connected()`.
    """
    keyboard_type: str
    subtype: int
    scan_code_mode: int
    num_function_keys: int
    num_indicators: int
    num_keys: int

    def __hash__(self):
        return self.handle or 0

    def __eq__(self, other):
        return isinstance(other, Keyboard) and other.handle == self.handle


@dataclass
class Mouse(RawInputDevice):
    """
    Mice can send the following event types:

    * `'down'` when a button is pressed
    * `'up'` when a button is released
    * `'move'` when the mouse is moved
    * `'wheel-up'` when the mouse is turned upwards
    * `'wheel-down'` when the mouse is turned down

    In case of `move` events, `RawInputEvent.delta_x` and `RawInputEvent.delta_y` hold the amount by which the mouse moved.
    For button events, `code` denotes the button index and `name` stores the human-readable button name.

    This class inherits the method `RawInputDevice.is_connected()`.
    """
    mouse_type: str
    """HID mouse, HID wheel mouse, Mouse with horizontal wheel, unknown"""
    num_buttons: int
    sample_rate: Optional[int]
    """data points per second (if available)"""
    has_horizontal_wheel: bool

    def __hash__(self):
        return self.handle or 0

    def __eq__(self, other):
        return isinstance(other, Mouse) and other.handle == self.handle


@dataclass
class HID(RawInputDevice):
    """
    HID devices that are neither classified as keyboard nor mouse.
    These devices send raw data as bytes, stored in `RawInputEvent.data`.
    All input events are classified as `event_type='data'`.

    This class inherits the method `RawInputDevice.is_connected()`.
    """
    version_number: int
    usage_page: int
    usage_page_name: str
    usage: int
    usage_name: str

    def __hash__(self):
        return self.handle or 0

    def __eq__(self, other):
        return isinstance(other, HID) and other.handle == self.handle


CACHED_DEVICES = {}  # handle -> RawInputDevice


def list_devices() -> Sequence[RawInputDevice]:
    """
    Retrieves a list of all currently registered raw input devices using `GetRawInputDeviceList`.
    For each device, this function also looks up its unique name and additional information.

    All discovered devices are cached by their `handle` which is unique during this session.

    Returns:
        Devices as sequence of `RawInputDevice`
    """
    devices = [get_device(dev.dwType, dev.hDevice) for dev in get_raw_input_device_list()]
    CACHED_DEVICES.clear()
    CACHED_DEVICES.update({d.handle: d for d in devices})
    return devices


def get_device(dw_type: int, handle: int) -> RawInputDevice:
    if handle in CACHED_DEVICES:
        return CACHED_DEVICES[handle]
    path = get_device_path(handle)
    info = get_device_info(handle)
    if dw_type == 0:
        mouse_type = MOUSE_TYPES.get(info.u.mouse.dwId, 'unknown')
        num_buttons = info.u.mouse.dwNumberOfButtons
        sample_rate = info.u.mouse.dwSampleRate or None
        has_horizontal_wheel = bool(info.u.mouse.fHasHorizontalWheel)
        vendor_id, product_id = parse_vid_pid(path)
        vendor_name, product_name = lookup_product(vendor_id, product_id)
        device = Mouse(handle, path, vendor_id, vendor_name, product_id, product_name, mouse_type, num_buttons, sample_rate, has_horizontal_wheel)
    elif dw_type == 1:
        kb_type = KEYBOARD_TYPES.get(info.u.keyboard.dwType, 'unknown')
        subtype = info.u.keyboard.dwSubType
        scan_code_mode = info.u.keyboard.dwKeyboardMode
        num_function_keys = info.u.keyboard.dwNumberOfFunctionKeys
        num_indicators = info.u.keyboard.dwNumberOfIndicators
        num_keys = info.u.keyboard.dwNumberOfKeysTotal
        vendor_id, product_id = parse_vid_pid(path)
        vendor_name, product_name = lookup_product(vendor_id, product_id)
        device = Keyboard(handle, path, vendor_id, vendor_name, product_id, product_name, kb_type, subtype, scan_code_mode, num_function_keys, num_indicators, num_keys)
    elif dw_type == 2:
        vendor_id = info.u.hid.dwVendorId
        product_id = info.u.hid.dwProductId
        version_number = info.u.hid.dwVersionNumber
        usage_page = info.u.hid.usUsagePage
        usage_page_name, page_entries = USAGE_PAGE_NAMES.get(usage_page, ('unknown', {}))
        usage = info.u.hid.usUsage
        usage_name = page_entries.get(usage, 'unknown')
        vendor_name, product_name = lookup_product(vendor_id, product_id)
        device = HID(handle, path, vendor_id, vendor_name, product_id, product_name, version_number, usage_page, usage_page_name, usage, usage_name)
    else:
        raise NotImplementedError(f"Unknown device type: {dw_type}")
    CACHED_DEVICES[handle] = device
    return device


@dataclass
class RawInputEvent:
    """
    These events are sent to the callback registered via `hook_raw_input_for_window()`.
    """
    event_type: str
    """'up'/'down' for buttons, 'move' for mouse, 'data' for HID"""
    code: int
    """button index or scan code, -1 for HID"""
    name: Optional[str]
    """mouse button or key name"""
    device_type: str
    """'keyboard', 'keypad', 'mouse', 'controller'"""
    device: RawInputDevice
    """Source `RawInputDevice`"""
    delta_x: Optional[int]
    """Horizontal mouse movement"""
    delta_y: Optional[int]
    """Vertical mouse movement"""
    hwnd: int
    """Window handle of the window this event was sent to"""
    time: float
    """Time of the event measured vis `time.perf_counter()`"""
    data: Optional[bytes]
    """Raw data sent by HID devices"""
    raw: RAWINPUT
    """Raw event data sent from Windows"""


def hook_raw_input_for_window(hwnd,
                              callback: Callable[[RawInputEvent], None],
                              device_types=('Pointer', 'Mouse', 'Joystick', 'Game Pad', 'Keyboard', 'Keypad', 'Multi-axis Controller')):
    """
    Listen to raw input events sent to a window by the operating system (Windows).

    This is implemented by overriding the window's procedure function which is the only function that receives raw input events.
    The new procedure calls the callback before executing the regular window procedure.

    The HWND can be retrieved from a TK instance using `window.winfo_id()` and similar functions exist for other libraries.

    Args:
        hwnd: Window handle (HWND)
            This can be obtained from various libraries that open windows, such as

            * `window.winfo_id()` in `tkinter`
            * `pygame.display.get_wm_info()['window']` in PyGame
            * Most functions in win32gui
            * `fig.canvas.manager.window.winId()` in matplotlib using PyQt5

        callback: Function
        device_types:
           Types of devices to listen for.
           This defines the usage page and value.
           Supported device types are `'Pointer'`, `'Mouse'`, `'Joystick'`, `'Game Pad'`, `'Keyboard'`, `'Keypad'`, `'Multi-axis Controller'`.
    """
    def process_message(hwnd, msg, wParam, lParam):  # Called by Windows to handle window events.
        if msg == WM_INPUT:  # raw input. other events don't reference the device
            event_time = time.perf_counter()
            dwSize = c_uint()
            if user32.GetRawInputData(lParam, RID_INPUT, NULL, byref(dwSize), sizeof(RAWINPUTHEADER)):
                raise ctypes.WinError(GetLastError())
            raw = RAWINPUT()
            assert user32.GetRawInputData(lParam, RID_INPUT, byref(raw), byref(dwSize), sizeof(RAWINPUTHEADER)) == dwSize.value
            device = get_device(raw.header.dwType, raw.header.hDevice)
            if raw.header.dwType == 1:  # Keyboard
                if raw.data.mouse.usFlags in MOVE_MODES and raw.data.mouse._s2.usButtonFlags == 0:  # actually caused by mouse
                    device = get_device(0, raw.header.hDevice)
                assert dwSize.value == 40
                message = raw.data.keyboard.message
                vk_code = raw.data.keyboard.vk_code
                scan_code = raw.data.keyboard.scan_code
                # flags = raw.data.keyboard.flags
                if vk_code in VIRTUAL_KEYBOARD:
                    key_name, is_keypad = VIRTUAL_KEYBOARD[vk_code]
                else:
                    key_name, is_keypad = KEY_NAMES_LOWER[scan_code], False
                evt_type = KEY_EVENT_TYPE[message]
                event = RawInputEvent(evt_type, scan_code, key_name, 'keypad' if is_keypad else 'keyboard', device, None, None, hwnd, event_time, None, raw)
            elif raw.header.dwType == 0:  # Mouse
                assert dwSize.value == 48
                button = raw.data.mouse.ulButtons
                if button == 0:
                    mode = raw.data.mouse.usFlags
                    event = RawInputEvent('move', mode, MOVE_MODES.get(mode, 'unknown'), 'mouse', device, raw.data.mouse.lLastX, raw.data.mouse.lLastY, hwnd, event_time, None, raw)
                else:
                    evt_type, button_id, button_name = MOUSE_BUTTONS[button]
                    event = RawInputEvent(evt_type, button_id, button_name, 'mouse', device, None, None, hwnd, event_time, None, raw)
            elif raw.header.dwType == 2:  # Controller
                size_hid = raw.data.hid.dwSizeHid  # The size, in bytes, of each HID input in bRawData.
                count = raw.data.hid.dwCount  # The number of HID inputs in bRawData.
                raw_data = raw.data.hid.bRawData  # The raw input data, as an array of bytes.
                raw_data_ptr = ctypes.cast(raw_data, POINTER(BYTE * (size_hid * count)))
                raw_data_bytes = ctypes.string_at(raw_data_ptr, sizeof(raw_data_ptr.contents))
                event = RawInputEvent('data', -1, f'{count} x {size_hid} bytes', 'hid', device, None, None, hwnd, event_time, raw_data_bytes, raw)
            else:
                raise NotImplementedError
            callback(event)
    if hwnd:
        set_window_procedure(hwnd, process_message, call_original=True)
    else:
        hwnd = invisible_window(process_message)
    for device_type in device_types:
        enable_raw_input_for_window(hwnd, device_type)
