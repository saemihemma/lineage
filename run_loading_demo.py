# run_loading_demo.py
from ui.screens.loading import LoadingScreen

def launch_main():
    print("Simulation starts…")

if __name__ == "__main__":
    LoadingScreen(on_enter=launch_main).mainloop()

