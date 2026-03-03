import os
import requests
import urllib3
import time
import base64
import json
import threading
from collections import defaultdict, deque

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Aruba IoT Gateway configuration
APIGW_URL = os.getenv('APIGW_URL', 'http://192.168.1.92:31080')
# Add http:// if missing
if not APIGW_URL.startswith('http://') and not APIGW_URL.startswith('https://'):
    APIGW_URL = f'http://{APIGW_URL}'
APIKEY = os.getenv('APIKEY', '69a54a133b2c436ce3a31580-0-9')
HEADERS = {"accept": "application/json", "apikey": APIKEY}

# MACs identifies comme bracelets Corsano 287-2B
known_devices = set()
# Stockage: {mac: {'serial': str, 'aps': {apMac: deque(maxlen=5)}}}
devices = defaultdict(lambda: {'serial': None, 'aps': defaultdict(lambda: deque(maxlen=20))})

def extract_serial(payload_b64):
    """Extract serial from SCAN_RSP"""
    try:
        payload = base64.b64decode(payload_b64)
        if len(payload) >= 13 and payload[0:2] == b'\x12\x16':
            return payload[5:13].decode('ascii', errors='ignore')
    except:
        pass
    return None

def print_stats():
    """Print one line per device with avg RSSI per AP"""
    print()
    for mac in sorted(devices.keys()):
        d = devices[mac]
        serial = d['serial'] or '?'
        ap_parts = []
        for ap_mac in sorted(d['aps'].keys()):
            samples = list(d['aps'][ap_mac])
            if samples:
                avg_rssi = sum(samples) / len(samples)
                ap_parts.append(f"AP({ap_mac}|RSSI:{avg_rssi:.0f})")
        if ap_parts:
            print(f"Device({mac}|SN:{serial}) -> {','.join(ap_parts)}")

def _start_notification_listener():
    """Start listener thread"""
    def _listen():
        try:
            r = requests.get(f"{APIGW_URL}/api/v3/ble/stream/packets",
                             headers=HEADERS,
                             stream=True,
                             timeout=None)
            
            packet_count = 0

            for line in r.iter_lines():
                if line:
                    data = json.loads(line)
                    result = data.get('result', {})

                    mac = result.get('mac')
                    rssi = result.get('rssi')
                    frame_type = result.get('frameType')
                    payload = result.get('payload')
                    ap_mac = result.get('apMac', 'Unknown')

                    # Identify Corsano 287-2B from ADV_IND payload
                    if frame_type == 'BLE_FRAME_TYPE_ADV_IND' and payload:
                        try:
                            raw = base64.b64decode(payload)
                            if b'287-2B' in raw:
                                known_devices.add(mac)
                        except:
                            pass

                    if mac and rssi is not None and mac in known_devices:
                        # Add RSSI sample per AP
                        devices[mac]['aps'][ap_mac].append(rssi)

                        # Extract serial if SCAN_RSP
                        if frame_type == 'BLE_FRAME_TYPE_SCAN_RSP' and payload:
                            serial = extract_serial(payload)
                            if serial:
                                devices[mac]['serial'] = serial
                        
                        packet_count += 1
                        
                        # Print every 20 packets
                        if packet_count % 5 == 0:
                            print_stats()

        except Exception as e:
            print(f"Error: {e}")

    thread = threading.Thread(target=_listen, daemon=True)
    thread.start()
    return thread

def main():
   
    # Start listening
    print("Starting RSSI Monitor...")
    listener_thread = _start_notification_listener()
    
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n\nStopping...")
        print_stats()

if __name__ == "__main__":
    main()