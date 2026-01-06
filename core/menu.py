import logging
import tkinter as tk
from tkinter import messagebox
from utils.config_utils import (
    get_selected_game_mode, set_selected_game_mode,
    load_config, save_config
)
from utils.game_utils import get_champions_map
from core.constants import SUPPORTED_MODES

def show_menu(run_script_callback):
    root = tk.Tk()
    root.title("INTAI Menu")
    root.geometry("500x400")

    # --- Frames for each "page" ---
    menu_frame = tk.Frame(root)
    settings_frame = tk.Frame(root)
    gamemode_frame = tk.Frame(root)

    def show_frame(frame):
        frame.tkraise()
        root.update_idletasks()
        # Resize window to fit current frame
        width = frame.winfo_reqwidth() + 20
        height = frame.winfo_reqheight() + 20
        root.geometry(f"{width}x{height}")

    # --- MENU PAGE ---
    def run_script():
        root.destroy()
        run_script_callback()

    def change_gamemode():
        # Clear previous widgets in gamemode_frame
        for widget in gamemode_frame.winfo_children():
            widget.destroy()

        # Top left "Back to Menu" button
        top_frame = tk.Frame(gamemode_frame)
        top_frame.pack(fill="x", pady=(5, 0))
        tk.Button(top_frame, text="← Back to Menu", command=lambda: show_frame(menu_frame)).pack(side="left", padx=5)

        tk.Label(gamemode_frame, text="Select Game Mode:", font=("Arial", 14)).pack(pady=10)
        mode_var = tk.IntVar(value=0)
        mode_list = list(SUPPORTED_MODES.keys())
        for idx, mode in enumerate(mode_list):
            tk.Radiobutton(gamemode_frame, text=mode, variable=mode_var, value=idx).pack(anchor="w", padx=20)

        def set_mode():
            idx = mode_var.get()
            if 0 <= idx < len(mode_list):
                set_selected_game_mode(mode_list[idx])
                logging.info(f"Game mode set to '{mode_list[idx]}'.")
                refresh_menu()
                show_frame(menu_frame)
            else:
                messagebox.showwarning("Invalid Selection", "Please select a valid game mode.")

        tk.Button(gamemode_frame, text="Set Mode", command=set_mode).pack(pady=10)
        show_frame(gamemode_frame)


    def refresh_menu():
        selected_game_mode = get_selected_game_mode()
        game_mode_label.config(text=f"Current Game Mode: {selected_game_mode}")

    # --- SETTINGS PAGE ---
    def change_settings():
        config = load_config()
        keybinds = config.get("Keybinds", {})
        general = config.get("General", {})
        game_res = general.get("game_resolution", {})
        res_w = int(game_res.get("width", 1920))
        res_h = int(game_res.get("height", 1080))
        preferred_champion_obj = general.get("preferred_champion", {})

        champions_map = get_champions_map()  # {id: name}
        # Sort lexicographically by champion name and produce list of (name, id)
        sorted_entries = sorted(champions_map.items(), key=lambda kv: kv[1])  # [(id, name)...]
        champ_display = [("None", -1)] + [(name, cid) for cid, name in sorted_entries]

        # Determine initial selection
        if isinstance(preferred_champion_obj, dict):
            initial_name = preferred_champion_obj.get("name", "None")
        else:
            initial_name = "None"

        champ_var = tk.StringVar(value=initial_name if initial_name in [name for name, _ in champ_display] else "None")

        # Clear previous widgets in settings_frame
        for widget in settings_frame.winfo_children():
            widget.destroy()

        # Top left "Back to Menu" button
        top_frame = tk.Frame(settings_frame)
        top_frame.pack(fill="x", pady=(5, 0))
        tk.Button(top_frame, text="← Back to Menu", command=lambda: show_frame(menu_frame)).pack(side="left", padx=5)

        # Main horizontal frame
        main_frame = tk.Frame(settings_frame)
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # (Keybinds UI removed — keybinds are now managed via in-game LCU settings)

        # Right: Champion selection
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side="left", fill="y")

        tk.Label(right_frame, text="Preferred Champion:").pack(anchor="w", pady=(0, 5))
        listbox_frame = tk.Frame(right_frame)
        listbox_frame.pack(fill="y")

        champ_listbox = tk.Listbox(listbox_frame, height=15, exportselection=False)
        champ_listbox.pack(side="left", fill="y")

        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical", command=champ_listbox.yview)
        scrollbar.pack(side="left", fill="y")
        champ_listbox.config(yscrollcommand=scrollbar.set)

        for name, _ in champ_display:
            champ_listbox.insert(tk.END, name)
        # Set initial selection
        if champ_var.get() in [name for name, _ in champ_display]:
            champ_listbox.selection_set([name for name, _ in champ_display].index(champ_var.get()))
            champ_listbox.see([name for name, _ in champ_display].index(champ_var.get()))
        else:
            champ_listbox.selection_set(0)

        def on_champ_select(event):
            selection = champ_listbox.curselection()
            if selection:
                selected_name = champ_listbox.get(selection[0])
                champ_var.set(selected_name)

        champ_listbox.bind("<<ListboxSelect>>", on_champ_select)

        # Surrender option (True/False)
        surrender_var = tk.BooleanVar(value=general.get("surrender", False))
        surrender_frame = tk.Frame(right_frame)
        surrender_frame.pack(anchor="w", pady=(10, 0))
        tk.Label(surrender_frame, text="Surrender:").pack(side="left")
        surrender_checkbox = tk.Checkbutton(surrender_frame, variable=surrender_var)
        surrender_checkbox.pack(side="left", padx=5)

        # Game resolution input
        res_frame = tk.Frame(right_frame)
        res_frame.pack(anchor="w", pady=(10, 0))
        tk.Label(res_frame, text="Game Resolution:").grid(row=0, column=0, columnspan=4, sticky="w")
        tk.Label(res_frame, text="Width:").grid(row=1, column=0, sticky="e")
        width_var = tk.StringVar(value=str(res_w))
        width_entry = tk.Entry(res_frame, textvariable=width_var, width=7)
        width_entry.grid(row=1, column=1, padx=(4,10))
        tk.Label(res_frame, text="Height:").grid(row=1, column=2, sticky="e")
        height_var = tk.StringVar(value=str(res_h))
        height_entry = tk.Entry(res_frame, textvariable=height_var, width=7)
        height_entry.grid(row=1, column=3, padx=(4,0))

        def save_and_exit():
            config.setdefault("General", {})
            selected_name = champ_var.get()
            if selected_name == "None":
                config["General"]["preferred_champion"] = {}
            else:
                # Find the champion id for the selected name
                for name, cid in champ_display:
                    if name == selected_name:
                        config["General"]["preferred_champion"] = {"id": cid, "name": name}
                        break
            # Save surrender option
            config["General"]["surrender"] = surrender_var.get()
            # Save game resolution
            try:
                w = int(width_var.get())
                h = int(height_var.get())
                config.setdefault("General", {})
                config["General"]["game_resolution"] = {"width": w, "height": h}
            except Exception:
                # ignore invalid entries
                pass
            save_config(config)
            show_frame(menu_frame)

        # Reset to default removed: default config file no longer used

        # Buttons at the bottom (no "Back to Menu" here)
        btn_frame = tk.Frame(settings_frame)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Save", command=save_and_exit).pack(side="left", padx=5)

        settings_frame.update_idletasks()
        show_frame(settings_frame)

    # --- Build MENU FRAME ---
    menu_frame.place(relwidth=1, relheight=1)
    tk.Label(menu_frame, text="INTAI Menu", font=("Arial", 16)).pack(pady=10)
    game_mode_label = tk.Label(menu_frame, text=f"Current Game Mode: {get_selected_game_mode()}", font=("Arial", 12))
    game_mode_label.pack(pady=5)
    tk.Button(menu_frame, text="Run Script", width=20, command=run_script).pack(pady=5)
    tk.Button(menu_frame, text="Change Game Mode", width=20, command=change_gamemode).pack(pady=5)
    tk.Button(menu_frame, text="Change Settings", width=20, command=change_settings).pack(pady=5)
    tk.Button(menu_frame, text="Exit", width=20, command=root.destroy).pack(pady=10)

    # --- Build SETTINGS FRAME ---
    settings_frame.place(relwidth=1, relheight=1)
    # --- Build GAMEMODE FRAME ---
    gamemode_frame.place(relwidth=1, relheight=1)

    # --- Start with menu frame ---
    menu_frame.tkraise()

    root.mainloop()