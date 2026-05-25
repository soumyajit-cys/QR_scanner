# QR Code Scanner

A modern desktop QR and barcode scanner built with **Python, Tkinter, OpenCV, Pyzbar, and Pillow**.

Scan QR codes from images or directly from a live webcam feed with a clean and responsive graphical interface.

---

## Features

### Image Scanning
- Scan QR codes and barcodes from:
  - PNG
  - JPG / JPEG
  - BMP
  - GIF
  - WebP
  - TIFF
- Preview scanned image with highlighted detection area.
- Supports multiple detections in a single image.

### Live Camera Scanning
- Real-time webcam scanning.
- Automatic QR/barcode detection.
- Duplicate detection prevention.
- Live overlay with bounding boxes and labels.

### Result Management
- View scan history.
- Copy detected content.
- Open detected URLs directly.
- Clear previous results.

### User Interface
- Modern dark-themed design.
- Responsive layout.
- Scrollable result section.
- Live status indicators.

---

# Preview

```text
QR Code Scanner
────────────────────────

[ Open Image ]
[ Start Camera ]

┌───────────────────────┐
│                       │
│     Camera Preview    │
│                       │
└───────────────────────┘

Results:
-------------------------
QR_CODE
https://example.com
[ Copy ] [ Open URL ]
```

---

# Project Structure

```text
qr-scanner/
│
├── main.py
├── README.md
├── requirements.txt
└── assets/
```

---

# Requirements

- Python 3.8+
- Webcam (optional)

Install dependencies:

```bash
pip install opencv-python pyzbar pillow
```

Or:

```bash
pip install -r requirements.txt
```

---

# requirements.txt

Create a file named `requirements.txt`

```txt
opencv-python
pyzbar
pillow
```

---

# Installation

## Clone Repository

```bash
git clone https://github.com/your-username/qr-scanner.git
```

Move into project folder:

```bash
cd qr-scanner
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# Run Application

Start the scanner:

```bash
python main.py
```

Application window will launch.

---

# Usage

## Scan from Image

1. Open the application.
2. Click **Open Image**.
3. Select an image file.
4. View detected QR results.

---

## Scan Using Webcam

1. Click **Start Camera**.
2. Point camera toward QR code.
3. Results appear automatically.
4. Stop camera when finished.

---

# Technologies Used

| Technology | Purpose |
|-----------|---------|
| Python | Core Development |
| Tkinter | GUI |
| OpenCV | Camera Processing |
| Pyzbar | QR Decoding |
| Pillow | Image Handling |
| Webbrowser | URL Opening |

---

# Architecture

## Core Functions

### `decode_frame()`
Converts OpenCV frame into RGB and decodes QR/barcodes.

### `draw_overlay()`
Draws:
- Detection boxes
- Labels
- QR outlines

### `QRScannerApp`
Main application class responsible for:
- GUI
- Camera handling
- Image scanning
- Result management

---

# Performance

- Smooth webcam scanning
- ~30 FPS update cycle
- Duplicate detection cooldown
- Optimized image previews

---

# Error Handling

Handles:

- Missing dependencies
- Camera unavailable
- Invalid images
- Lost camera connection
- Empty scan results

---

# Future Improvements

- Export results
- QR Generator
- Multiple camera support
- Scan timestamps
- Cloud sync
- OCR integration
- Theme customization

---

# License

This project is licensed for educational and personal use.

---

# Author
soumyajit-cys


