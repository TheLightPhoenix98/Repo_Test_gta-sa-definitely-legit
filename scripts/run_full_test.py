import os
import sys
import threading
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_REPO_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "gta-sa-definitely-legit"))

sys.path.insert(0, MAIN_REPO_DIR)
os.chdir(MAIN_REPO_DIR)

PLAY_WAIT_SECONDS = int(os.environ.get("PLAY_WAIT_SECONDS", "45"))


def run_wizard_phase():
    from wizard import App

    app = App()

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
      
        app.after(5000, step_finish)

    def step_finish():
        app.frames["FinishPage"].finish()

    app.after(1000, step_license)
    app.mainloop()


def run_play_phase():
    import pyautogui

    def send_escape_later():
        time.sleep(PLAY_WAIT_SECONDS)
        pyautogui.press("esc")

    threading.Thread(target=send_escape_later, daemon=True).start()

    from player import run_player
    run_player()


if __name__ == "__main__":
    print("Phase 1: wizard")
    run_wizard_phase()

    print("Phase 2: play + roast")
    run_play_phase()

    print("Done")
