import os
os.environ["SDL_AUDIODRIVER"] = "dummy"
import random
import shutil
import subprocess
import sys
import threading
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_REPO_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "gta-sa-definitely-legit"))

# just so wizard.py / player.py / resources.py can be imported as-is,
# nothing in that repo gets touched or modified
sys.path.insert(0, MAIN_REPO_DIR)
os.chdir(MAIN_REPO_DIR)


NOTEPAD_PRANK_DELAY_SECONDS = 4
NOTEPAD_PRANK_TEXT = "Prank Like A Dev"


def _human_type(shell, text):
    for ch in text:
        shell.SendKeys(ch)
        time.sleep(random.uniform(0.09, 0.24))
        if random.random() < 0.12:
            time.sleep(random.uniform(0.15, 0.35))


def run_notepad_prank():
    try:
        import win32com.client
    except ImportError:
        print("pywin32 not available, skipping notepad prank")
        return

    notepad_path = shutil.which("notepad") or shutil.which("notepad.exe")
    if not notepad_path:
        print("notepad not found, skipping notepad prank")
        return

    try:
        subprocess.Popen([notepad_path])
    except Exception as e:
        print("Couldn't launch notepad:", e)
        return

    shell = win32com.client.Dispatch("WScript.Shell")
    time.sleep(1)
    try:
        shell.AppActivate("Notepad")
    except Exception:
        pass
    time.sleep(0.3)

    try:
        _human_type(shell, NOTEPAD_PRANK_TEXT)
    except Exception as e:
        print("Notepad typing failed:", e)


def get_video_duration_seconds():
    # read the actual intro video's length so PLAY_WAIT_SECONDS can never
    # be shorter than the video itself -- a hardcoded guess here is what
    # caused the window to force-close mid-video before the roast ever
    # got a chance to show
    import cv2
    from resources import VIDEO_PATH

    cap = cv2.VideoCapture(VIDEO_PATH)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    cap.release()
    return frame_count / fps if fps else 0


ROAST_BUFFER_SECONDS = 20  # how long to actually sit on the roast screen before closing

_env_value = os.environ.get("PLAY_WAIT_SECONDS")
if _env_value is not None:
    PLAY_WAIT_SECONDS = int(_env_value)
else:
    PLAY_WAIT_SECONDS = int(get_video_duration_seconds()) + ROAST_BUFFER_SECONDS

WIZARD_AND_PRANK_BUFFER = 75
HARD_TIMEOUT_SECONDS = PLAY_WAIT_SECONDS + WIZARD_AND_PRANK_BUFFER


def start_watchdog():
    def killer():
        time.sleep(HARD_TIMEOUT_SECONDS)
        print(f"Watchdog: nothing finished after {HARD_TIMEOUT_SECONDS}s, force-killing the process")
        sys.stdout.flush()
        os._exit(1)

    threading.Thread(target=killer, daemon=True).start()


def run_wizard_phase():
    from wizard import App

    app = App()

    # clicks through the existing wizard using the same methods the
    # buttons themselves call - nothing here is a special test hook,
    # it's all stuff that already exists in the installer
    step_delay = 1800

    def step_license():
        app.frames["WelcomePage"].go_next()
        app.after(step_delay, step_location)

    def step_location():
        license_page = app.frames["LicensePage"]
        license_page.agree_var.set(True)
        license_page.toggle_next()
        license_page.go_next()
        app.after(step_delay, step_components)

    def step_components():
        app.frames["LocationPage"].go_next()
        app.after(step_delay, step_progress)

    def step_progress():
        app.frames["ComponentsPage"].go_next()
        # the progress bar's own animation speed can change (it did --
        # we slowed it down for realism) so instead of guessing a fixed
        # wait here, poll until it actually reports 100% before moving on
        wait_for_progress_done()

    def wait_for_progress_done():
        progress_page = app.frames["ProgressPage"]
        if getattr(progress_page, "pct", 0) >= 100:
            app.after(800, step_finish)
        else:
            app.after(300, wait_for_progress_done)

    def step_finish():
        try:
            app.frames["FinishPage"].finish()
        except Exception as e:
            # if shortcut creation blows up (seen this happen with COM
            # on some CI images), don't let it strand the mainloop -
            # just log it and close the window ourselves
            print("finish() raised, closing anyway:", e)
            app.destroy()

    app.after(1000, step_license)
    app.mainloop()


def run_play_phase():
    import tkinter

    print(f"Play phase: waiting up to {PLAY_WAIT_SECONDS}s for video + roast", flush=True)

    # instead of trying to simulate a real OS-level ESC keypress (which
    # needs the window to actually have OS focus - unreliable on a CI
    # runner's session), we schedule the window to close itself via
    # Tkinter's own .after() timer. that runs on the same thread as
    # mainloop() so it always fires, focus or no focus.
    original_tk_init = tkinter.Tk.__init__

    def patched_init(self, *args, **kwargs):
        original_tk_init(self, *args, **kwargs)
        self.after(PLAY_WAIT_SECONDS * 1000, self.destroy)

    tkinter.Tk.__init__ = patched_init

    from player import run_player
    run_player()


if __name__ == "__main__":
    start_watchdog()

    print("Phase 1: wizard", flush=True)
    run_wizard_phase()

    print("Phase 2: play + roast", flush=True)
    run_play_phase()

    print("Phase 3: notepad prank", flush=True)
    time.sleep(NOTEPAD_PRANK_DELAY_SECONDS)
    run_notepad_prank()

    print("Done", flush=True)
    os._exit(0)
