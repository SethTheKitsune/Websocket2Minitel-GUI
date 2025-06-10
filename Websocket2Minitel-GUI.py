import tkinter as tk
from tkinter import messagebox, scrolledtext
import asyncio
import websockets
import serial
import threading
import json
import os
import time
from datetime import datetime

ser = None
ws = None
loop = None
connected = False
favorites_file = "favorites.json"
tasks = []

def log(text):
    timestamp = datetime.now().strftime("[%H:%M:%S]")
    logbox.config(state='normal')
    logbox.insert(tk.END, f"{timestamp} {text}\n")
    logbox.see(tk.END)
    logbox.config(state='disabled')

def safe_close():
    global ser
    try:
        if ser and ser.is_open:
            ser.flush()
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            ser.close()
            del ser
    except Exception as e:
        log(f"Force close failed: {e}")  


async def bridge(url, tty, speed):
    global ser, ws, connected
    ser = serial.Serial(tty, int(speed), parity=serial.PARITY_EVEN, bytesize=7, timeout=1)
    ws = await websockets.connect(url)
    ser.write(b'\x07\x0c\x1f\x40\x41connexion\x0a')
    ser.write(b'\x1b\x3b\x60\x58\x52')
    connected = True
    log(f"Connected to {url} at {tty} ({speed} bps)")

async def w2m():
    while connected:
        try:
            data = await ws.recv()
            ser.write(data.encode())
        except:
            break

async def m2w():
    while connected:
        try:
            if ser.inWaiting() > 0:
                tosend = ser.read(ser.inWaiting()).decode()
                await ws.send(tosend)
            else:
                await asyncio.sleep(0.1)
        except:
            break

bridge_loop = None

def start_bridge(url, port, baud):
    global connected, bridge_loop

    async def run_bridge():
     global ser, ws, connected, tasks
     try:
         await bridge(url, port, baud)
         update_ui_state(connected=True)
         tasks = [asyncio.create_task(w2m()), asyncio.create_task(m2w())]
         await asyncio.gather(*tasks)
     except asyncio.CancelledError:
         log("Bridge tasks cancelled.")
     except Exception as e:
         log(f"!! Error: {e}")
         messagebox.showerror("Connection Error", str(e))
         update_ui_state(disconnected=True)
     finally:
         try:
             if ws and not ws.closed:
                 await ws.close()
             if ser:
                 ser.dtr = False
                 ser.rts = False
                 ser.flush()
                 ser.reset_input_buffer()
                 ser.reset_output_buffer()
                 ser.close()
                 del ser
                 log("Serial port force closed.")
         except Exception as e:
             log(f"Force close failed: {e}")

         connected = False
         tasks.clear()




    def thread_target():
        global bridge_loop
        bridge_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(bridge_loop)
        try:
            bridge_loop.run_until_complete(run_bridge())
        except Exception as e:
            log(f"Loop crash: {e}")
        finally:
            bridge_loop.close()

    threading.Thread(target=thread_target, daemon=True).start()

def on_disconnect():
    global bridge_loop
    if connected and bridge_loop and tasks:
        for task in tasks:
            bridge_loop.call_soon_threadsafe(task.cancel)
        log("Disconnecting...")
    else:
        log("No active connection to disconnect.")
    update_ui_state(disconnected=True)


def on_connect():
    if connected:
        messagebox.showinfo("Already connected", "Please disconnect first or wait a while before reconnecting.")
        return
    url, port, baud = url_entry.get(), port_entry.get(), baud_entry.get()
    if not url or not port or not baud:
        messagebox.showwarning("Missing Info", "Please fill in all fields.")
        return
    update_ui_state(connecting=True)
    log("Attempting to connect...")
    threading.Thread(target=start_bridge, args=(url, port, baud), daemon=True).start()

def on_disconnect():
    if connected:
        log("Disconnecting...")
        safe_close()
        log("Disconnected.")
    update_ui_state(disconnected=True)

def on_reset():
    on_disconnect()
    url_entry.delete(0, tk.END)
    port_entry.delete(0, tk.END)
    baud_entry.delete(0, tk.END)
    update_ui_state(disconnected=True)
    log("All fields cleared.")

def update_ui_state(connecting=False, connected=False, disconnected=False):
    if connecting:
        connect_button.config(state='disabled')
        disconnect_button.config(state='disabled')
        reset_button.config(state='normal')
    elif connected:
        connect_button.config(state='disabled')
        disconnect_button.config(state='normal')
        reset_button.config(state='normal')
    elif disconnected:
        connect_button.config(state='normal')
        disconnect_button.config(state='disabled')
        reset_button.config(state='disabled')

def load_favorites():
    if os.path.exists(favorites_file):
        with open(favorites_file, "r") as f:
            return json.load(f)
    return []

def save_favorites():
    with open(favorites_file, "w") as f:
        json.dump(list(speed_dial.get(0, tk.END)), f)

def add_favorite():
    url = url_entry.get()
    if url and url not in speed_dial.get(0, tk.END):
        speed_dial.insert(tk.END, url)
        save_favorites()
        log(f"Saved '{url}' to speed dial.")

def remove_favorite():
    selected = speed_dial.curselection()
    if selected:
        speed_dial.delete(selected)
        save_favorites()
        log("Entry removed from speed dial.")

def fill_from_favorite(event):
    selected = speed_dial.curselection()
    if selected:
        url_entry.delete(0, tk.END)
        url_entry.insert(0, speed_dial.get(selected))
        log(f"Loaded '{speed_dial.get(selected)}' from speed dial.")

# GUI Setup
root = tk.Tk()
root.title("Websocket2Minitel GUI Ver. 1.0 - By SethTheKitsune")
root.configure(bg="#1e1e1e")
root.minsize(640, 440)

fg_color = "#eeeeee"
bg_color = "#1e1e1e"
entry_bg = "#2b2b2b"

# Speed Dial
speed_dial_frame = tk.Frame(root, bg=bg_color)
speed_dial_frame.grid(row=0, column=0, rowspan=3, sticky="ns", padx=(10, 5), pady=10)

tk.Label(speed_dial_frame, text="Speed Dial", bg=bg_color, fg=fg_color).pack(anchor="w")
speed_dial = tk.Listbox(speed_dial_frame, height=20, width=40, bg=entry_bg, fg=fg_color, selectbackground="#444")
speed_dial.pack(pady=5)
speed_dial.bind("<Double-Button-1>", fill_from_favorite)
tk.Button(speed_dial_frame, text="Add", command=add_favorite, width=12).pack(pady=1)
tk.Button(speed_dial_frame, text="Remove", command=remove_favorite, width=12).pack(pady=1)

# Main Fields
form_frame = tk.Frame(root, bg=bg_color)
form_frame.grid(row=0, column=1, sticky="n", padx=5, pady=(10, 0))

tk.Label(form_frame, text="WebSocket URL:", bg=bg_color, fg=fg_color).grid(row=0, column=0, sticky="w")
url_entry = tk.Entry(form_frame, width=35, bg=entry_bg, fg=fg_color)
url_entry.grid(row=1, column=0, sticky="ew", pady=2)

tk.Label(form_frame, text="Serial Port (COMXX):", bg=bg_color, fg=fg_color).grid(row=2, column=0, sticky="w")
port_entry = tk.Entry(form_frame, width=15, bg=entry_bg, fg=fg_color)
port_entry.insert(0, "COM4")
port_entry.grid(row=3, column=0, sticky="ew", pady=2)

tk.Label(form_frame, text="Baud Rate (bps):", bg=bg_color, fg=fg_color).grid(row=4, column=0, sticky="w")
baud_entry = tk.Entry(form_frame, width=10, bg=entry_bg, fg=fg_color)
baud_entry.insert(0, "4800")
baud_entry.grid(row=5, column=0, sticky="w", pady=2)

btn_frame = tk.Frame(form_frame, bg=bg_color)
btn_frame.grid(row=6, column=0, pady=(10, 0))
connect_button = tk.Button(btn_frame, text="Connect!", command=on_connect, width=10)
connect_button.pack(side="left", padx=2)
disconnect_button = tk.Button(btn_frame, text="Disconnect", command=on_disconnect, state='disabled', width=10)
disconnect_button.pack(side="left", padx=2)
reset_button = tk.Button(btn_frame, text="Clear", command=on_reset, state='disabled', width=10)
reset_button.pack(side="left", padx=2)

# Log
logbox = scrolledtext.ScrolledText(root, height=10, width=20, bg=entry_bg, fg=fg_color, state='disabled')
logbox.grid(row=1, column=1, padx=10, pady=10, sticky="nsew", rowspan=2)

root.grid_rowconfigure(2, weight=1)
root.grid_columnconfigure(1, weight=1)
log("GUI initialized correctly.")


# Load favorites on startup
for url in load_favorites():
    speed_dial.insert(tk.END, url)

url_entry.focus()
root.mainloop()
