import os.path
import re
from typing import Tuple, Optional


with open(os.path.join(os.path.dirname(__file__), 'usb.ids'), 'r') as usb_ids_file:
    DATABASE = usb_ids_file.read()


def lookup_product(vendor_id: int, product_id: int) -> Tuple[Optional[str], Optional[str]]:
    vendor_id = f'{vendor_id:#06x}'[2:]
    product_id = f'{product_id:#06x}'[2:]
    try:
        vendor_pos = DATABASE.index(f'\n{vendor_id}')
    except ValueError:
        return None, None
    vendor_pos_end = DATABASE.index('\n', vendor_pos+7)
    vendor_name = DATABASE[vendor_pos+7:vendor_pos_end]
    next_vendor_pos = re.search(r'\n[0-9a-zA-Z]', DATABASE[vendor_pos_end:]).start()  # ToDo if this is the last vendor, we get an error
    products_database = DATABASE[vendor_pos_end:vendor_pos_end+next_vendor_pos]
    try:
        product_pos = products_database.index(f'\n\t{product_id}')
        product_pos_end = products_database.index('\n', product_pos+7)
        product_name = products_database[product_pos+7:product_pos_end]
    except ValueError:
        product_name = None
    return vendor_name, product_name
    # ToDo if not in database, download new database http://www.linux-usb.org/usb.ids


def parse_vid_pid(device_id: str):
    if device_id is None:
        return 0, 0
    vendor_id = re.search(r'VID_(.*?)[&#]', device_id).group(1)
    product_id = re.search(r'PID_(.*?)[&#]', device_id).group(1)
    return int(vendor_id, 16), int(product_id, 16)


if __name__ == '__main__':
    vid, pid = parse_vid_pid('\\\\?\\HID#{00001812-0000-1000-8000-00805f9b34fb}&Dev&VID_045e&PID_0b13&REV_0509&0c352633ee04&IG_00#a&3724ae32&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}')
    print(lookup_product(vendor_id=vid, product_id=pid))
