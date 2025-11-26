import ctypes
import time
import mido
import os
import keyboard
import win32gui
import win32con
import win32api
import sys
import json
import threading
from ctypes import wintypes

# ============================================================================
# 1. CONFIGURATION
# ============================================================================
CONFIG = {
    "midi_root": "midis",         
    "window_title": "Where Winds Meet", 
    "db_file": "track_selections.json",
    
    # Input Tuning
    "note_hold_time": 0,          
    "chord_strum_delay": 0,
    
    # Controls
    "speed_step": 0.1,            
    "seek_step": 10.0,
}

# ============================================================================
# 2. APP STATE
# ============================================================================
state = {
    # Flags
    "paused": False,
    "muted": False,
    "looping": False,
    "running": True,
    
    # Triggers
    "restart_flag": False,        
    "request_selection": False,   
    "request_track_mixer": False, 
    "mixer_ready_event": threading.Event(),
    "player_ready_for_mixer": threading.Event(), 
    
    # Playback Data
    "current_index": 0,
    "playlist": [],               
    "current_folder_name": "ALL", 
    "playback_speed": 1.0,
    "manual_track_indices": None, 
    
    # REPLACED: seek_seconds/percent with Ticks for precision
    "resume_from_tick": 0,
    
    # Persistence
    "track_db": {}, 
    "game_hwnd": None,
    
    # UI Buffer
    "dashboard": {
        "st": "STOPPED", "bar": "", 
        "curr": "00:00", "tot": "00:00", 
        "spd": "1.0", "song": "", "mixer": ""
    }
}

# ============================================================================
# 3. GENERAL MIDI INSTRUMENT LIST
# ============================================================================
GM_INSTRUMENTS = {
    0: "Acoustic Grand Piano", 1: "Bright Acoustic Piano", 2: "Electric Grand Piano", 3: "Honky-tonk Piano",
    4: "Electric Piano 1", 5: "Electric Piano 2", 6: "Harpsichord", 7: "Clavinet",
    8: "Celesta", 9: "Glockenspiel", 10: "Music Box", 11: "Vibraphone",
    12: "Marimba", 13: "Xylophone", 14: "Tubular Bells", 15: "Dulcimer",
    16: "Drawbar Organ", 17: "Percussive Organ", 18: "Rock Organ", 19: "Church Organ",
    20: "Reed Organ", 21: "Accordion", 22: "Harmonica", 23: "Tango Accordion",
    24: "Acoustic Guitar (nylon)", 25: "Acoustic Guitar (steel)", 26: "Electric Guitar (jazz)", 27: "Electric Guitar (clean)",
    28: "Electric Guitar (muted)", 29: "Overdriven Guitar", 30: "Distortion Guitar", 31: "Guitar Harmonics",
    32: "Acoustic Bass", 33: "Electric Bass (finger)", 34: "Electric Bass (pick)", 35: "Fretless Bass",
    36: "Slap Bass 1", 37: "Slap Bass 2", 38: "Synth Bass 1", 39: "Synth Bass 2",
    40: "Violin", 41: "Viola", 42: "Cello", 43: "Contrabass",
    44: "Tremolo Strings", 45: "Pizzicato Strings", 46: "Orchestral Harp", 47: "Timpani",
    48: "String Ensemble 1", 49: "String Ensemble 2", 50: "Synth Strings 1", 51: "Synth Strings 2",
    52: "Choir Aahs", 53: "Voice Oohs", 54: "Synth Voice", 55: "Orchestra Hit",
    56: "Trumpet", 57: "Trombone", 58: "Tuba", 59: "Muted Trumpet",
    60: "French Horn", 61: "Brass Section", 62: "Synth Brass 1", 63: "Synth Brass 2",
    64: "Soprano Sax", 65: "Alto Sax", 66: "Tenor Sax", 67: "Baritone Sax",
    68: "Oboe", 69: "English Horn", 70: "Bassoon", 71: "Clarinet",
    72: "Piccolo", 73: "Flute", 74: "Recorder", 75: "Pan Flute",
    76: "Blown Bottle", 77: "Shakuhachi", 78: "Whistle", 79: "Ocarina",
    80: "Lead 1 (square)", 81: "Lead 2 (sawtooth)", 82: "Lead 3 (calliope)", 83: "Lead 4 (chiff)",
    84: "Lead 5 (charang)", 85: "Lead 6 (voice)", 86: "Lead 7 (fifths)", 87: "Lead 8 (bass + lead)",
    88: "Pad 1 (new age)", 89: "Pad 2 (warm)", 90: "Pad 3 (polysynth)", 91: "Pad 4 (choir)",
    92: "Pad 5 (bowed)", 93: "Pad 6 (metallic)", 94: "Pad 7 (halo)", 95: "Pad 8 (sweep)",
    96: "FX 1 (rain)", 97: "FX 2 (soundtrack)", 98: "FX 3 (crystal)", 99: "FX 4 (atmosphere)",
    100: "FX 5 (brightness)", 101: "FX 6 (goblins)", 102: "FX 7 (echoes)", 103: "FX 8 (sci-fi)",
    104: "Sitar", 105: "Banjo", 106: "Shamisen", 107: "Koto",
    108: "Kalimba", 109: "Bag pipe", 110: "Fiddle", 111: "Shanai",
    112: "Tinkle Bell", 113: "Agogo", 114: "Steel Drums", 115: "Woodblock",
    116: "Taiko Drum", 117: "Melodic Tom", 118: "Synth Drum", 119: "Reverse Cymbal",
    120: "Guitar Fret Noise", 121: "Breath Noise", 122: "Seashore", 123: "Bird Tweet",
    124: "Telephone Ring", 125: "Helicopter", 126: "Applause", 127: "Gunshot"
}

# ============================================================================
# 4. DB & INPUT LOGIC
# ============================================================================
def load_track_db():
    if os.path.exists(CONFIG["db_file"]):
        try:
            with open(CONFIG["db_file"], "r") as f: state["track_db"] = json.load(f)
        except: state["track_db"] = {}
    else: state["track_db"] = {}

def save_track_db():
    try:
        with open(CONFIG["db_file"], "w") as f: json.dump(state["track_db"], f, indent=4)
    except: pass

SC_LSHIFT = 0x2A; SC_LCTRL = 0x1D
SCAN_CODES = { 'z':0x2C,'x':0x2D,'c':0x2E,'v':0x2F,'b':0x30,'n':0x31,'m':0x32,'a':0x1E,'s':0x1F,'d':0x20,'f':0x21,'g':0x22,'h':0x23,'j':0x24,'q':0x10,'w':0x11,'e':0x12,'r':0x13,'t':0x14,'y':0x15,'u':0x16 }
NOTE_MAP = {48:(None,'z'),49:('shift','z'),50:(None,'x'),51:('ctrl','c'),52:(None,'c'),53:(None,'v'),54:('shift','v'),55:(None,'b'),56:('shift','b'),57:(None,'n'),58:('ctrl','m'),59:(None,'m'),60:(None,'a'),61:('shift','a'),62:(None,'s'),63:('ctrl','d'),64:(None,'d'),65:(None,'f'),66:('shift','f'),67:(None,'g'),68:('shift','g'),69:(None,'h'),70:('ctrl','j'),71:(None,'j'),72:(None,'q'),73:('shift','q'),74:(None,'w'),75:('ctrl','e'),76:(None,'e'),77:(None,'r'),78:('shift','r'),79:(None,'t'),80:('shift','t'),81:(None,'y'),82:('ctrl','u'),83:(None,'u')}

def press_atomic(modifier, key_char):
    hwnd = state.get("game_hwnd")
    if not hwnd: return

    sc_key = SCAN_CODES.get(key_char.lower(), 0)
    vk_key = ord(key_char.upper())
    if sc_key == 0: return

    def pm(msg, w, l):
        win32api.PostMessage(hwnd, msg, w, l)

    if modifier == 'shift': 
        pm(win32con.WM_KEYDOWN, 0xA0, 0x002A0001) 
    elif modifier == 'ctrl': 
        pm(win32con.WM_KEYDOWN, 0xA2, 0x001D0001)

    lparam_down = 1 | (sc_key << 16)
    pm(win32con.WM_KEYDOWN, vk_key, lparam_down)

    if CONFIG["note_hold_time"] > 0: time.sleep(CONFIG["note_hold_time"])

    lparam_up = 1 | (sc_key << 16) | 0xC0000001
    pm(win32con.WM_KEYUP, vk_key, lparam_up)

    if modifier == 'shift': pm(win32con.WM_KEYUP, 0xA0, 0xC02A0001)
    elif modifier == 'ctrl': pm(win32con.WM_KEYUP, 0xA2, 0xC01D0001)

# ============================================================================
# 5. WINDOW & FOCUS
# ============================================================================
def focus_terminal():
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd: 
            if win32gui.IsIconic(hwnd): win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            win32gui.SetForegroundWindow(hwnd)
            win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    except: pass

def get_game_hwnd():
    toplist = []; 
    def enum_win(hwnd, result): toplist.append((hwnd, win32gui.GetWindowText(hwnd)))
    win32gui.EnumWindows(enum_win, toplist)
    for (hwnd, title) in toplist:
        if CONFIG["window_title"].lower() in title.lower(): return hwnd
    return None

def minimize_game_window():
    hwnd = get_game_hwnd()
    if hwnd:
        try: win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        except: pass

def handle_focus_state():
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        # Just a check (logic can be expanded if needed)
        is_focused = CONFIG["window_title"].lower() in title.lower()
    except: pass

# ============================================================================
# 6. HOTKEYS & CONTROLS
# ============================================================================
def next_song():
    if not state["playlist"]: return
    state["current_index"] = (state["current_index"] + 1) % len(state["playlist"])
    state["restart_flag"] = True; state["manual_track_indices"] = None; state["resume_from_tick"] = 0
def prev_song():
    if not state["playlist"]: return
    state["current_index"] = (state["current_index"] - 1) % len(state["playlist"])
    state["restart_flag"] = True; state["manual_track_indices"] = None; state["resume_from_tick"] = 0

def toggle_pause(): state["paused"] = not state["paused"]
def toggle_mute(): state["muted"] = not state["muted"]
def toggle_loop(): state["looping"] = not state["looping"]
def stop_script(): state["running"] = False; state["restart_flag"] = True
def trigger_menu(): state["request_selection"] = True
def trigger_mixer(): state["request_track_mixer"] = True
def speed_up(): state["playback_speed"] = min(state["playback_speed"] + CONFIG["speed_step"], 10.0)
def speed_down(): state["playback_speed"] = max(state["playback_speed"] - CONFIG["speed_step"], 0.1)

keyboard.add_hotkey('right', next_song)
keyboard.add_hotkey('left', prev_song)
keyboard.add_hotkey('up', speed_up)
keyboard.add_hotkey('down', speed_down)
keyboard.add_hotkey('F3', toggle_pause)
keyboard.add_hotkey('F4', stop_script)
keyboard.add_hotkey('F5', trigger_menu)
keyboard.add_hotkey('F6', toggle_mute)
keyboard.add_hotkey('F7', trigger_mixer)
keyboard.add_hotkey('F8', toggle_loop)

# ============================================================================
# 7. UI HELPERS
# ============================================================================
def format_time(seconds):
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def update_dashboard(current_sec, total_sec, is_seeking=False):
    if total_sec == 0: total_sec = 1
    percent = min(current_sec / total_sec, 1.0)
    filled = int(35 * percent)
    bar = "█" * filled + "░" * (35 - filled)
    
    if is_seeking: st = "⏩ SEEKING    "
    elif state["paused"]: st = "⏸  PAUSED     "
    elif state["muted"]: st = "🔇 MUTED      "
    elif state["looping"]: st = "🔁 LOOPING    "
    else: st = "▶  PLAYING    "
    
    state["dashboard"].update({
        "st": st, "bar": bar, 
        "curr": format_time(current_sec), "tot": format_time(total_sec), 
        "spd": f"{state['playback_speed']:.1f}"
    })

def print_dashboard():
    d = state["dashboard"]
    sys.stdout.write(f"\r{d['st']} | {d['bar']} | {d['curr']} / {d['tot']} | Spd: {d['spd']}x   ")
    sys.stdout.flush()

# ============================================================================
# 8. FILE & TRACK LOGIC (REFACTORED)
# ============================================================================
def get_subfolders():
    if not os.path.exists(CONFIG["midi_root"]): os.makedirs(CONFIG["midi_root"])
    return sorted([d for d in os.listdir(CONFIG["midi_root"]) if os.path.isdir(os.path.join(CONFIG["midi_root"], d))])

def scan_files(subfolder=None):
    file_list = []
    root_path = CONFIG["midi_root"]
    if subfolder:
        target_path = os.path.join(root_path, subfolder)
        for f in os.listdir(target_path):
            if f.lower().endswith(('.mid', '.midi')): file_list.append(os.path.join(target_path, f))
    else:
        for dirpath, _, filenames in os.walk(root_path):
            for f in filenames:
                if f.lower().endswith(('.mid', '.midi')): file_list.append(os.path.join(dirpath, f))
    return sorted(file_list)

def get_track_info(mid):
    info = []
    for i, track in enumerate(mid.tracks):
        note_count = sum(1 for m in track if m.type == 'note_on' and m.velocity > 0)
        instrument = "Unknown"; is_drum = False
        for msg in track:
            if msg.type == 'program_change': 
                instrument = GM_INSTRUMENTS.get(msg.program, f"Prog {msg.program}")
                break
            if msg.type == 'note_on' and msg.channel == 9: 
                is_drum = True; instrument = "DRUMS (Ch10)"; break
        if note_count > 0: info.append({'index': i, 'name': track.name.strip(), 'notes': note_count, 'inst': instrument, 'drum': is_drum})
    return info

def prepare_midi_data(full_path, manual_indices=None):
    """
    Refactored helper to parse MIDI, select tracks, and build the timeline.
    Returns: (mido_obj, events_dict, total_duration_sec, active_tracks_count, total_playable_tracks, tempo)
    """
    try:
        mid = mido.MidiFile(full_path)
    except:
        return None, None, 0, 0, 0, 500000

    # 1. Determine Tracks to Play
    fname = os.path.basename(full_path)
    indices = []
    track_source_name = "Auto"
    
    if manual_indices:
        indices = manual_indices
        track_source_name = "Manual"
    elif fname in state["track_db"]:
        data = state["track_db"][fname]
        if isinstance(data, dict):
            indices = data.get("tracks", [])
            # Update speed if saved
            if "speed" in data: state["playback_speed"] = data["speed"]
            track_source_name = "Saved Mix"
        elif isinstance(data, list):
            indices = data
            track_source_name = "Saved Mix"
    
    # Fallback: Auto-select busiest track if no indices found
    if not indices:
        best = 0; maxn = 0
        for i, t in enumerate(mid.tracks):
            c = sum(1 for m in t if m.type == 'note_on' and m.velocity > 0)
            if c > maxn: maxn, best = c, i
        indices = [best]
        track_source_name = f"Auto (Trk {best})"

    # 2. Build Event Dictionary (Absolute Ticks -> Notes)
    events_by_time = {}
    total_playable_tracks = sum(1 for t in mid.tracks if sum(1 for m in t if m.type == 'note_on' and m.velocity > 0) > 0)
    
    for i in indices:
        if i < len(mid.tracks):
            track = mid.tracks[i]
            curr_ticks = 0
            for msg in track:
                curr_ticks += msg.time
                if msg.type == 'note_on' and msg.velocity > 0:
                    if curr_ticks not in events_by_time: events_by_time[curr_ticks] = []
                    events_by_time[curr_ticks].append(msg.note)

    # 3. Calculate Meta Data
    sorted_times = sorted(events_by_time.keys())
    last_tick = sorted_times[-1] if sorted_times else 0
    tempo = mido.bpm2tempo(120) # Default
    
    # Scan for tempo changes (simplified: takes last tempo found in track 0)
    for msg in mid.tracks[0]:
        if msg.type == 'set_tempo': tempo = msg.tempo

    total_duration = mido.tick2second(last_tick, mid.ticks_per_beat, tempo)
    
    state["dashboard"]["mixer"] = f"{track_source_name} | Active: {len(indices)} / {total_playable_tracks} Tracks"
    
    return mid, events_by_time, total_duration, len(indices), total_playable_tracks, tempo

# ============================================================================
# 9. MENUS
# ============================================================================
def run_track_mixer(full_path):
    # --- HANDSHAKE: Wait for Player to Pause & Save State ---
    # This prevents the UI from appearing before the resume_from_tick is saved.
    state["player_ready_for_mixer"].wait(timeout=2.0)
    state["player_ready_for_mixer"].clear()
    
    minimize_game_window()
    time.sleep(0.2)
    focus_terminal()
    time.sleep(0.2)
    
    try: mid = mido.MidiFile(full_path)
    except: return
    
    tracks = get_track_info(mid)
    fname = os.path.basename(full_path)
    
    # Load selection
    selected = set()
    if state["manual_track_indices"]:
        selected = set(state["manual_track_indices"])
    elif fname in state["track_db"]:
        data = state["track_db"][fname]
        if isinstance(data, list): selected = set(data)
        elif isinstance(data, dict): selected = set(data.get("tracks", []))
    else:
        best = max(tracks, key=lambda t: t['notes'])['index']
        selected = {best}

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("="*70); print(f"🎛️  TRACK MIXER: {fname}"); print("="*70)
        print("Toggle tracks by number. Press ENTER to Resume."); print("-" * 70)
        print(f"{'#':<4} {'[x]':<5} {'NOTES':<8} {'INSTRUMENT':<25} {'NAME'}")
        for t in tracks:
            chk = "[x]" if t['index'] in selected else "[ ]"; warn = "⚠️" if t['drum'] else ""
            print(f"{t['index']:<4} {chk:<5} {t['notes']:<8} {t['inst']:<25} {t['name']} {warn}")
        print("-" * 70)
        inp = input("Toggle # > ")
        if inp == "": break
        try:
            idx = int(inp)
            if any(t['index'] == idx for t in tracks):
                if idx in selected: selected.remove(idx)
                else: selected.add(idx)
        except: pass
    
    # Save Data
    if fname not in state["track_db"] or isinstance(state["track_db"][fname], list):
        state["track_db"][fname] = {}
    
    state["track_db"][fname]["tracks"] = list(selected)
    if "speed" not in state["track_db"][fname]:
        state["track_db"][fname]["speed"] = state["playback_speed"]
        
    save_track_db()
    state["manual_track_indices"] = list(selected)
    state["restart_flag"] = True 
    # SYNC: Tell playback thread we are done
    state["mixer_ready_event"].set()

def run_selection_menu():
    minimize_game_window()
    time.sleep(0.2)
    focus_terminal()
    time.sleep(0.2)
    
    os.system('cls' if os.name == 'nt' else 'clear')
    subfolders = get_subfolders()
    print("="*50); print("      📂 PLAYLIST SELECTION"); print("="*50); print(f"[1]  🔥 ALL SONGS (Master)")
    for i, folder in enumerate(subfolders): print(f"[{i+2}]  📂 {folder}")
    try:
        user_input = input("\nSelect Folder # > ")
        if not user_input: return
        
        choice = int(user_input)
        temp_playlist = []; temp_folder_name = "ALL"
        
        if choice == 1: temp_playlist = scan_files(None)
        elif 2 <= choice <= len(subfolders) + 1: 
            temp_folder_name = subfolders[choice - 2]
            temp_playlist = scan_files(temp_folder_name)
        else: return

        if temp_playlist:
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"--- SONGS IN: {temp_folder_name} ---")
            for i, full_path in enumerate(temp_playlist): 
                print(f"[{i+1}] {os.path.basename(full_path)}")
            
            print("\n(Enter number to Play, or leave empty to Cancel)")
            si = input("Start Song # > ")
            
            if si.strip():
                state["playlist"] = temp_playlist
                state["current_folder_name"] = temp_folder_name
                state["current_index"] = int(si) - 1
                state["restart_flag"] = True
                state["resume_from_tick"] = 0
                state["manual_track_indices"] = None
            else:
                print("Selection Cancelled.")
                time.sleep(0.5)
    except: pass

# ============================================================================
# 10. PLAYBACK LOOP
# ============================================================================
def check_seek_keys(accumulated_time, total_duration, mid, tempo):
    """
    Checks for PageUp/PageDown.
    Converts the Time Seek into a Tick Seek for the main loop to handle.
    """
    target_sec = -1
    if keyboard.is_pressed('page down'):
        target_sec = min(accumulated_time + CONFIG["seek_step"], total_duration)
    elif keyboard.is_pressed('page up'):
        target_sec = max(accumulated_time - CONFIG["seek_step"], 0.0)
    
    if target_sec != -1:
        # Convert Seconds -> Ticks to ensure we resume at exact grid position
        target_ticks = mido.second2tick(target_sec, mid.ticks_per_beat, tempo)
        state["resume_from_tick"] = int(target_ticks)
        state["restart_flag"] = True
        return True
    return False

def wait_for_playback(real_wait, accumulated_time, total_duration, mid, tempo):
    start_wait = time.time()
    while True:
        # Handle Pause
        while state["paused"]:
            update_dashboard(accumulated_time, total_duration)
            time.sleep(0.1)
            if state["restart_flag"] or state["request_track_mixer"]: return True
            if check_seek_keys(accumulated_time, total_duration, mid, tempo): return True

        # Check Interrupts
        if state["restart_flag"] or state["request_track_mixer"]: return True
        if check_seek_keys(accumulated_time, total_duration, mid, tempo): return True

        # Check Time
        elapsed = time.time() - start_wait
        target_wait = real_wait / state["playback_speed"]
        if elapsed >= target_wait: return False
        
        # Update UI & Sleep
        update_dashboard(accumulated_time, total_duration)

def playback_worker():
    last_path = None
    while state["running"]:
        # Race Condition Fix: Reset flag at START of loop
        state["restart_flag"] = False

        if not state["playlist"]: time.sleep(1); continue
        
        full_path = state["playlist"][state["current_index"]]
        
        # --- RESET SPEED ON TRACK CHANGE ---
        if full_path != last_path:
            state["playback_speed"] = 1.0
            last_path = full_path

        state["dashboard"]["song"] = os.path.basename(full_path)

        # --- PREPARE DATA (Refactored) ---
        mid, events_by_time, total_duration, _, _, tempo = prepare_midi_data(full_path, state["manual_track_indices"])
        
        if not mid or not events_by_time:
            time.sleep(1); continue

        state["game_hwnd"] = get_game_hwnd()
        
        sorted_times = sorted(events_by_time.keys())
        prev_tick = 0
        
        # If resuming, calculate starting time for UI
        accumulated_time = 0.0
        if state["resume_from_tick"] > 0:
            accumulated_time = mido.tick2second(state["resume_from_tick"], mid.ticks_per_beat, tempo)

        # --- TICK LOOP ---
        for current_tick in sorted_times:
            if state["restart_flag"] or not state["running"]: break
            
            # --- SEEKING LOGIC (The Fix) ---
            if current_tick < state["resume_from_tick"]:
                prev_tick = current_tick
                continue
            
            # --- CRITICAL FIX: ALIGN PREV_TICK ---
            if state["resume_from_tick"] > 0:
                prev_tick = state["resume_from_tick"]
                state["resume_from_tick"] = 0

            # --- MIXER INTERRUPT (CHECK #1: Before Waiting) ---
            if state["request_track_mixer"]:
                state["resume_from_tick"] = current_tick
                state["player_ready_for_mixer"].set() 
                state["mixer_ready_event"].clear()
                while state["request_track_mixer"] and state["running"]:
                    state["mixer_ready_event"].wait(timeout=0.1)
                break 

            # --- CALCULATE DELTA ---
            delta_ticks = current_tick - prev_tick
            if delta_ticks > 0:
                real_wait = mido.tick2second(delta_ticks, mid.ticks_per_beat, tempo)
                accumulated_time += real_wait
                
                # --- WAIT (Handles Speed/Pause/Input) ---
                if accumulated_time < state["resume_from_tick"]: # Visual seek only
                     if int(accumulated_time * 100) % 2 == 0: 
                         update_dashboard(accumulated_time, total_duration, is_seeking=True)
                else:
                    interrupted = wait_for_playback(real_wait, accumulated_time, total_duration, mid, tempo)
                    
                    # --- MIXER INTERRUPT (CHECK #2: After Waiting) ---
                    # Crucial Fix: If interrupted by mixer while sleeping, save position NOW.
                    if interrupted and state["request_track_mixer"]:
                         state["resume_from_tick"] = current_tick
                         state["player_ready_for_mixer"].set()
                         state["mixer_ready_event"].clear()
                         while state["request_track_mixer"] and state["running"]:
                             state["mixer_ready_event"].wait(timeout=0.1)
                         break

                    if interrupted: break

            # --- PLAY NOTES ---
            for note in events_by_time[current_tick]:
                if note in NOTE_MAP and not state["muted"]:
                    mod, key = NOTE_MAP[note]
                    press_atomic(mod, key)
                    if CONFIG["chord_strum_delay"] > 0: time.sleep(CONFIG["chord_strum_delay"])
            
            prev_tick = current_tick
        
        # --- END OF SONG ---
        if not state["restart_flag"] and not state["request_track_mixer"] and state["running"]:
             state["resume_from_tick"] = 0
             if not state["looping"]: next_song()
             time.sleep(1)
        
        # Save speed changes if any occurred
        if state["playback_speed"] != 1.0:
            fname = os.path.basename(full_path)
            if fname not in state["track_db"]: state["track_db"][fname] = {}
            if isinstance(state["track_db"][fname], dict):
                state["track_db"][fname]["speed"] = state["playback_speed"]
            save_track_db()

def main():
    os.system("") 
    load_track_db()
    state["playlist"] = [] 
    
    t = threading.Thread(target=playback_worker, daemon=True)
    t.start()

    print("="*80); print("🎵 JUKEBOX STARTED"); print("="*80)
    print("⌨️  F3:Pause F4:Stop F5:Menu F6:Mute F7:Mixer F8:Loop | PgUp/Dn: Seek | Arrows: Nav")
    sys.stdout.write("\033[?25l") # Hide Cursor

    # Force Menu on Start
    state["request_selection"] = True

    last_song = ""
    while state["running"]:
        if state["request_selection"]:
            state["request_selection"] = False
            run_selection_menu()
            last_song = "" 

        elif state["request_track_mixer"]:
            run_track_mixer(state["playlist"][state["current_index"]])
            state["request_track_mixer"] = False 
            last_song = "" 

        else:
            handle_focus_state()
            curr_song = state["dashboard"]["song"]
            
            if curr_song != last_song and curr_song:
                last_song = curr_song
                os.system('cls' if os.name == 'nt' else 'clear')
                print("="*80); print(f"🎵 NOW PLAYING: {curr_song}")
                print(f"🎛️  Mixer: {state['dashboard']['mixer']}"); print("="*80)
                print("\n\n"); print("="*80)
                print("⌨️  F3:Pause F4:Stop F5:Menu F6:Mute F7:Mixer L:Loop | PgUp/Dn: Seek | Arrows: Nav"); print("="*80)
                sys.stdout.write("\033[?25l"); sys.stdout.write("\033[5A") 
            
            if curr_song:
                print_dashboard()
            time.sleep(0.1)
    
    sys.stdout.write("\033[?25h")

if __name__ == "__main__":
    main()