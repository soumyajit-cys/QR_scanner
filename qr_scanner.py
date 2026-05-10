"""
QR Code Scanner
===============
Scan QR codes from:
  • An image file (JPG, PNG, BMP, GIF, WebP, etc.)
  • Live webcam feed

Dependencies (install once):
    pip install opencv-python pyzbar pillow
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import webbrowser
import time

# ── Third-party imports with friendly error messages ──────────────────────────
try:
    import cv2
except ImportError:
    raise SystemExit("OpenCV is missing. Run:  pip install opencv-python")

try:
    from pyzbar import pyzbar
except ImportError:
    raise SystemExit("pyzbar is missing. Run:  pip install pyzbar")

try:
    from PIL import Image, ImageTk
except ImportError:
    raise SystemExit("Pillow is missing. Run:  pip install pillow")


# ─────────────────────────────────────────────────────────────────────────────
#  Colour palette & fonts
# ─────────────────────────────────────────────────────────────────────────────
BG        = "#0f0f14"
CARD      = "#1a1a24"
ACCENT    = "#00e5ff"
ACCENT2   = "#7c3aed"
SUCCESS   = "#22c55e"
WARNING   = "#f59e0b"
TEXT      = "#e2e8f0"
SUBTEXT   = "#64748b"
BORDER    = "#2d2d3d"
FONT_MONO = ("Courier New", 10)
FONT_MAIN = ("Segoe UI", 10)
FONT_HEAD = ("Segoe UI", 14, "bold")
FONT_BIG  = ("Segoe UI", 18, "bold")


# ─────────────────────────────────────────────────────────────────────────────
#  Helper: decode QR / barcodes from an OpenCV frame
# ─────────────────────────────────────────────────────────────────────────────
def decode_frame(frame):
    """Return list of decoded objects from an OpenCV BGR frame."""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return pyzbar.decode(rgb)


def draw_overlay(frame, decoded_objects):
    """Draw bounding boxes and labels on frame (in-place)."""
    for obj in decoded_objects:
        pts = obj.polygon
        if len(pts) == 4:
            import numpy as np
            pts_arr = np.array([[p.x, p.y] for p in pts], dtype=np.int32)
            cv2.polylines(frame, [pts_arr], True, (0, 229, 255), 2)
        data = obj.data.decode("utf-8", errors="replace")
        x, y, w, h = obj.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 229, 255), 2)
        cv2.putText(frame, data[:40], (x, y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 229, 255), 2)
    return frame


# ─────────────────────────────────────────────────────────────────────────────
#  Main application
# ─────────────────────────────────────────────────────────────────────────────
class QRScannerApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("QR Code Scanner")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(860, 620)

        # State
        self._cap          = None
        self._cam_running  = False
        self._cam_thread   = None
        self._results      = []          # list of (type, data) tuples
        self._last_seen    = {}          # data -> timestamp  (dedup)
        self._photo_ref    = None        # prevent GC of PhotoImage

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG, pady=18)
        hdr.pack(fill="x", padx=30)

        tk.Label(hdr, text="◈", font=("Segoe UI", 24), fg=ACCENT, bg=BG).pack(side="left")
        tk.Label(hdr, text="  QR Code Scanner", font=FONT_BIG,
                 fg=TEXT, bg=BG).pack(side="left")
        tk.Label(hdr, text="scan from image or live camera",
                 font=("Segoe UI", 10), fg=SUBTEXT, bg=BG).pack(side="left", padx=12)

        sep = tk.Frame(self, bg=BORDER, height=1)
        sep.pack(fill="x", padx=30)

        # ── Body (left preview + right results) ───────────────────────────
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=30, pady=20)

        # Left column – preview + controls
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)

        self._build_preview(left)
        self._build_controls(left)

        # Right column – results panel
        right = tk.Frame(body, bg=BG, width=300)
        right.pack(side="right", fill="y", padx=(20, 0))
        right.pack_propagate(False)
        self._build_results(right)

    def _card(self, parent, **kw):
        return tk.Frame(parent, bg=CARD,
                        highlightbackground=BORDER, highlightthickness=1, **kw)

    def _build_preview(self, parent):
        wrapper = self._card(parent)
        wrapper.pack(fill="both", expand=True)

        self._preview_label = tk.Label(
            wrapper, bg="#0a0a10",
            text="No source selected\n\nChoose 'Open Image' or 'Start Camera'",
            fg=SUBTEXT, font=FONT_MAIN, width=60, height=20,
            anchor="center"
        )
        self._preview_label.pack(fill="both", expand=True, padx=2, pady=2)

        # Status bar inside preview
        status_bar = tk.Frame(wrapper, bg="#12121a")
        status_bar.pack(fill="x")
        self._status_dot  = tk.Label(status_bar, text="●", fg=SUBTEXT,
                                     bg="#12121a", font=("Segoe UI", 8))
        self._status_dot.pack(side="left", padx=(8, 4), pady=4)
        self._status_text = tk.Label(status_bar, text="Idle", fg=SUBTEXT,
                                     bg="#12121a", font=("Segoe UI", 9))
        self._status_text.pack(side="left")

    def _build_controls(self, parent):
        ctrl = tk.Frame(parent, bg=BG)
        ctrl.pack(fill="x", pady=(12, 0))

        btn_cfg = dict(font=("Segoe UI", 10, "bold"), relief="flat",
                       cursor="hand2", pady=8, padx=16, bd=0)

        # Image button
        self._btn_image = tk.Button(
            ctrl, text="📂  Open Image", bg=ACCENT2, fg="white",
            activebackground="#6d28d9", activeforeground="white",
            command=self._open_image, **btn_cfg
        )
        self._btn_image.pack(side="left", padx=(0, 8))

        # Camera toggle
        self._btn_cam = tk.Button(
            ctrl, text="📷  Start Camera", bg=ACCENT, fg=BG,
            activebackground="#00bcd4", activeforeground=BG,
            command=self._toggle_camera, **btn_cfg
        )
        self._btn_cam.pack(side="left", padx=(0, 8))

        # Clear results
        tk.Button(
            ctrl, text="🗑  Clear", bg=CARD, fg=TEXT,
            activebackground=BORDER, activeforeground=TEXT,
            command=self._clear_results, **btn_cfg
        ).pack(side="right")

    def _build_results(self, parent):
        hdr = tk.Frame(parent, bg=BG)
        hdr.pack(fill="x", pady=(0, 8))
        tk.Label(hdr, text="Scan Results", font=FONT_HEAD,
                 fg=TEXT, bg=BG).pack(side="left")
        self._count_label = tk.Label(hdr, text="0 found", font=("Segoe UI", 9),
                                     fg=SUBTEXT, bg=BG)
        self._count_label.pack(side="right")

        results_card = self._card(parent)
        results_card.pack(fill="both", expand=True)

        # Scrollable results list
        canvas = tk.Canvas(results_card, bg=CARD, highlightthickness=0)
        sb = ttk.Scrollbar(results_card, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._results_inner = tk.Frame(canvas, bg=CARD)
        self._results_window = canvas.create_window(
            (0, 0), window=self._results_inner, anchor="nw"
        )

        def _on_resize(e):
            canvas.itemconfig(self._results_window, width=e.width)
        canvas.bind("<Configure>", _on_resize)

        self._results_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        # Mouse-wheel scrolling
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        self._results_canvas = canvas

        # Empty state
        self._empty_label = tk.Label(
            self._results_inner,
            text="No QR codes scanned yet.\n\nOpen an image or start the\ncamera to begin.",
            fg=SUBTEXT, bg=CARD, font=FONT_MAIN, pady=40
        )
        self._empty_label.pack(pady=20)

    # ── Status helpers ────────────────────────────────────────────────────────

    def _set_status(self, text, colour=SUBTEXT):
        self._status_dot.config(fg=colour)
        self._status_text.config(text=text, fg=colour)

    # ── Image scanning ────────────────────────────────────────────────────────

    def _open_image(self):
        path = filedialog.askopenfilename(
            title="Select an image with a QR code",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff *.tif"),
                ("All files", "*.*")
            ]
        )
        if not path:
            return

        # Stop camera if running
        if self._cam_running:
            self._stop_camera()

        self._set_status("Reading image…", WARNING)
        self.update_idletasks()

        frame = cv2.imread(path)
        if frame is None:
            messagebox.showerror("Error", f"Could not read image:\n{path}")
            self._set_status("Failed to load image", "red")
            return

        decoded = decode_frame(frame)
        annotated = draw_overlay(frame, decoded)

        # Show in preview
        img_rgb   = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        pil_img   = Image.fromarray(img_rgb)
        pil_img.thumbnail((560, 420))
        photo     = ImageTk.PhotoImage(pil_img)
        self._photo_ref = photo
        self._preview_label.config(image=photo, text="", width=0, height=0)

        if decoded:
            for obj in decoded:
                data = obj.data.decode("utf-8", errors="replace")
                self._add_result(obj.type, data)
            self._set_status(f"Found {len(decoded)} QR/barcode(s)", SUCCESS)
        else:
            self._set_status("No QR codes found in image", WARNING)
            messagebox.showinfo("Result", "No QR codes or barcodes were detected in that image.")

    # ── Camera scanning ───────────────────────────────────────────────────────

    def _toggle_camera(self):
        if self._cam_running:
            self._stop_camera()
        else:
            self._start_camera()

    def _start_camera(self):
        self._cap = cv2.VideoCapture(0)
        if not self._cap.isOpened():
            messagebox.showerror("Camera Error",
                                 "Could not open webcam.\n"
                                 "Make sure a camera is connected and not in use.")
            self._cap = None
            return

        self._cam_running = True
        self._btn_cam.config(text="⏹  Stop Camera", bg="#dc2626",
                             activebackground="#b91c1c")
        self._set_status("Camera active – point at a QR code", ACCENT)

        self._cam_thread = threading.Thread(target=self._camera_loop, daemon=True)
        self._cam_thread.start()

    def _stop_camera(self):
        self._cam_running = False
        if self._cap:
            self._cap.release()
            self._cap = None
        self._btn_cam.config(text="📷  Start Camera", bg=ACCENT,
                             activebackground="#00bcd4", fg=BG)
        self._preview_label.config(image="", text="Camera stopped.\n\nPress 'Start Camera' to resume.",
                                   fg=SUBTEXT, width=60, height=20)
        self._photo_ref = None
        self._set_status("Camera stopped", SUBTEXT)

    def _camera_loop(self):
        """Run in background thread; reads frames, decodes, updates UI."""
        while self._cam_running:
            ret, frame = self._cap.read()
            if not ret:
                self.after(0, lambda: messagebox.showerror(
                    "Camera Error", "Lost connection to camera."))
                break

            decoded = decode_frame(frame)
            annotated = draw_overlay(frame.copy(), decoded)

            # Convert for Tkinter (must happen on main thread via after)
            img_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)

            pw = self._preview_label.winfo_width()  or 560
            ph = self._preview_label.winfo_height() or 420
            pil_img.thumbnail((pw, ph))

            photo = ImageTk.PhotoImage(pil_img)

            # Schedule UI update on main thread
            self.after(0, self._update_camera_frame, photo, decoded)
            time.sleep(0.03)          # ~30 fps cap

    def _update_camera_frame(self, photo, decoded):
        if not self._cam_running:
            return
        self._photo_ref = photo
        self._preview_label.config(image=photo, text="", width=0, height=0)

        now = time.time()
        for obj in decoded:
            data = obj.data.decode("utf-8", errors="replace")
            if data in self._last_seen and now - self._last_seen[data] < 3:
                continue          # de-duplicate within 3 s
            self._last_seen[data] = now
            self._add_result(obj.type, data)

        if decoded:
            self._set_status(f"Detected {len(decoded)} code(s)", SUCCESS)
        else:
            self._set_status("Scanning… (no QR in frame)", ACCENT)

    # ── Result panel helpers ──────────────────────────────────────────────────

    def _add_result(self, qr_type, data):
        """Add a result card to the results panel."""
        self._results.append((qr_type, data))

        # Remove empty-state label
        if self._empty_label.winfo_ismapped():
            self._empty_label.pack_forget()

        is_url = data.lower().startswith(("http://", "https://", "ftp://"))

        card = tk.Frame(self._results_inner, bg="#12121f",
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", padx=8, pady=4)

        # Header row
        top = tk.Frame(card, bg="#12121f")
        top.pack(fill="x", padx=10, pady=(8, 2))

        type_badge = tk.Label(top, text=qr_type, font=("Segoe UI", 8, "bold"),
                              fg=BG, bg=ACCENT2, padx=6, pady=2)
        type_badge.pack(side="left")

        idx_label = tk.Label(top, text=f"#{len(self._results)}", font=("Segoe UI", 8),
                             fg=SUBTEXT, bg="#12121f")
        idx_label.pack(side="right")

        # Data text (scrollable if long)
        data_frame = tk.Frame(card, bg="#12121f")
        data_frame.pack(fill="x", padx=10, pady=4)

        txt = tk.Text(data_frame, bg="#0a0a10", fg=TEXT, font=FONT_MONO,
                      wrap="word", height=3, relief="flat", bd=0,
                      selectbackground=ACCENT2, selectforeground="white")
        txt.insert("1.0", data)
        txt.config(state="disabled")
        txt.pack(fill="x")

        # Action buttons
        btn_row = tk.Frame(card, bg="#12121f")
        btn_row.pack(fill="x", padx=10, pady=(2, 8))

        def _copy(d=data):
            self.clipboard_clear()
            self.clipboard_append(d)
            self._set_status("Copied to clipboard!", SUCCESS)

        tk.Button(btn_row, text="Copy", font=("Segoe UI", 8), relief="flat",
                  bg=BORDER, fg=TEXT, activebackground=ACCENT2,
                  activeforeground="white", cursor="hand2",
                  padx=8, pady=3, command=_copy).pack(side="left", padx=(0, 6))

        if is_url:
            def _open(d=data):
                webbrowser.open(d)
            tk.Button(btn_row, text="Open URL", font=("Segoe UI", 8), relief="flat",
                      bg=ACCENT, fg=BG, activebackground="#00bcd4",
                      activeforeground=BG, cursor="hand2",
                      padx=8, pady=3, command=_open).pack(side="left")

            url_icon = tk.Label(btn_row, text="🔗 URL detected",
                                font=("Segoe UI", 8), fg=SUCCESS, bg="#12121f")
            url_icon.pack(side="right")

        # Update count
        self._count_label.config(text=f"{len(self._results)} found")
        # Scroll to bottom
        self._results_canvas.after(50, lambda: self._results_canvas.yview_moveto(1.0))

    def _clear_results(self):
        for widget in self._results_inner.winfo_children():
            widget.destroy()
        self._results.clear()
        self._last_seen.clear()
        self._count_label.config(text="0 found")
        self._empty_label = tk.Label(
            self._results_inner,
            text="No QR codes scanned yet.\n\nOpen an image or start the\ncamera to begin.",
            fg=SUBTEXT, bg=CARD, font=FONT_MAIN, pady=40
        )
        self._empty_label.pack(pady=20)

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def _on_close(self):
        self._cam_running = False
        if self._cap:
            self._cap.release()
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QRScannerApp()
    app.mainloop()