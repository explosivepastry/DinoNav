import tkinter as tk
import threading
import time
import sys
import ctypes
import webbrowser

try:
    from PIL import Image, ImageTk, ImageDraw
except ImportError:
    print("pillow isn't installed, run: pip install pillow")
    sys.exit(1)

try:
    import win32gui
    import win32ui
    import win32con
    import win32api
except ImportError:
    print("pywin32 isn't installed, run: pip install pywin32")
    sys.exit(1)

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    print("keyboard not installed, hotkeys disabled. run: pip install keyboard")
    KEYBOARD_AVAILABLE = False


DARK_BG   = "#0d0f0d"
PANEL_BG  = "#111411"
BORDER    = "#2a3d2a"
ACCENT    = "#4a7c59"
ACCENT_LT = "#6aaf7e"
TEXT_PRI  = "#c8d8c0"
TEXT_SEC  = "#5a7a5a"
TEXT_DIM  = "#3a4a3a"
BTN_HOVER = "#1e2e1e"

SERVERS = {
    "EU": "https://eu.dinoden.gg/map",
    "NA": "https://na.dinoden.gg/map",
}

CONFIG = {
    "refresh_interval": 3,
    "overlay_size":     340,
    "overlay_opacity":  0.92,
    "overlay_pos":      (20, 20),
    "browser_keywords": ["dinoden", "dino den"],
    "crop_left":        0.155,
    "crop_right":       0.145,
    "crop_top":         0.060,
    "crop_bottom":      0.020,
    "crop_step":        0.010,
    "corner_r":         12,
    "min_size":         180,
    "max_size":         700,
    "size_step":        50,
}


def find_browser_hwnd():
    found = []
    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        if any(k in win32gui.GetWindowText(hwnd).lower() for k in CONFIG["browser_keywords"]):
            found.append(hwnd)
    win32gui.EnumWindows(cb, None)
    return found[0] if found else None


def capture_printwindow(hwnd):
    try:
        x, y, x2, y2 = win32gui.GetWindowRect(hwnd)
        w, h = x2 - x, y2 - y
        if w <= 0 or h <= 0:
            return None
        hdc = win32gui.GetWindowDC(hwnd)
        mdc = win32ui.CreateDCFromHandle(hdc)
        sdc = mdc.CreateCompatibleDC()
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(mdc, w, h)
        sdc.SelectObject(bmp)
        if not ctypes.windll.user32.PrintWindow(hwnd, sdc.GetSafeHdc(), 2):
            ctypes.windll.user32.PrintWindow(hwnd, sdc.GetSafeHdc(), 0)
        info = bmp.GetInfo()
        raw  = bmp.GetBitmapBits(True)
        img  = Image.frombuffer("RGB", (info["bmWidth"], info["bmHeight"]),
                                raw, "raw", "BGRX", 0, 1)
        win32gui.DeleteObject(bmp.GetHandle())
        sdc.DeleteDC(); mdc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hdc)
        return img
    except Exception as e:
        print(f"capture failed: {e}")
        return None


def move_window_offscreen(hwnd):
    try:
        sw = win32api.GetSystemMetrics(0)
        x, y, x2, y2 = win32gui.GetWindowRect(hwnd)
        win32gui.MoveWindow(hwnd, sw + 10, 0, x2 - x, y2 - y, True)
        return True
    except Exception as e:
        print(f"couldn't move browser: {e}")
        return False


def restore_window(hwnd):
    try:
        win32gui.MoveWindow(hwnd, 100, 100, 1280, 800, True)
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass


def crop_to_map(img):
    w, h = img.size
    l = int(w * CONFIG["crop_left"])
    r = int(w * CONFIG["crop_right"])
    t = int(h * CONFIG["crop_top"])
    b = int(h * CONFIG["crop_bottom"])
    img = img.crop((l, t, w - r, h - b))
    cw, ch = img.size
    if cw > ch:
        d = (cw - ch) // 2
        img = img.crop((d, 0, d + ch, ch))
    elif ch > cw:
        d = (ch - cw) // 2
        img = img.crop((0, d, cw, d + cw))
    return img


def round_image(img, r):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, *img.size], radius=r, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def finish_image(img, server_key, ok):
    bw = 1
    nw, nh = img.width + bw*2, img.height + bw*2
    out = Image.new("RGBA", (nw, nh), (0,0,0,0))
    ImageDraw.Draw(out).rounded_rectangle(
        [0, 0, nw-1, nh-1], radius=CONFIG["corner_r"]+bw, fill=(42, 61, 42, 180))
    out.paste(img, (bw, bw), img)
    d = ImageDraw.Draw(out)
    d.rectangle([0, 0, 32, 16], fill=(74, 124, 89, 220))
    try:
        from PIL import ImageFont
        fnt = ImageFont.truetype("cour.ttf", 9)
    except Exception:
        fnt = None
    d.text((4, 3), server_key, fill=(13, 15, 13, 255), font=fnt)
    dot = (58, 122, 74, 255) if ok else (139, 48, 48, 255)
    d.ellipse([out.width-14, 4, out.width-4, 14], fill=dot)
    return out


class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DinoNav")
        self.resizable(False, False)
        self.configure(bg=DARK_BG)
        self.selected_server = tk.StringVar(value="EU")
        self._build()
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw-self.winfo_width())//2}+{(sh-self.winfo_height())//2}")

    def _build(self):
        bar = tk.Frame(self, bg=PANEL_BG, height=36)
        bar.pack(fill="x")
        tk.Label(bar, text="DinoNav", bg=PANEL_BG, fg=ACCENT_LT,
                 font=("Courier New", 11, "bold")).pack(side="left", padx=14, pady=8)
        tk.Label(bar, text="v1.0", bg=PANEL_BG, fg=TEXT_DIM,
                 font=("Courier New", 8)).pack(side="right", padx=14, pady=10)
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        body = tk.Frame(self, bg=DARK_BG, padx=24, pady=20)
        body.pack(fill="both")

        tk.Label(body, text="SELECT SERVER", bg=DARK_BG, fg=TEXT_SEC,
                 font=("Courier New", 8, "bold")).pack(anchor="w", pady=(0,8))
        row = tk.Frame(body, bg=DARK_BG)
        row.pack(fill="x", pady=(0,20))
        self.eu_btn = self._srv_btn(row, "EU", "eu.dinoden.gg")
        self.eu_btn.pack(side="left", fill="x", expand=True, padx=(0,6))
        self.na_btn = self._srv_btn(row, "NA", "na.dinoden.gg")
        self.na_btn.pack(side="left", fill="x", expand=True)
        self._update_srv_btns()

        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(0,16))

        info = tk.Frame(body, bg=PANEL_BG, padx=12, pady=10)
        info.pack(fill="x", pady=(0,20))
        for s in [
            "1. Open the map in Chrome or Edge and log in",
            "2. Click 'Open Map in Browser' or do it yourself",
            "3. Click 'Hide Browser' to move it off-screen",
            "4. Launch The Isle in Borderless Windowed",
            "5. Use Ctrl+]/[ to nudge crop if needed",
        ]:
            tk.Label(info, text=s, bg=PANEL_BG, fg=TEXT_SEC,
                     font=("Courier New", 8), anchor="w").pack(fill="x", pady=1)

        self._btn(body, "OPEN MAP IN BROWSER", self.open_browser).pack(fill="x", pady=(0,8))
        self._btn(body, "HIDE BROWSER  (move off-screen)", self.hide_browser,
                  fg=TEXT_SEC).pack(fill="x", pady=(0,8))

        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(0,16))

        self._btn(body, "▶  LAUNCH DINONAV", self.launch,
                  bg=ACCENT, fg=DARK_BG, font=("Courier New", 10, "bold")).pack(fill="x")

        self.status_var = tk.StringVar(value="")
        tk.Label(body, textvariable=self.status_var, bg=DARK_BG, fg=TEXT_DIM,
                 font=("Courier New", 8), wraplength=280).pack(pady=(10,0))

    def _srv_btn(self, parent, key, label):
        f = tk.Frame(parent, bg=PANEL_BG, cursor="hand2")
        tk.Label(f, text=key, bg=PANEL_BG, fg=TEXT_PRI,
                 font=("Courier New", 13, "bold")).pack(pady=(10,2))
        tk.Label(f, text=label, bg=PANEL_BG, fg=TEXT_SEC,
                 font=("Courier New", 7)).pack(pady=(0,10))
        f.bind("<Button-1>", lambda e, k=key: self._select_srv(k))
        for w in f.winfo_children():
            w.bind("<Button-1>", lambda e, k=key: self._select_srv(k))
        return f

    def _select_srv(self, key):
        self.selected_server.set(key)
        self._update_srv_btns()

    def _update_srv_btns(self):
        sel = self.selected_server.get()
        for key, btn in [("EU", self.eu_btn), ("NA", self.na_btn)]:
            col = ACCENT if key == sel else PANEL_BG
            btn.configure(bg=col)
            for w in btn.winfo_children():
                w.configure(bg=col)

    def _btn(self, parent, text, cmd, bg=PANEL_BG, fg=ACCENT_LT,
             font=("Courier New", 9)):
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                      activebackground=BTN_HOVER, activeforeground=fg,
                      relief="flat", bd=0, font=font, cursor="hand2", pady=8)
        b.bind("<Enter>", lambda e: b.configure(bg=BTN_HOVER if bg == PANEL_BG else bg))
        b.bind("<Leave>", lambda e: b.configure(bg=bg))
        return b

    def open_browser(self):
        webbrowser.open(SERVERS[self.selected_server.get()])
        self.status_var.set("browser opened — log in and then click Hide Browser")

    def hide_browser(self):
        hwnd = find_browser_hwnd()
        if hwnd:
            move_window_offscreen(hwnd)
            self.status_var.set("browser moved off-screen, it's still running")
        else:
            self.status_var.set("couldn't find the browser — open the map first")

    def launch(self):
        self.destroy()
        Overlay(self.selected_server.get()).run()


class Overlay:
    def __init__(self, server_key):
        self.server_key  = server_key
        self.size        = CONFIG["overlay_size"]
        self.visible     = True
        self.running     = True
        self.status      = "connecting..."
        self.status_ok   = False
        self.last_time   = 0
        self.pending_img = None
        self.drag_start  = None
        self.drag_origin = (0, 0)

        self.root = tk.Tk()
        self.root.title("DinoNav")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", CONFIG["overlay_opacity"])
        self.root.configure(bg=DARK_BG)
        self.root.wm_attributes("-transparentcolor", DARK_BG)
        x, y = CONFIG["overlay_pos"]
        self.root.geometry(f"+{x}+{y}")

        self.canvas = tk.Canvas(self.root, width=self.size, height=self.size,
                                bg=DARK_BG, highlightthickness=0, cursor="fleur")
        self.canvas.pack()

        self.canvas.bind("<ButtonPress-1>",   self._drag_start)
        self.canvas.bind("<B1-Motion>",       self._drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._drag_end)
        self.canvas.bind("<Button-3>",        self._menu)

        if KEYBOARD_AVAILABLE:
            keyboard.add_hotkey("ctrl+m",    self.toggle)
            keyboard.add_hotkey("ctrl+r",    self.force_refresh)
            keyboard.add_hotkey("ctrl+up",   self.size_up)
            keyboard.add_hotkey("ctrl+down", self.size_down)
            keyboard.add_hotkey("ctrl+q",    self.quit)
            keyboard.add_hotkey("ctrl+]",    self.crop_left_more)
            keyboard.add_hotkey("ctrl+[",    self.crop_left_less)
            keyboard.add_hotkey("ctrl+p",    self.crop_top_more)
            keyboard.add_hotkey("ctrl+;",    self.crop_top_less)

        self._set_ct(True)
        self._draw_placeholder()
        threading.Thread(target=self._loop, daemon=True).start()
        self.root.after(200, self._tick)

    def _drag_start(self, e):
        self._set_ct(False)
        self.drag_start = (e.x_root, e.y_root)
        geo = self.root.geometry()
        _, pos = geo.split("+", 1)
        px, py = pos.split("+")
        self.drag_origin = (int(px), int(py))

    def _drag_move(self, e):
        if self.drag_start:
            dx = e.x_root - self.drag_start[0]
            dy = e.y_root - self.drag_start[1]
            self.root.geometry(f"+{self.drag_origin[0]+dx}+{self.drag_origin[1]+dy}")

    def _drag_end(self, e):
        self.drag_start = None
        self._set_ct(True)

    def _set_ct(self, on):
        try:
            hwnd = win32gui.FindWindow(None, "DinoNav")
            if not hwnd:
                return
            s = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            s = (s | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED) if on \
                else (s & ~win32con.WS_EX_TRANSPARENT)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, s)
        except Exception:
            pass

    def _menu(self, e):
        self._set_ct(False)
        m = tk.Menu(self.root, tearoff=0, bg=PANEL_BG, fg=TEXT_PRI,
                    activebackground=ACCENT, activeforeground=DARK_BG, bd=0, relief="flat")
        m.add_command(label=f"  {self.server_key}  •  {self.status}", state="disabled")
        m.add_command(label=f"  left crop: {CONFIG['crop_left']:.3f}   top crop: {CONFIG['crop_top']:.3f}", state="disabled")
        m.add_separator()
        m.add_command(label="  Toggle visibility      Ctrl+M",  command=self.toggle)
        m.add_command(label="  Size up                Ctrl+↑",  command=self.size_up)
        m.add_command(label="  Size down              Ctrl+↓",  command=self.size_down)
        m.add_command(label="  Crop left +            Ctrl+]",  command=self.crop_left_more)
        m.add_command(label="  Crop left -            Ctrl+[",  command=self.crop_left_less)
        m.add_command(label="  Crop top +             Ctrl+P",  command=self.crop_top_more)
        m.add_command(label="  Crop top -             Ctrl+;",  command=self.crop_top_less)
        m.add_command(label="  Force refresh          Ctrl+R",  command=self.force_refresh)
        m.add_separator()
        m.add_command(label="  Bring browser back",             command=self._restore)
        m.add_separator()
        m.add_command(label="  Quit                   Ctrl+Q",  command=self.quit)
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()
            self.root.after(500, lambda: self._set_ct(True))

    def toggle(self):
        self.visible = not self.visible
        self.root.attributes("-alpha", CONFIG["overlay_opacity"] if self.visible else 0.0)

    def force_refresh(self): self.last_time = 0

    def size_up(self):
        self.size = min(self.size + CONFIG["size_step"], CONFIG["max_size"])
        self.canvas.config(width=self.size, height=self.size)
        self.force_refresh()

    def size_down(self):
        self.size = max(self.size - CONFIG["size_step"], CONFIG["min_size"])
        self.canvas.config(width=self.size, height=self.size)
        self.force_refresh()

    def crop_left_more(self):
        CONFIG["crop_left"] = round(min(CONFIG["crop_left"] + CONFIG["crop_step"], 0.5), 3)
        self.force_refresh()

    def crop_left_less(self):
        CONFIG["crop_left"] = round(max(CONFIG["crop_left"] - CONFIG["crop_step"], 0.0), 3)
        self.force_refresh()

    def crop_top_more(self):
        CONFIG["crop_top"] = round(min(CONFIG["crop_top"] + CONFIG["crop_step"], 0.5), 3)
        self.force_refresh()

    def crop_top_less(self):
        CONFIG["crop_top"] = round(max(CONFIG["crop_top"] - CONFIG["crop_step"], 0.0), 3)
        self.force_refresh()

    def _restore(self):
        hwnd = find_browser_hwnd()
        if hwnd: restore_window(hwnd)

    def quit(self):
        self.running = False
        if KEYBOARD_AVAILABLE: keyboard.unhook_all()
        self.root.quit()

    def _draw_placeholder(self, msg=None):
        self.canvas.delete("all")
        s = self.size
        self.canvas.create_rectangle(0, 0, s, s, fill=PANEL_BG, outline="")
        self.canvas.create_rectangle(1, 1, s-1, s-1, fill="", outline=BORDER, width=1)
        self.canvas.create_rectangle(0, 0, 36, 18, fill=ACCENT, outline="")
        self.canvas.create_text(18, 9, text=self.server_key, fill=DARK_BG,
                                font=("Courier New", 7, "bold"))
        cx, cy = s//2, s//2
        self.canvas.create_text(cx, cy-14, text="DinoNav", fill=ACCENT_LT,
                                font=("Courier New", 10, "bold"))
        self.canvas.create_text(cx, cy+8, text=msg or self.status, fill=TEXT_SEC,
                                font=("Courier New", 8), width=s-30)
        self.canvas.create_text(cx, s-18, text="right-click for options",
                                fill=TEXT_DIM, font=("Courier New", 7))

    def _loop(self):
        while self.running:
            if time.time() - self.last_time >= CONFIG["refresh_interval"]:
                self._capture()
                self.last_time = time.time()
            time.sleep(0.5)

    def _capture(self):
        try:
            hwnd = find_browser_hwnd()
            if not hwnd:
                self.status = "browser not found\nopen the map url"
                self.status_ok = False
                self.pending_img = None
                return

            raw = capture_printwindow(hwnd)
            if raw is None:
                self.status = "capture failed\ntry Chrome or Edge"
                self.status_ok = False
                self.pending_img = None
                return

            img = crop_to_map(raw)
            img = img.resize((self.size - 4, self.size - 4), Image.LANCZOS)
            img = round_image(img, CONFIG["corner_r"])
            img = finish_image(img, self.server_key, True)

            self.status_ok   = True
            self.status      = "live"
            self.pending_img = img

        except Exception as e:
            self.status    = f"error: {e}"
            self.status_ok = False
            self.pending_img = None
            print(f"capture error: {e}")

    def _tick(self):
        if self.pending_img is not None:
            img = self.pending_img
            self.pending_img = None
            self._photo = ImageTk.PhotoImage(img)
            self.canvas.config(width=img.width, height=img.height)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=self._photo)
        elif not self.status_ok:
            self._draw_placeholder()
        self.root.after(500, self._tick)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = Launcher()
    app.mainloop()
