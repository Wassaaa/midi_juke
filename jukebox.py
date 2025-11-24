import ctypes
import time
import mido
import os
import keyboard
import win32gui
import win32con
import sys
import json
from ctypes import wintypes

# ============================================================================
# 1. CONFIGURATION
# ============================================================================
CONFIG = {
    "midi_root": "midis",         
    "window_title": "Where Winds Meet", 
    "db_file": "track_selections.json",
    "note_hold_time": 0,          
    "chord_strum_delay": 0.002,
    "speed_step": 0.1,            
    "seek_step": 10.0,
}

# ============================================================================
# 2. APP STATE
# ============================================================================
state = {
    "paused": False, "muted": False, "muted_by_focus": False, "looping": False,
    "running": True, "restart_flag": False, "request_selection": False, "request_track_mixer": False, 
    "current_index": 0, "playlist": [], "current_folder_name": "ALL", 
    "playback_speed": 1.0, "manual_track_indices": None, "resume_seek_seconds": 0.0,
    "track_db": {}, 
}

# ============================================================================
# 3. GENERAL MIDI INSTRUMENT LIST (0-127)
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

SendInput = ctypes.windll.user32.SendInput
SC_LSHIFT = 0x2A; SC_LCTRL = 0x1D
SCAN_CODES = { 'z':0x2C,'x':0x2D,'c':0x2E,'v':0x2F,'b':0x30,'n':0x31,'m':0x32,'a':0x1E,'s':0x1F,'d':0x20,'f':0x21,'g':0x22,'h':0x23,'j':0x24,'q':0x10,'w':0x11,'e':0x12,'r':0x13,'t':0x14,'y':0x15,'u':0x16 }
NOTE_MAP = {48:(None,'z'),49:('shift','z'),50:(None,'x'),51:('ctrl','c'),52:(None,'c'),53:(None,'v'),54:('shift','v'),55:(None,'b'),56:('shift','b'),57:(None,'n'),58:('ctrl','m'),59:(None,'m'),60:(None,'a'),61:('shift','a'),62:(None,'s'),63:('ctrl','d'),64:(None,'d'),65:(None,'f'),66:('shift','f'),67:(None,'g'),68:('shift','g'),69:(None,'h'),70:('ctrl','j'),71:(None,'j'),72:(None,'q'),73:('shift','q'),74:(None,'w'),75:('ctrl','e'),76:(None,'e'),77:(None,'r'),78:('shift','r'),79:(None,'t'),80:('shift','t'),81:(None,'y'),82:('ctrl','u'),83:(None,'u')}

PUL = ctypes.POINTER(ctypes.c_ulong)
class KeyBdInput(ctypes.Structure): _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort), ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", PUL)]
class HardwareInput(ctypes.Structure): _fields_ = [("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_short), ("wParamH", ctypes.c_ushort)]
class MouseInput(ctypes.Structure): _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", PUL)]
class Input_I(ctypes.Union): _fields_ = [("ki", KeyBdInput), ("mi", MouseInput), ("hi", HardwareInput)]
class Input(ctypes.Structure): _fields_ = [("type", ctypes.c_ulong), ("ii", Input_I)]

def make_input(scancode, flags): return Input(1, Input_I(ki=KeyBdInput(0, scancode, 0x0008 | flags, 0, None)))
def send_atomic(inputs): n = len(inputs); LPINPUT = Input * n; p_inputs = LPINPUT(*inputs); ctypes.windll.user32.SendInput(n, p_inputs, ctypes.sizeof(Input))

def press_atomic(modifier, key_char):
    sc_key = SCAN_CODES.get(key_char.lower(), 0); 
    if sc_key==0: return
    seq_down=[]; 
    if modifier=='shift': seq_down.append(make_input(SC_LSHIFT, 0))
    elif modifier=='ctrl': seq_down.append(make_input(SC_LCTRL, 0))
    seq_down.append(make_input(sc_key, 0)); send_atomic(seq_down)
    if CONFIG["note_hold_time"]>0: time.sleep(CONFIG["note_hold_time"])
    seq_up=[]; seq_up.append(make_input(sc_key, 0x0002))
    if modifier=='shift': seq_up.append(make_input(SC_LSHIFT, 0x0002))
    elif modifier=='ctrl': seq_up.append(make_input(SC_LCTRL, 0x0002))
    send_atomic(seq_up)

def get_game_hwnd():
    toplist = []; 
    def enum_win(hwnd, result): toplist.append((hwnd, win32gui.GetWindowText(hwnd)))
    win32gui.EnumWindows(enum_win, toplist)
    for (hwnd, title) in toplist:
        if CONFIG["window_title"].lower() in title.lower(): return hwnd
    return None

def focus_game_window():
    hwnd = get_game_hwnd()
    if hwnd:
        try:
            if win32gui.IsIconic(hwnd): win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE); win32gui.SetForegroundWindow(hwnd); win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        except: pass

def minimize_game_window():
    hwnd = get_game_hwnd()
    if hwnd:
        try: win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        except: pass

def handle_focus_state():
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        is_focused = CONFIG["window_title"].lower() in title.lower()
        state["muted_by_focus"] = not is_focused
    except: pass

def next_song():
    if not state["playlist"]: return
    state["current_index"] = (state["current_index"] + 1) % len(state["playlist"]); state["restart_flag"] = True; state["paused"] = False; state["manual_track_indices"] = None; state["resume_seek_seconds"] = 0.0
def prev_song():
    if not state["playlist"]: return
    state["current_index"] = (state["current_index"] - 1) % len(state["playlist"]); state["restart_flag"] = True; state["paused"] = False; state["manual_track_indices"] = None; state["resume_seek_seconds"] = 0.0

def toggle_pause(): state["paused"] = not state["paused"]
def toggle_mute(): state["muted"] = not state["muted"]
def toggle_loop(): state["looping"] = not state["looping"]
def stop_script(): state["running"] = False; state["restart_flag"] = True
def trigger_menu(): state["request_selection"] = True; state["restart_flag"] = True; state["paused"] = False
def trigger_mixer(): state["request_track_mixer"] = True; state["restart_flag"] = True; state["paused"] = False
def speed_up(): state["playback_speed"] = min(state["playback_speed"] + CONFIG["speed_step"], 10.0)
def speed_down(): state["playback_speed"] = max(state["playback_speed"] - CONFIG["speed_step"], 0.1)

keyboard.add_hotkey('right', next_song); keyboard.add_hotkey('left', prev_song)
keyboard.add_hotkey('up', speed_up); keyboard.add_hotkey('down', speed_down)
keyboard.add_hotkey('F3', toggle_pause); keyboard.add_hotkey('F4', stop_script)
keyboard.add_hotkey('F5', trigger_menu); keyboard.add_hotkey('F6', toggle_mute)
keyboard.add_hotkey('F7', trigger_mixer); keyboard.add_hotkey('l', toggle_loop)

def format_time(seconds): mins = int(seconds // 60); secs = int(seconds % 60); return f"{mins:02d}:{secs:02d}"

def update_dashboard(current_sec, total_sec, is_seeking=False):
    if total_sec == 0: total_sec = 1
    percent = min(current_sec / total_sec, 1.0)
    filled = int(35 * percent)
    bar = "█" * filled + "░" * (35 - filled)
    
    if is_seeking: st = "⏩ SEEKING    "
    elif state["paused"]: st = "⏸  PAUSED     "
    elif state["muted"]: st = "🔇 MUTED      "
    elif state["muted_by_focus"]: st = "⚠️  BACKGROUND "
    elif state["looping"]: st = "🔁 LOOPING    "
    else: st = "▶  PLAYING    "
    
    sys.stdout.write(f"\r{st} | {bar} | {format_time(current_sec)} / {format_time(total_sec)} | Spd: {state['playback_speed']:.1f}x")
    sys.stdout.flush()

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

def run_track_mixer(full_path):
    minimize_game_window(); time.sleep(0.2)
    try: mid = mido.MidiFile(full_path)
    except: return
    tracks = get_track_info(mid)
    fname = os.path.basename(full_path)
    if fname in state["track_db"]:
        selected = set(state["track_db"][fname])
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
    state["track_db"][fname] = list(selected); save_track_db()
    state["manual_track_indices"] = list(selected); focus_game_window()

def run_selection_menu():
    minimize_game_window(); time.sleep(0.2)
    os.system('cls' if os.name == 'nt' else 'clear')
    subfolders = get_subfolders()
    print("="*50); print("       📂 PLAYLIST SELECTION"); print("="*50); print(f"[1]  🔥 ALL SONGS (Master)")
    for i, folder in enumerate(subfolders): print(f"[{i+2}]  📂 {folder}")
    try:
        user_input = input("\nSelect Folder # > ")
        if not user_input: return
        choice = int(user_input)
        new_playlist = []; folder_name = "ALL"
        if choice == 1: new_playlist = scan_files(None)
        elif 2 <= choice <= len(subfolders) + 1: folder_name = subfolders[choice - 2]; new_playlist = scan_files(folder_name)
        else: return
        if new_playlist:
            state["playlist"] = new_playlist; state["current_folder_name"] = folder_name; state["current_index"] = 0
            os.system('cls' if os.name == 'nt' else 'clear'); print(f"--- SONGS IN: {folder_name} ---")
            for i, full_path in enumerate(state["playlist"]): print(f"[{i+1}] {os.path.basename(full_path)}")
            si = input("\nStart Song # > ")
            if si.strip(): state["current_index"] = int(si) - 1
            state["resume_seek_seconds"] = 0.0 
    except: pass

def play_file(full_path):
    try: mid = mido.MidiFile(full_path)
    except: return
    ctypes.windll.kernel32.SetConsoleTitleW(f"Bard Bot - {os.path.basename(full_path)}")
    events_by_time = {}; tracks_to_play = []
    fname = os.path.basename(full_path)
    real_tracks_count = sum(1 for t in mid.tracks if sum(1 for m in t if m.type == 'note_on' and m.velocity > 0) > 0)

    if fname in state["track_db"]:
        saved_indices = state["track_db"][fname]
        for i in saved_indices:
            if i < len(mid.tracks): tracks_to_play.append(mid.tracks[i])
        track_source_name = "Saved Mix"
    else:
        best = 0; maxn = 0
        for i, t in enumerate(mid.tracks):
            c = sum(1 for m in t if m.type == 'note_on' and m.velocity > 0)
            if c > maxn: maxn, best = c, i
        tracks_to_play.append(mid.tracks[best])
        track_source_name = f"Auto (Track {best})"

    for track in tracks_to_play:
        curr = 0
        for msg in track:
            curr += msg.time
            if msg.type == 'note_on' and msg.velocity > 0:
                if curr not in events_by_time: events_by_time[curr] = []
                events_by_time[curr].append(msg.note)

    os.system('cls' if os.name == 'nt' else 'clear')
    print("="*80); print(f"🎵 NOW PLAYING: {os.path.basename(full_path)}")
    print(f"🎛️  Mixer: {track_source_name} | Active: {len(tracks_to_play)} / {real_tracks_count} Tracks"); print("="*80)
    print("\n\n"); print("="*80)
    print("⌨️  F3:Pause F4:Stop F5:Menu F6:Mute F7:Mixer L:Loop | PgUp/Dn: Seek | Arrows: Nav"); print("="*80)
    sys.stdout.write("\033[?25l"); sys.stdout.write("\033[5A") 

    sorted_times = sorted(events_by_time.keys())
    last_ticks = 0; tempo = mido.bpm2tempo(120)
    last_note_tick = sorted_times[-1] if sorted_times else 0
    total_duration = mido.tick2second(last_note_tick, mid.ticks_per_beat, tempo)
    accumulated_time = 0.0

    for t in sorted_times:
        if state["restart_flag"] or not state["running"]: break
        delta_ticks = t - last_ticks
        if delta_ticks > 0:
            real_wait = mido.tick2second(delta_ticks, mid.ticks_per_beat, tempo)
            accumulated_time += real_wait
            if accumulated_time < state["resume_seek_seconds"]:
                if int(accumulated_time * 100) % 5 == 0: update_dashboard(accumulated_time, total_duration, is_seeking=True)
                last_ticks = t; continue 

            if keyboard.is_pressed('page down'): state["resume_seek_seconds"] = min(accumulated_time + CONFIG["seek_step"], total_duration); return 
            if keyboard.is_pressed('page up'): state["resume_seek_seconds"] = max(accumulated_time - CONFIG["seek_step"], 0.0); return 

            handle_focus_state()
            start_wait = time.time()
            while True:
                while state["paused"]:
                    handle_focus_state(); update_dashboard(accumulated_time, total_duration); time.sleep(0.1)
                    if state["restart_flag"] or state["request_track_mixer"]: 
                        if state["request_track_mixer"]: state["resume_seek_seconds"] = accumulated_time
                        return
                    if keyboard.is_pressed('page down'): state["resume_seek_seconds"] = min(accumulated_time + CONFIG["seek_step"], total_duration); return
                    if keyboard.is_pressed('page up'): state["resume_seek_seconds"] = max(accumulated_time - CONFIG["seek_step"], 0.0); return

                elapsed = time.time() - start_wait
                target_wait = real_wait / state["playback_speed"]
                if elapsed >= target_wait: break
                if state["restart_flag"] or not state["running"]: break
                if state["request_track_mixer"]: state["resume_seek_seconds"] = accumulated_time; return
                if keyboard.is_pressed('page down'): state["resume_seek_seconds"] = min(accumulated_time + CONFIG["seek_step"], total_duration); return
                if keyboard.is_pressed('page up'): state["resume_seek_seconds"] = max(accumulated_time - CONFIG["seek_step"], 0.0); return
                handle_focus_state(); update_dashboard(accumulated_time, total_duration); time.sleep(0.01)

        if state["restart_flag"] or not state["running"]: break
        if state["request_track_mixer"]: state["resume_seek_seconds"] = accumulated_time; return

        for note in events_by_time[t]:
            if note in NOTE_MAP:
                if not state["muted"] and not state["muted_by_focus"]:
                    mod, key = NOTE_MAP[note]
                    press_atomic(mod, key)
                    if CONFIG["chord_strum_delay"] > 0: time.sleep(CONFIG["chord_strum_delay"])
        last_ticks = t
    
    sys.stdout.write("\033[?25h")
    if not state["restart_flag"]: state["resume_seek_seconds"] = 0.0

def main():
    os.system("") 
    load_track_db()
    state["playlist"] = scan_files(None)
    if not state["playlist"]: print(f"No files in '{CONFIG['midi_root']}'!"); return
    state["request_selection"] = True

    while state["running"]:
        if state["request_selection"]:
            run_selection_menu(); state["request_selection"] = False; state["restart_flag"] = False; state["playback_speed"] = 1.0; focus_game_window(); time.sleep(0.5)

        if state["request_track_mixer"]:
            run_track_mixer(state["playlist"][state["current_index"]]); state["request_track_mixer"] = False; state["restart_flag"] = False; focus_game_window(); time.sleep(0.5)

        if state["playlist"] and not state["request_selection"] and not state["request_track_mixer"]:
            play_file(state["playlist"][state["current_index"]])
            if not state["restart_flag"] and state["running"] and state["resume_seek_seconds"] == 0.0:
                if not state["looping"]: next_song()
                time.sleep(1)
        state["restart_flag"] = False

if __name__ == "__main__":
    main()
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

def run_track_mixer(full_path):
    minimize_game_window(); time.sleep(0.2)
    try: mid = mido.MidiFile(full_path)
    except: return
    tracks = get_track_info(mid)
    fname = os.path.basename(full_path)
    if fname in state["track_db"]:
        selected = set(state["track_db"][fname])
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
    state["track_db"][fname] = list(selected); save_track_db()
    state["manual_track_indices"] = list(selected); focus_game_window()

def run_selection_menu():
    minimize_game_window(); time.sleep(0.2)
    os.system('cls' if os.name == 'nt' else 'clear')
    subfolders = get_subfolders()
    print("="*50); print("       📂 PLAYLIST SELECTION"); print("="*50); print(f"[1]  🔥 ALL SONGS (Master)")
    for i, folder in enumerate(subfolders): print(f"[{i+2}]  📂 {folder}")
    try:
        user_input = input("\nSelect Folder # > ")
        if not user_input: return
        choice = int(user_input)
        new_playlist = []; folder_name = "ALL"
        if choice == 1: new_playlist = scan_files(None)
        elif 2 <= choice <= len(subfolders) + 1: folder_name = subfolders[choice - 2]; new_playlist = scan_files(folder_name)
        else: return
        if new_playlist:
            state["playlist"] = new_playlist; state["current_folder_name"] = folder_name; state["current_index"] = 0
            os.system('cls' if os.name == 'nt' else 'clear'); print(f"--- SONGS IN: {folder_name} ---")
            for i, full_path in enumerate(state["playlist"]): print(f"[{i+1}] {os.path.basename(full_path)}")
            si = input("\nStart Song # > ")
            if si.strip(): state["current_index"] = int(si) - 1
            state["resume_seek_seconds"] = 0.0 
    except: pass

def play_file(full_path):
    try: mid = mido.MidiFile(full_path)
    except: return
    ctypes.windll.kernel32.SetConsoleTitleW(f"Bard Bot - {os.path.basename(full_path)}")
    events_by_time = {}; tracks_to_play = []
    fname = os.path.basename(full_path)
    real_tracks_count = sum(1 for t in mid.tracks if sum(1 for m in t if m.type == 'note_on' and m.velocity > 0) > 0)

    if fname in state["track_db"]:
        saved_indices = state["track_db"][fname]
        for i in saved_indices:
            if i < len(mid.tracks): tracks_to_play.append(mid.tracks[i])
        track_source_name = "Saved Mix"
    else:
        best = 0; maxn = 0
        for i, t in enumerate(mid.tracks):
            c = sum(1 for m in t if m.type == 'note_on' and m.velocity > 0)
            if c > maxn: maxn, best = c, i
        tracks_to_play.append(mid.tracks[best])
        track_source_name = f"Auto (Track {best})"

    for track in tracks_to_play:
        curr = 0
        for msg in track:
            curr += msg.time
            if msg.type == 'note_on' and msg.velocity > 0:
                if curr not in events_by_time: events_by_time[curr] = []
                events_by_time[curr].append(msg.note)

    os.system('cls' if os.name == 'nt' else 'clear')
    print("="*80); print(f"🎵 NOW PLAYING: {os.path.basename(full_path)}")
    print(f"🎛️  Mixer: {track_source_name} | Active: {len(tracks_to_play)} / {real_tracks_count} Tracks"); print("="*80)
    print("\n\n"); print("="*80)
    print("⌨️  F3:Pause F4:Stop F5:Menu F6:Mute F7:Mixer L:Loop | PgUp/Dn: Seek | Arrows: Nav"); print("="*80)
    sys.stdout.write("\033[?25l"); sys.stdout.write("\033[5A") 

    sorted_times = sorted(events_by_time.keys())
    last_ticks = 0; tempo = mido.bpm2tempo(120)
    last_note_tick = sorted_times[-1] if sorted_times else 0
    total_duration = mido.tick2second(last_note_tick, mid.ticks_per_beat, tempo)
    accumulated_time = 0.0

    for t in sorted_times:
        if state["restart_flag"] or not state["running"]: break
        delta_ticks = t - last_ticks
        if delta_ticks > 0:
            real_wait = mido.tick2second(delta_ticks, mid.ticks_per_beat, tempo)
            accumulated_time += real_wait
            if accumulated_time < state["resume_seek_seconds"]:
                if int(accumulated_time * 100) % 5 == 0: update_dashboard(accumulated_time, total_duration, is_seeking=True)
                last_ticks = t; continue 

            if keyboard.is_pressed('page down'): state["resume_seek_seconds"] = min(accumulated_time + CONFIG["seek_step"], total_duration); return 
            if keyboard.is_pressed('page up'): state["resume_seek_seconds"] = max(accumulated_time - CONFIG["seek_step"], 0.0); return 

            handle_focus_state()
            start_wait = time.time()
            while True:
                while state["paused"]:
                    handle_focus_state(); update_dashboard(accumulated_time, total_duration); time.sleep(0.1)
                    if state["restart_flag"] or state["request_track_mixer"]: 
                        if state["request_track_mixer"]: state["resume_seek_seconds"] = accumulated_time
                        return
                    if keyboard.is_pressed('page down'): state["resume_seek_seconds"] = min(accumulated_time + CONFIG["seek_step"], total_duration); return
                    if keyboard.is_pressed('page up'): state["resume_seek_seconds"] = max(accumulated_time - CONFIG["seek_step"], 0.0); return

                elapsed = time.time() - start_wait
                target_wait = real_wait / state["playback_speed"]
                if elapsed >= target_wait: break
                if state["restart_flag"] or not state["running"]: break
                if state["request_track_mixer"]: state["resume_seek_seconds"] = accumulated_time; return
                if keyboard.is_pressed('page down'): state["resume_seek_seconds"] = min(accumulated_time + CONFIG["seek_step"], total_duration); return
                if keyboard.is_pressed('page up'): state["resume_seek_seconds"] = max(accumulated_time - CONFIG["seek_step"], 0.0); return
                handle_focus_state(); update_dashboard(accumulated_time, total_duration); time.sleep(0.01)

        if state["restart_flag"] or not state["running"]: break
        if state["request_track_mixer"]: state["resume_seek_seconds"] = accumulated_time; return

        for note in events_by_time[t]:
            if note in NOTE_MAP:
                if not state["muted"] and not state["muted_by_focus"]:
                    mod, key = NOTE_MAP[note]
                    press_atomic(mod, key)
                    if CONFIG["chord_strum_delay"] > 0: time.sleep(CONFIG["chord_strum_delay"])
        last_ticks = t
    
    sys.stdout.write("\033[?25h")
    if not state["restart_flag"]: state["resume_seek_seconds"] = 0.0

def main():
    os.system("") 
    load_track_db()
    state["playlist"] = scan_files(None)
    if not state["playlist"]: print(f"No files in '{CONFIG['midi_root']}'!"); return
    state["request_selection"] = True

    while state["running"]:
        if state["request_selection"]:
            run_selection_menu(); state["request_selection"] = False; state["restart_flag"] = False; state["playback_speed"] = 1.0; focus_game_window(); time.sleep(0.5)

        if state["request_track_mixer"]:
            run_track_mixer(state["playlist"][state["current_index"]]); state["request_track_mixer"] = False; state["restart_flag"] = False; focus_game_window(); time.sleep(0.5)

        if state["playlist"] and not state["request_selection"] and not state["request_track_mixer"]:
            play_file(state["playlist"][state["current_index"]])
            if not state["restart_flag"] and state["running"] and state["resume_seek_seconds"] == 0.0:
                if not state["looping"]: next_song()
                time.sleep(1)
        state["restart_flag"] = False

if __name__ == "__main__":
    main()