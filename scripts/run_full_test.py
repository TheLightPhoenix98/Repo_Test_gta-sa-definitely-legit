import os
import sys
import threading
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_REPO_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "gta-sa-definitely-legit"))

# just so wizard.py / player.py / resources.py can be imported as-is,
# nothing in that repo gets touched or modified
sys.path.insert(0, MAIN_REPO_DIR)
os.chdir(MAIN_REPO_DIR)

PLAY_WAIT_SECONDS = int(os.environ.get("PLAY_WAIT_SECONDS", "45"))

# hard ceiling on the whole script - wizard phase + play phase combined.
# if anything gets stuck for any reason (COM error, unfocused window
# eating the escape key, whatever) this kills the process outright so
# the CI job can never hang forever like it did last time
HARD_TIMEOUT_SECONDS = PLAY_WAIT_SECONDS + 90


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
        # progress page finishes and flips to FinishPage on its own,
        # just give it a bit of headroom
        app.after(5000, step_finish)

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
    import pyautogui

    def send_escape_later():
        time.sleep(PLAY_WAIT_SECONDS)
        # press it a few times a couple seconds apart in case the window
        # wasn't focused yet on the first attempt
        for _ in range(3):
            pyautogui.press("esc")
            time.sleep(2)

    threading.Thread(target=send_escape_later, daemon=True).start()

    from player import run_player
    run_player()


if __name__ == "__main__":
    start_watchdog()

    print("Phase 1: wizard")
    run_wizard_phase()

    print("Phase 2: play + roast")
    run_play_phase()

    print("Done")
    os._exit(0)
