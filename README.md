# DinoNav

A lightweight minimap overlay for **The Isle: Evrima** that captures the live [Dino Den](https://eu.dinoden.gg) map and displays it on top of your game in real time.

![Python](https://img.shields.io/badge/python-3.8%2B-blue) ![Platform](https://img.shields.io/badge/platform-Windows-lightgrey) ![License](https://img.shields.io/badge/license-MIT-green)

---

## How it works

DinoNav uses the Windows `PrintWindow` API to capture your browser window directly from its render buffer — meaning it keeps working even when the browser is completely hidden behind your game. No screen recording, no game memory access, no anti-cheat risk.

---

## Requirements

- Windows
- Python 3.8+
- Chrome or Edge (Firefox may not work)
- A [Dino Den](https://eu.dinoden.gg) account

Install dependencies:

```
pip install pillow pywin32 keyboard
```

---

## Setup

1. Open `eu.dinoden.gg/map` or `na.dinoden.gg/map` in Chrome or Edge and log in
2. Run DinoNav and select your server (EU or NA)
3. Click **Hide Browser** — this moves the browser off-screen so it doesn't cover your game, but keeps it rendering in the background
4. Click **Launch DinoNav**
5. Switch The Isle to **Borderless Windowed** mode
6. The minimap will appear in the top-left corner of your screen

---

## Hotkeys

| Hotkey | Action |
|--------|--------|
| `Ctrl+M` | Toggle minimap on/off |
| `Ctrl+↑` | Make minimap bigger |
| `Ctrl+↓` | Make minimap smaller |
| `Ctrl+R` | Force refresh now |
| `Ctrl+]` | Shift map view left |
| `Ctrl+[` | Shift map view right |
| `Ctrl+P` | Shift map view up |
| `Ctrl+;` | Shift map view down |
| `Ctrl+Q` | Quit |

You can also **drag** the minimap anywhere on screen by clicking and dragging it, and **right-click** it for a context menu with all options.

---

## Adjusting the crop

DinoNav captures the full browser window and crops out the Dino Den sidebar and panels automatically. If the crop isn't quite right for your screen resolution or browser zoom level, use the hotkeys above to nudge it until the map looks clean. The current crop values are shown in the right-click menu.

---

## Notes

- The browser must stay open (even off-screen) for the minimap to update
- If DinoNav can't find your browser, make sure the Dino Den map tab is open and the window title contains "dinoden"
- Right-click the minimap and choose **Bring browser back** if you need to interact with it
- Refresh rate is every 3 seconds by default — you can change `refresh_interval` in the `CONFIG` dict at the top of the script

---

## Disclaimer

DinoNav only reads your browser window. It does not interact with, read from, or write to The Isle game process in any way. It is not affiliated with Afterthought LLC or The Dino Den.
