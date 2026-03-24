"""
Crimson Desert Glide Patcher
Combined patch + uninstall GUI — single file, no dependencies beyond stdlib.
"""

import os
import shutil
import struct
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

# ── Constants ────────────────────────────────────────────────────────────────

PAZ_REL      = os.path.join("0008", "0.paz")
BACKUP_NAME  = "0.paz.glide_patcher_backup"

BASE_OFFSET  = 0x00CCDF9E
FAST_OFFSET  = 0x00CCBD2B

BASE_PREFIX  = bytes([0x00, 0x2b, 0x2c, 0x05, 0x50, 0xe4, 0x12, 0x22])
BASE_SUFFIX  = bytes([0x25, 0x0d, 0x0f, 0xe4, 0x12, 0x13])
FAST_PREFIX  = bytes([0x02, 0x00, 0x2c, 0x1d, 0xf5, 0x0a, 0x1d, 0x21])
FAST_SUFFIX  = bytes([0x6c, 0x4d, 0x0f, 0x50, 0xc8, 0x14])

DEFAULT_BASE = bytes([0x58, 0x9E])
DEFAULT_FAST = bytes([0xB0, 0x3C])

DEFAULT_NORMAL = Decimal("25")
DEFAULT_FAST_V = Decimal("50")

DEFAULT_GAME_DIRS = [
    r"D:\SteamLibrary\steamapps\common\Crimson Desert",
    r"C:\Program Files (x86)\Steam\steamapps\common\Crimson Desert",
    r"C:\Program Files\Steam\steamapps\common\Crimson Desert",
    r"E:\Program Files\Steam\steamapps\common\Crimson Desert",
]

# ── Core logic ────────────────────────────────────────────────────────────────

def find_default_game_dir():
    # 1. Check if running from inside the game folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(os.path.join(script_dir, PAZ_REL)):
        return script_dir

    # 2. Check known common paths
    for d in DEFAULT_GAME_DIRS:
        if os.path.exists(os.path.join(d, PAZ_REL)):
            return d

    # 3. Scan all available drives
    found = scan_all_drives()
    if found:
        return found

    return DEFAULT_GAME_DIRS[0]


def scan_all_drives() -> str:
    """Walk every drive letter looking for the Crimson Desert paz file."""
    import string
    game_subpath = os.path.join("Crimson Desert", PAZ_REL)
    # Common Steam library subfolder patterns to search under each drive
    search_roots = [
        "SteamLibrary\\steamapps\\common",
        "Steam\\steamapps\\common",
        "Program Files\\Steam\\steamapps\\common",
        "Program Files (x86)\\Steam\\steamapps\\common",
        "Games\\steamapps\\common",
        "Games",
    ]
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if not os.path.exists(drive):
            continue
        for root in search_roots:
            candidate = os.path.join(drive, root, "Crimson Desert")
            if os.path.exists(os.path.join(candidate, PAZ_REL)):
                return candidate
    return ""


def parse_cost(text: str, label: str) -> int:
    """Parse a stamina value and return the scaled int (value * 1000, rounded).
    0 is allowed and writes 0x0000 directly (infinite / free glide).
    """
    try:
        value = Decimal(text.strip())
    except InvalidOperation:
        raise ValueError(f"{label} is not a valid number: '{text}'")
    scaled = int((value * 1000).to_integral_value(rounding=ROUND_HALF_UP))
    if scaled <= 0:
        raise ValueError(f"{label} must be at least 0.001.")
    if scaled > 65535:
        raise ValueError(f"{label} must be between 0.001 and 65.535. Got {value}.")
    return scaled


def cost_to_bytes(scaled: int) -> bytes:
    """Return the two-byte little-endian two's-complement negation."""
    raw = (-scaled) & 0xFFFF
    return bytes([raw & 0xFF, (raw >> 8) & 0xFF])


def assert_context(blob: bytes, offset: int, prefix: bytes, suffix: bytes, label: str):
    if offset < len(prefix) or (offset + 2 + len(suffix)) > len(blob):
        raise ValueError(f"{label} patch offset is out of bounds for this archive.")
    actual_pre = blob[offset - len(prefix): offset]
    actual_suf = blob[offset + 2: offset + 2 + len(suffix)]
    if actual_pre != prefix:
        raise ValueError(f"{label} guard bytes do not match this game build.\n"
                         f"  Expected prefix: {prefix.hex(' ')}\n"
                         f"  Found:           {actual_pre.hex(' ')}")
    if actual_suf != suffix:
        raise ValueError(f"{label} guard bytes do not match this game build.\n"
                         f"  Expected suffix: {suffix.hex(' ')}\n"
                         f"  Found:           {actual_suf.hex(' ')}")


def write_bytes_at(path: str, offset: int, data: bytes):
    with open(path, "r+b") as f:
        f.seek(offset)
        f.write(data)


def read_bytes_at(path: str, offset: int, count: int) -> bytes:
    with open(path, "rb") as f:
        f.seek(offset)
        buf = f.read(count)
    if len(buf) != count:
        raise IOError("Could not read the expected number of bytes from the archive.")
    return buf


def do_patch(game_dir: str, normal_text: str, fast_text: str) -> str:
    paz_path    = os.path.join(game_dir, PAZ_REL)
    backup_path = os.path.join(os.path.dirname(paz_path), BACKUP_NAME)

    normal_scaled = parse_cost(normal_text, "Normal glide cost")
    fast_scaled   = parse_cost(fast_text,   "Fast glide cost")

    blob = open(paz_path, "rb").read()
    assert_context(blob, BASE_OFFSET, BASE_PREFIX, BASE_SUFFIX, "Normal glide")
    assert_context(blob, FAST_OFFSET, FAST_PREFIX, FAST_SUFFIX, "Fast glide")

    lines = []
    if not os.path.exists(backup_path):
        shutil.copy2(paz_path, backup_path)
        lines.append(f"Backup created:  {backup_path}")
    else:
        lines.append(f"Backup exists:   {backup_path}")

    normal_bytes = cost_to_bytes(normal_scaled)
    fast_bytes   = cost_to_bytes(fast_scaled)

    write_bytes_at(paz_path, BASE_OFFSET, normal_bytes)
    write_bytes_at(paz_path, FAST_OFFSET, fast_bytes)

    cur_base = read_bytes_at(paz_path, BASE_OFFSET, 2)
    cur_fast = read_bytes_at(paz_path, FAST_OFFSET, 2)

    lines += [
        f"Patched:         {paz_path}",
        f"Normal glide:    {normal_text}  →  {cur_base.hex(' ').upper()}",
        f"Fast glide:      {fast_text}  →  {cur_fast.hex(' ').upper()}",
        "Scope: shared glide/flight roots for Damian, CrowWing, and RocketPack.",
        "",
        f"Bytes now:  normal={cur_base.hex(' ').upper()}  fast={cur_fast.hex(' ').upper()}",
    ]
    return "\n".join(lines)


def do_uninstall(game_dir: str) -> str:
    paz_path    = os.path.join(game_dir, PAZ_REL)
    backup_path = os.path.join(os.path.dirname(paz_path), BACKUP_NAME)

    lines = []
    if os.path.exists(backup_path):
        shutil.copy2(backup_path, paz_path)
        lines.append(f"Restored backup: {backup_path}")
    else:
        blob = open(paz_path, "rb").read()
        assert_context(blob, BASE_OFFSET, BASE_PREFIX, BASE_SUFFIX, "Normal glide")
        assert_context(blob, FAST_OFFSET, FAST_PREFIX, FAST_SUFFIX, "Fast glide")
        write_bytes_at(paz_path, BASE_OFFSET, DEFAULT_BASE)
        write_bytes_at(paz_path, FAST_OFFSET, DEFAULT_FAST)
        lines.append("Backup not found — restored default glide values directly.")

    cur_base = read_bytes_at(paz_path, BASE_OFFSET, 2)
    cur_fast = read_bytes_at(paz_path, FAST_OFFSET, 2)
    lines += [
        "",
        f"Bytes now:  normal={cur_base.hex(' ').upper()}  fast={cur_fast.hex(' ').upper()}",
    ]
    return "\n".join(lines)


# ── GUI ───────────────────────────────────────────────────────────────────────

DARK_BG    = "#1a1a2e"
PANEL_BG   = "#16213e"
ACCENT     = "#e94560"
ACCENT2    = "#0f3460"
TEXT_FG    = "#eaeaea"
MUTED      = "#888888"
INPUT_BG   = "#0d1b2a"
SUCCESS_FG = "#4caf50"
ERROR_FG   = "#f44336"
WARN_FG    = "#ff9800"
FONT_BODY  = ("Segoe UI", 10)
FONT_BOLD  = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 14, "bold")
FONT_MONO  = ("Consolas", 9)


class GlidePatcherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()  # hide until fully positioned
        self.title("CrimsonWings")
        self.resizable(False, False)
        self.configure(bg=DARK_BG)
        self._set_icon()
        self._build_ui()
        self.game_dir_var.set(find_default_game_dir())
        self._center()
        self.deiconify()  # show in final position

    def _set_icon(self):
        # Resolve icon path whether running as a script or a PyInstaller bundle
        if getattr(sys, 'frozen', False):
            base = sys._MEIPASS
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        ico = os.path.join(base, 'icon.ico')
        if os.path.exists(ico):
            try:
                self.iconbitmap(ico)
            except Exception:
                pass  # Non-Windows fallback — silently skip

    # ── Layout ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        pad = {"padx": 16, "pady": 6}

        # ── Title bar ──
        title_frame = tk.Frame(self, bg=ACCENT2, padx=16, pady=10)
        title_frame.pack(fill="x")
        tk.Label(title_frame, text="CrimsonWings",
                 font=FONT_TITLE, fg=ACCENT, bg=ACCENT2).pack(side="left")
        tk.Label(title_frame, text="by DatGuySnowfox", font=FONT_BODY, fg=MUTED, bg=ACCENT2).pack(side="right", anchor="s")

        # ── Game folder ──
        folder_frame = tk.LabelFrame(self, text=" Game Folder ", font=FONT_BOLD,
                                     fg=TEXT_FG, bg=DARK_BG, bd=1, relief="groove",
                                     padx=12, pady=8)
        folder_frame.pack(fill="x", padx=16, pady=(12, 4))

        self.game_dir_var = tk.StringVar()
        dir_row = tk.Frame(folder_frame, bg=DARK_BG)
        dir_row.pack(fill="x")
        dir_entry = tk.Entry(dir_row, textvariable=self.game_dir_var,
                             bg=INPUT_BG, fg=TEXT_FG, insertbackground=TEXT_FG,
                             relief="flat", font=FONT_BODY, width=52)
        dir_entry.pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(dir_row, text="Browse…", command=self._browse,
                  bg=ACCENT2, fg=TEXT_FG, activebackground=ACCENT,
                  relief="flat", font=FONT_BODY, cursor="hand2",
                  padx=8).pack(side="left", padx=(6, 0))
        self.scan_btn = tk.Button(dir_row, text="Scan Drives", command=self._scan_drives,
                  bg=PANEL_BG, fg=TEXT_FG, activebackground=ACCENT2,
                  relief="flat", font=FONT_BODY, cursor="hand2",
                  padx=8)
        self.scan_btn.pack(side="left", padx=(4, 0))

        self.dir_status_lbl = tk.Label(folder_frame, text="", font=FONT_BODY,
                                       bg=DARK_BG, fg=MUTED)
        self.dir_status_lbl.pack(anchor="w", pady=(4, 0))
        self.game_dir_var.trace_add("write", lambda *_: self._validate_dir())

        # ── Tabs ──
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("TNotebook",        background=DARK_BG, borderwidth=0)
        style.configure("TNotebook.Tab",    background=ACCENT2, foreground=TEXT_FG,
                        font=FONT_BOLD, padding=[12, 6])
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#ffffff")])

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=16, pady=8)

        self._build_patch_tab(nb)
        self._build_uninstall_tab(nb)

        # ── Log ──
        log_frame = tk.LabelFrame(self, text=" Log ", font=FONT_BOLD,
                                  fg=TEXT_FG, bg=DARK_BG, bd=1, relief="groove",
                                  padx=8, pady=6)
        log_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self.log_text = tk.Text(log_frame, height=7, bg=INPUT_BG, fg=TEXT_FG,
                                font=FONT_MONO, relief="flat", state="disabled",
                                wrap="word", padx=6, pady=4)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.tag_config("ok",   foreground=SUCCESS_FG)
        self.log_text.tag_config("err",  foreground=ERROR_FG)
        self.log_text.tag_config("warn", foreground=WARN_FG)
        self.log_text.tag_config("info", foreground=TEXT_FG)

        tk.Button(log_frame, text="Clear log", command=self._clear_log,
                  bg=PANEL_BG, fg=MUTED, activebackground=ACCENT2,
                  relief="flat", font=("Segoe UI", 8), cursor="hand2"
                  ).pack(anchor="e", pady=(4, 0))

    def _build_patch_tab(self, nb):
        tab = tk.Frame(nb, bg=DARK_BG, padx=16, pady=12)
        nb.add(tab, text="  Patch  ")

        info = ("Modifies the stamina cost for gliding.\n"
                "Defaults: Normal = 25 · Fast = 50\n"
                "Range: 0.001 – 65.535")
        tk.Label(tab, text=info, font=FONT_BODY, fg=MUTED, bg=DARK_BG,
                 justify="left").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        def labeled_entry(row, label, default, var_name):
            tk.Label(tab, text=label, font=FONT_BOLD, fg=TEXT_FG, bg=DARK_BG,
                     width=22, anchor="w").grid(row=row, column=0, sticky="w")
            var = tk.StringVar(value=str(default))
            setattr(self, var_name, var)
            e = tk.Entry(tab, textvariable=var, bg=INPUT_BG, fg=TEXT_FG,
                         insertbackground=TEXT_FG, relief="flat", font=FONT_BODY,
                         width=14, justify="center")
            e.grid(row=row, column=1, sticky="w", ipady=4, padx=(4, 0))
            reset_val = str(default)
            tk.Button(tab, text="Reset", command=lambda v=var, d=reset_val: v.set(d),
                      bg=PANEL_BG, fg=MUTED, activebackground=ACCENT2,
                      relief="flat", font=("Segoe UI", 8), cursor="hand2",
                      padx=6).grid(row=row, column=2, padx=(6, 0))

        labeled_entry(1, "Normal glide cost:", DEFAULT_NORMAL, "normal_var")
        labeled_entry(2, "Fast glide cost:",   DEFAULT_FAST_V, "fast_var")

        tk.Button(tab, text="Apply Patch", command=self._on_patch,
                  bg=ACCENT, fg="#ffffff", activebackground="#c73652",
                  relief="flat", font=FONT_BOLD, cursor="hand2",
                  padx=20, pady=8).grid(row=3, column=0, columnspan=3,
                                        pady=(16, 0), sticky="w")

    def _build_uninstall_tab(self, nb):
        tab = tk.Frame(nb, bg=DARK_BG, padx=16, pady=12)
        nb.add(tab, text="  Uninstall  ")

        info = ("Restores the original glide values.\n\n"
                "• If a backup file exists, it will be restored directly.\n"
                "• Otherwise, the default byte values are written back.\n\n"
                "Default values: Normal = 25  ·  Fast = 50")
        tk.Label(tab, text=info, font=FONT_BODY, fg=MUTED, bg=DARK_BG,
                 justify="left").pack(anchor="w", pady=(0, 16))

        # Show backup status
        self.backup_status_lbl = tk.Label(tab, text="", font=FONT_BODY,
                                          bg=DARK_BG, fg=MUTED)
        self.backup_status_lbl.pack(anchor="w", pady=(0, 8))
        self.game_dir_var.trace_add("write", lambda *_: self._update_backup_status())

        tk.Button(tab, text="Uninstall / Restore Defaults", command=self._on_uninstall,
                  bg=ACCENT2, fg=TEXT_FG, activebackground=ACCENT,
                  relief="flat", font=FONT_BOLD, cursor="hand2",
                  padx=20, pady=8).pack(anchor="w")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _center(self):
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _scan_drives(self):
        self.scan_btn.config(text="Scanning…", state="disabled")
        self.update_idletasks()
        found = scan_all_drives()
        self.scan_btn.config(text="Scan Drives", state="normal")
        if found:
            self.game_dir_var.set(found)
            self._log(f"Scan found: {found}", "ok")
        else:
            self._log("Scan complete — Crimson Desert not found on any drive.", "warn")
            messagebox.showwarning("Not found",
                "Crimson Desert was not found on any drive.\n"
                "Use Browse to locate it manually.")

    def _browse(self):
        d = filedialog.askdirectory(title="Select Crimson Desert game folder",
                                    initialdir=self.game_dir_var.get())
        if d:
            self.game_dir_var.set(d)

    def _paz_path(self):
        return os.path.join(self.game_dir_var.get(), PAZ_REL)

    def _validate_dir(self):
        paz = self._paz_path()
        if os.path.exists(paz):
            self.dir_status_lbl.config(text=f"✔  Found: {paz}", fg=SUCCESS_FG)
        else:
            self.dir_status_lbl.config(text=f"✘  Not found: {paz}", fg=ERROR_FG)
        self._update_backup_status()

    def _update_backup_status(self):
        paz  = self._paz_path()
        bkup = os.path.join(os.path.dirname(paz), BACKUP_NAME)
        if os.path.exists(bkup):
            self.backup_status_lbl.config(text=f"Backup found: {bkup}", fg=SUCCESS_FG)
        elif os.path.exists(paz):
            self.backup_status_lbl.config(text="No backup found — defaults will be written directly.", fg=WARN_FG)
        else:
            self.backup_status_lbl.config(text="", fg=MUTED)

    def _log(self, msg: str, tag="info"):
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n", tag)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    def _check_paz(self) -> bool:
        if not os.path.exists(self._paz_path()):
            messagebox.showerror("File not found",
                                 f"Could not find:\n{self._paz_path()}\n\n"
                                 "Make sure the path points to your Crimson Desert folder.")
            return False
        return True

    # ── Actions ──────────────────────────────────────────────────────────────

    def _on_patch(self):
        if not self._check_paz():
            return
        try:
            result = do_patch(self.game_dir_var.get(),
                              self.normal_var.get(),
                              self.fast_var.get())
            self._log("── Patch ──────────────────────────────────────", "info")
            self._log(result, "ok")
            messagebox.showinfo("Patch complete", "Glide values patched successfully.")
        except Exception as e:
            self._log("── Patch FAILED ───────────────────────────────", "info")
            self._log(str(e), "err")
            messagebox.showerror("Patch failed", str(e))
        self._update_backup_status()

    def _on_uninstall(self):
        if not self._check_paz():
            return
        if not messagebox.askyesno("Confirm uninstall",
                                   "Restore original glide values?\n\n"
                                   "If a backup exists it will be used;\n"
                                   "otherwise defaults are written directly."):
            return
        try:
            result = do_uninstall(self.game_dir_var.get())
            self._log("── Uninstall ──────────────────────────────────", "info")
            self._log(result, "ok")
            messagebox.showinfo("Uninstall complete", "Glide values restored successfully.")
        except Exception as e:
            self._log("── Uninstall FAILED ───────────────────────────", "info")
            self._log(str(e), "err")
            messagebox.showerror("Uninstall failed", str(e))
        self._update_backup_status()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = GlidePatcherApp()
    app.mainloop()
