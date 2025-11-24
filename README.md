# MIDI Jukebox

This script plays MIDI files through keyboard emulation in a specified window.

## Setup

### 1. Install Python

If you don't have Python installed, download and install it from [python.org](https://www.python.org/downloads/). Make sure to check the box that says "Add Python to PATH" during installation.

### 2. Get the Code

You can either download the code as a ZIP file and extract it, or use Git to clone the repository:

```bash
git clone <repository_url>
cd midi_juke
```

### 3. Create a Virtual Environment

It's good practice to use a virtual environment to keep dependencies for different projects separate.

```bash
python -m venv .venv
```

Then, activate the virtual environment. On Windows:

```bash
.venv\Scripts\activate
```

### 4. Install Dependencies

Install the required Python packages using pip and the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

## Running the Jukebox

1.  Make sure you have your MIDI files in the `midis` directory.
2.  Activate the virtual environment if you haven't already:
    ```bash
    .venv\Scripts\activate
    ```
3.  Run the script:
    ```bash
    python jukebox.py
    ```
4.  The script will look for a window with the title "Where Winds Meet" by default. You can change this in the `CONFIG` section of `jukebox.py`.
5.  Use the on-screen controls to play, pause, and select songs.
