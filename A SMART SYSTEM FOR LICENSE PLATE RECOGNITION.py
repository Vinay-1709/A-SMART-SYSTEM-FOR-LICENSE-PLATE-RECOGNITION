import cv2
import pytesseract
import winsound
import re
import time
import csv
import os
from datetime import datetime

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Constants
TOTAL_SLOTS = 30
PLATE_PATTERN = r'[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}'
PLATE_HISTORY_TIME = 3  # seconds

# CSV Files
ENTRY_CSV = "detected_plates.csv"
EXIT_CSV = "exited_plates.csv"
FISHY_CSV = "fishy_plates.csv"

# Plate tracking
DETECTED_ENTRY = set()
DETECTED_EXIT = set()
last_seen_entry = {}
last_seen_exit = {}

# Initialize CSVs
for csv_file in [ENTRY_CSV, EXIT_CSV, FISHY_CSV]:
    if not os.path.exists(csv_file):
        with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Plate Number', 'Time'])

# Load plates from file
def load_plate_set(csv_file):
    plates = set()
    if os.path.exists(csv_file):
        with open(csv_file, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                if row:
                    plates.add(row[0])
    return plates

# Save plate to file
def store_plate(csv_file, plate):
    with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([plate, datetime.now().strftime('%Y-%m-%d %H:%M:%S')])

# Video capture
cap = cv2.VideoCapture(0)
mode = 'ENTRY'  # Default mode

print("Press 'E' for ENTRY mode, 'X' for EXIT mode, 'Q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (640, 480))
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    text = pytesseract.image_to_string(
        gray,
        config='--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    )
    cleaned = ''.join(filter(str.isalnum, text)).upper()
    found_plates = re.findall(PLATE_PATTERN, cleaned)

    current_entries = load_plate_set(ENTRY_CSV)
    current_exits = load_plate_set(EXIT_CSV)

    for plate in found_plates:
        now = time.time()

        if mode == 'ENTRY':
            if plate not in current_entries and (plate not in DETECTED_ENTRY or (now - last_seen_entry.get(plate, 0)) > PLATE_HISTORY_TIME):
                DETECTED_ENTRY.add(plate)
                store_plate(ENTRY_CSV, plate)
                winsound.Beep(1000, 200)
                print(f"[ENTRY] {plate}")
                last_seen_entry[plate] = now

        elif mode == 'EXIT':
            if plate not in current_entries:
                winsound.Beep(600, 500)  # Alert sound
                print(f"ERROR PLATE NOT FOUND AT ENTRY: {plate}")
                store_plate(FISHY_CSV, plate)
            elif plate not in current_exits and (plate not in DETECTED_EXIT or (now - last_seen_exit.get(plate, 0)) > PLATE_HISTORY_TIME):
                DETECTED_EXIT.add(plate)
                store_plate(EXIT_CSV, plate)
                winsound.Beep(800, 200)
                print(f"[EXIT] {plate}")
                last_seen_exit[plate] = now

    # Parking stats
    total_entries = len(current_entries)
    total_exits = len(current_exits)
    occupied = max(0, total_entries - total_exits)
    vacant = max(0, TOTAL_SLOTS - occupied)

    # Display info
    cv2.putText(frame, f"MODE: {mode}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    cv2.putText(frame, f"Occupied: {occupied}", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 100, 100), 2)
    cv2.putText(frame, f"Vacant: {vacant}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 255, 100), 2)

    # Crop view (demo placeholder)
    x, y, w, h = 100, 100, 200, 60
    cropped = frame[y:y+h, x:x+w]
    cv2.imshow("Plate Crop", cropped)

    cv2.imshow("Smart Parking Dashboard", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('e'):
        mode = 'ENTRY'
    elif key == ord('x'):
        mode = 'EXIT'

cap.release()
cv2.destroyAllWindows()
