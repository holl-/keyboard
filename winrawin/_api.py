from ._win_raw_input import *


@dataclass
class RawInputDevice:
    handle: int
    name: str

    def is_connected(self):
        return is_connected(self.handle)


@dataclass
class Keyboard(RawInputDevice):
    kb_type: str
    subtype: int
    scan_code_mode: int
    num_function_keys: int
    num_indicators: int
    num_keys: int

    def __hash__(self):
        return self.handle

    def __eq__(self, other):
        return isinstance(other, Keyboard) and other.handle == self.handle


@dataclass
class Mouse(RawInputDevice):
    mouse_type: str  # HID mouse, HID wheel mouse, Mouse with horizontal wheel, unknown
    num_buttons: int
    sample_rate: Optional[int]  # data points per second (if available)
    has_horizontal_wheel: bool

    def __hash__(self):
        return self.handle

    def __eq__(self, other):
        return isinstance(other, Mouse) and other.handle == self.handle


@dataclass
class HID(RawInputDevice):
    vendor_id: int
    product_id: int
    version_number: int
    usage_page: int
    usage_page_name: str
    usage: int
    usage_name: str

    def __hash__(self):
        return self.handle

    def __eq__(self, other):
        return isinstance(other, HID) and other.handle == self.handle


CACHED_DEVICES = {}  # handle -> RawInputDevice


def list_devices():
    devices = [get_device(dev.dwType, dev.hDevice) for dev in get_raw_input_device_list()]
    CACHED_DEVICES.clear()
    CACHED_DEVICES.update({d.handle: d for d in devices})
    return devices


def get_device(dw_type: int, handle: int) -> RawInputDevice:
    if handle in CACHED_DEVICES:
        return CACHED_DEVICES[handle]
    name = get_device_name(handle)
    info = get_device_info(handle)
    if dw_type == 0:
        mouse_type = MOUSE_TYPES.get(info.u.mouse.dwId, 'unknown')
        num_buttons = info.u.mouse.dwNumberOfButtons
        sample_rate = info.u.mouse.dwSampleRate or None
        has_horizontal_wheel = bool(info.u.mouse.fHasHorizontalWheel)
        device = Mouse(handle, name, mouse_type, num_buttons, sample_rate, has_horizontal_wheel)
    elif dw_type == 1:
        kb_type = KEYBOARD_TYPES.get(info.u.keyboard.dwType, 'unknown')
        subtype = info.u.keyboard.dwSubType
        scan_code_mode = info.u.keyboard.dwKeyboardMode
        num_function_keys = info.u.keyboard.dwNumberOfFunctionKeys
        num_indicators = info.u.keyboard.dwNumberOfIndicators
        num_keys = info.u.keyboard.dwNumberOfKeysTotal
        device = Keyboard(handle, name, kb_type, subtype, scan_code_mode, num_function_keys, num_indicators, num_keys)
    elif dw_type == 2:
        vendor_id = info.u.hid.dwVendorId
        product_id = info.u.hid.dwProductId
        version_number = info.u.hid.dwVersionNumber
        usage_page = info.u.hid.usUsagePage
        usage_page_name, page_entries = USAGE_PAGE_NAMES.get(usage_page, ('unknown', {}))
        usage = info.u.hid.usUsage
        usage_name = page_entries.get(usage, 'unknown')
        device = HID(handle, name, vendor_id, product_id, version_number, usage_page, usage_page_name, usage, usage_name)
    else:
        raise NotImplementedError(f"Unknown device type: {dw_type}")
    CACHED_DEVICES[handle] = device
    return device


@dataclass
class RawInputEvent:
    event_type: str  # 'up'/'down' for buttons, 'move' for mouse
    code: int  # button index or scan code
    name: Optional[str]  # mouse button or key name
    device_type: str  # 'keyboard', 'keypad', 'mouse', 'controller'
    device: RawInputDevice
    delta_x: Optional[int]  # mouse movement
    delta_y: Optional[int]  # mouse movement
    hwnd: int  # window id
    time: float  # time of the event measured vis time.perf_counter()


def hook_raw_input_for_window(hwnd,
                              callback: Callable[[RawInputEvent], None],
                              device_types=('keyboard', 'mouse', 'controller')):
    """
    Listen to raw input events sent to a window by the operating system (Windows).

    This is implemented by overriding the window's procedure function which is the only function that receives raw input events.
    The new procedure calls the callback before executing the regular window procedure.

    The HWND can be retrieved from a TK instance using `window.winfo_id()` and similar functions exist for other libraries.

    Args:
        hwnd: Window id (HWND)
        callback: Function
        device_types: Types of devices to listen for. Supports 'keyboard' and 'mouse'.
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
                event = RawInputEvent(evt_type, scan_code, key_name, 'keypad' if is_keypad else 'keyboard', device, None, None, hwnd, event_time)
            elif raw.header.dwType == 0:  # Mouse
                assert dwSize.value == 48
                button = raw.data.mouse.ulButtons
                if button == 0:
                    event = RawInputEvent('move', -1, None, 'mouse', device, raw.data.mouse.lLastX, raw.data.mouse.lLastY, hwnd, event_time)
                else:
                    evt_type, button_id, button_name = MOUSE_BUTTONS[button]
                    event = RawInputEvent(evt_type, button_id, button_name, 'mouse', device, None, None, hwnd, event_time)
            else:
                raise NotImplementedError
            callback(event)

    if hwnd:
        set_window_procedure(hwnd, process_message, call_original=True)
    else:
        hwnd = invisible_window(process_message)
    for device_type in device_types:
        enable_raw_input_for_window(hwnd, device_type)
