import math
import time

import tkinter as tk

from winrawin import hook_raw_input_for_window, RawInputEvent, list_devices, Mouse, Keyboard


def tk_rgb(r, g, b):
    return "#%02x%02x%02x" % (r, g, b)


def open_window():
    window = tk.Tk()
    window.title("Device Monitoring")
    window.geometry('640x600')

    def create_copiable_label(parent, text, **kwargs):
        def copy(_event):
            window.clipboard_clear()
            window.clipboard_append(text)
            print(f"Copied to clipboard: {text}")

        label = tk.Label(parent, text=text[:8] + "..." + text[-24:], **kwargs)
        label.bind("<Button-1>", copy)
        return label

    label_info = tk.Label(text="Click on an entry to copy it to the clipboard.")
    label_info.pack()

    table = tk.Frame(window)
    table.pack()

    label1 = tk.Label(table, text="Mice")
    label2 = tk.Label(table, text="Keyboards")
    label3 = tk.Label(table, text="Other")
    label1.grid(row=0, column=0)
    label2.grid(row=0, column=1)
    label3.grid(row=0, column=2)

    labels = {}
    n_mice = 0
    n_keyboards = 0
    n_hid = 0
    for device in list_devices():
        label = create_copiable_label(table, text=device.name, bg=tk_rgb(0, 0, 0))
        labels[device] = label
        if isinstance(device, Mouse):
            n_mice += 1
            label.grid(row=n_mice, column=0)
        elif isinstance(device, Keyboard):
            n_keyboards += 1
            label.grid(row=n_keyboards, column=1)
        else:
            n_hid += 1
            label.grid(row=n_hid, column=2)

    last_event_times = {d: -100 for d in list_devices()}

    def update_colors():
        for device, label in labels.items():
            if not device.is_connected():
                label.config(bg=tk_rgb(255, 0, 0))
            else:
                last = time.perf_counter() - last_event_times[device]
                fac = 1 - math.exp(-last)
                label.config(bg=tk_rgb(int(255 * fac), 255, int(255 * fac)))
        window.after(10, update_colors)

    window.after(10, update_colors)

    def process_event(e: RawInputEvent):
        last_event_times[e.device] = e.time

    hook_raw_input_for_window(window.winfo_id(), process_event)
    window.mainloop()


if __name__ == '__main__':
    open_window()
