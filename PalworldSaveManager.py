import os
import configparser
import subprocess
from pathlib import Path
from colorama import init, Fore, Style
import shutil
import time

init(autoreset=True)

CONFIG_FILE = "config.ini"

# ---------- First-time setup ----------
config = configparser.ConfigParser()
if not os.path.exists(CONFIG_FILE):
    palserver_dir = input(Fore.CYAN + Style.BRIGHT +
                          "Enter full path to your PalServer folder (ex. C:\\Program Files (x86)\\Steam\\SteamApps\\common\\PalServer): " +
                          Style.RESET_ALL).strip()
    config['DEFAULT'] = {'palserver_dir': palserver_dir}
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)

config.read(CONFIG_FILE)
PALSERVER_DIR = Path(config['DEFAULT']['palserver_dir'])
SAVE_DIR = PALSERVER_DIR / "Pal" / "Saved" / "SaveGames" / "0"

# Paths
GUS_FILE = PALSERVER_DIR / "Pal" / "Saved" / "Config" / "WindowsServer" / "GameUserSettings.ini"
WS_FILE = PALSERVER_DIR / "Pal" / "Saved" / "Config" / "WindowsServer" / "PalWorldSettings.ini"
DEFAULT_WS = PALSERVER_DIR / "DefaultPalWorldSettings.ini"
PAKS_DIR = PALSERVER_DIR / "Pal" / "Content" / "Paks"
BIN_DIR = PALSERVER_DIR / "Pal" / "Binaries" / "Win64"

ACTIVE_ID = None

# ---------- Determine active world ----------
if GUS_FILE.exists():
    with open(GUS_FILE, 'r') as f:
        inside_section = False
        for line in f:
            line = line.strip()
            if line == "[/Script/Pal.PalGameLocalSettings]":
                inside_section = True
            elif inside_section and line.startswith("DedicatedServerName="):
                ACTIVE_ID = line.split("=", 1)[1]
                break

if not ACTIVE_ID or not (SAVE_DIR / ACTIVE_ID).exists():
    ACTIVE_ID = input(Fore.YELLOW + Style.BRIGHT +
                      "Enter the active world folder name manually: " +
                      Style.RESET_ALL).strip()

TRASH_DIR = SAVE_DIR / "__trash__"
TRASH_DIR.mkdir(exist_ok=True)

# ---------- Utility Functions ----------
def list_worlds():
    worlds = []
    for d in SAVE_DIR.iterdir():
        if d.is_dir() and d.name != ACTIVE_ID and not d.name.startswith("__trash__"):
            name = (d / "name.txt").read_text().strip() if (d / "name.txt").exists() else d.name
            mod_time = d.stat().st_mtime
            worlds.append((d.name, name, mod_time))
    return worlds

def list_deleted():
    deleted = []
    for d in TRASH_DIR.iterdir():
        if d.is_dir():
            name_txt = d / "name.txt"
            friendly_name = name_txt.read_text().strip() if name_txt.exists() else d.name
            deleted.append((d.name, friendly_name))
    return deleted

def safe_rename(dest_dir, name):
    idx = 1
    new_name = name
    while (dest_dir / new_name).exists():
        new_name = f"{name}_{idx}"
        idx += 1
    return new_name

def get_next_world_name():
    idx = 1
    while (SAVE_DIR / f"world{idx}").exists():
        idx += 1
    return f"world{idx}"

def backup_current_world(world_id):
    """Save PalWorldSettings.ini + mods into current world folder and clear live dirs."""
    world_dir = SAVE_DIR / world_id
    mods_dir = world_dir / "Mods"
    mods_dir.mkdir(exist_ok=True)

    # Save PalWorldSettings.ini
    if DEFAULT_WS.exists():
        shutil.copy2(DEFAULT_WS, WS_FILE)
    else:
        WS_FILE.write_text("")  # empty file if default doesn't exist

    # Save ~mods and LogicMods
    for folder in ["~mods", "LogicMods"]:
        src = PAKS_DIR / folder
        dst = mods_dir / folder
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            shutil.rmtree(src)

    # Save UE4SS files
    for file in ["ue4ss", "dwmapi.dll"]:
        src = BIN_DIR / file
        if src.exists():
            dst = mods_dir / file
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                shutil.rmtree(src)
            else:
                shutil.copy2(src, dst)
                src.unlink()

def restore_world(world_id):
    """Restore PalWorldSettings.ini + mods from saved world folder into live dirs."""
    world_dir = SAVE_DIR / world_id
    mods_dir = world_dir / "Mods"

    # Restore PalWorldSettings.ini
    ws_src = world_dir / "PalWorldSettings.ini"
    if ws_src.exists():
        shutil.copy2(ws_src, WS_FILE)

    # Restore ~mods and LogicMods
    for folder in ["~mods", "LogicMods"]:
        src = mods_dir / folder
        dst = PAKS_DIR / folder
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

    # Restore UE4SS files
    for file in ["ue4ss", "dwmapi.dll"]:
        src = mods_dir / file
        dst = BIN_DIR / file
        if src.exists():
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

def copy_from_world_to_active(source_world_id, copy_settings=True, copy_mods=True):
    source_dir = SAVE_DIR / source_world_id
    active_dir = SAVE_DIR / ACTIVE_ID

    # ---------- Settings ----------
    if copy_settings:
        ws_src = source_dir / "PalWorldSettings.ini"
        if ws_src.exists():
            print(Fore.CYAN + f"Copying Settings from {source_world_id}..." + Style.RESET_ALL)
            shutil.copy2(ws_src, WS_FILE)  # overwrite WindowsServer PalWorldSettings.ini
            shutil.copy2(ws_src, active_dir / "PalWorldSettings.ini")  # overwrite active save folder
            print(Fore.GREEN + "Settings copied." + Style.RESET_ALL)

    # ---------- Mods ----------
    if copy_mods:
        mods_src = source_dir / "Mods"
        mods_dst = active_dir / "Mods"
        mods_dst.mkdir(exist_ok=True)

        # Copy ~mods and LogicMods
        for folder in ["~mods", "LogicMods"]:
            src = mods_src / folder
            dst = mods_dst / folder
            live_dst = PAKS_DIR / folder
            if src.exists():
                print(Fore.CYAN + f"Copying {folder}..." + Style.RESET_ALL)
                if dst.exists(): shutil.rmtree(dst)
                shutil.copytree(src, dst)
                if live_dst.exists(): shutil.rmtree(live_dst)
                shutil.copytree(src, live_dst)
                print(Fore.GREEN + f"{folder} copied." + Style.RESET_ALL)

        # Copy UE4SS files
        for file in ["ue4ss", "dwmapi.dll"]:
            src = mods_src / file
            dst = mods_dst / file
            live_dst = BIN_DIR / file
            if src.exists():
                print(Fore.CYAN + f"Copying {file}..." + Style.RESET_ALL)
                if src.is_dir():
                    if dst.exists(): shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                    if live_dst.exists(): shutil.rmtree(live_dst)
                    shutil.copytree(src, live_dst)
                else:
                    shutil.copy2(src, dst)
                    shutil.copy2(src, live_dst)
                print(Fore.GREEN + f"{file} copied." + Style.RESET_ALL)



# ---------- Main Loop ----------
while True:
    os.system('cls')
    # Header
    print(Fore.CYAN + Style.BRIGHT + "="*30)
    print(Fore.CYAN + Style.BRIGHT + "Palworld Save Manager")
    print(Fore.CYAN + Style.BRIGHT + "="*30 + Style.RESET_ALL)
    print()

    # List worlds
    worlds = list_worlds()
    if worlds:
        print(Fore.MAGENTA + Style.BRIGHT + "Available Worlds:" + Style.RESET_ALL)
        for i, (folder, name, mod) in enumerate(worlds, start=1):
            print(Fore.WHITE + f"{i}. {name}" + Style.RESET_ALL + f" (Folder: {folder})")
    else:
        print(Fore.YELLOW + Style.BRIGHT + "No other worlds available." + Style.RESET_ALL)

    # Active world info
    active_name = (SAVE_DIR / ACTIVE_ID / "name.txt").read_text().strip() if (SAVE_DIR / ACTIVE_ID / "name.txt").exists() else ACTIVE_ID
    print()
    print(Fore.GREEN + Style.BRIGHT + f"Current active world: {active_name} (Folder: {ACTIVE_ID})" + Style.RESET_ALL)
    print()

    # Menu options
    print(Style.BRIGHT + "[S]" + Style.RESET_ALL + " Switch World")
    print(Style.BRIGHT + "[N]" + Style.RESET_ALL + " New World")
    print(Style.BRIGHT + "[D]" + Style.RESET_ALL + " Delete World")
    print(Style.BRIGHT + "[U]" + Style.RESET_ALL + " Undo Delete")
    print(Style.BRIGHT + "[C]" + Style.RESET_ALL + " Clear Deleted Worlds")
    print(Style.BRIGHT + "[R]" + Style.RESET_ALL + " Rename World")
    print(Style.BRIGHT + "[L]" + Style.RESET_ALL + " Launch Server")
    print(Style.BRIGHT + "[P]" + Style.RESET_ALL + " Paste/Copy Settings and or Mods")
    print(Style.BRIGHT + "[Q]" + Style.RESET_ALL + " Quit")

    choice = input(Style.BRIGHT + "Enter choice: " + Style.RESET_ALL).strip().upper()

    try:
        if choice == "Q":
            break

        # ---------- Switch World ----------
        elif choice == "S":
            if not worlds:
                print(Fore.YELLOW + "No worlds available to switch!" + Style.RESET_ALL)
                input(Fore.CYAN + "Press Enter to continue..." + Style.RESET_ALL)
                continue

            while True:
                num = input(Style.BRIGHT + "Enter world number to activate: " + Style.RESET_ALL).strip()
                if not num.isdigit():
                    print(Fore.YELLOW + "Invalid input! Please enter a number." + Style.RESET_ALL)
                    continue
                num = int(num)
                if 1 <= num <= len(worlds):
                    break
                else:
                    print(Fore.YELLOW + "Number out of range!" + Style.RESET_ALL)

            sel_folder, sel_name, _ = worlds[num-1]

            backup_current_world(ACTIVE_ID)

            old_world_name = get_next_world_name()
            (SAVE_DIR / ACTIVE_ID).rename(SAVE_DIR / old_world_name)

            (SAVE_DIR / sel_folder).rename(SAVE_DIR / ACTIVE_ID)

            restore_world(ACTIVE_ID)

            print(Fore.GREEN + f"Activated world: {sel_name}" + Style.RESET_ALL)
            input(Fore.CYAN + "Press Enter to continue..." + Style.RESET_ALL)


        # ---------- New World ----------
        elif choice == "N":
            # Backup current
            backup_current_world(ACTIVE_ID)

            # Rename current active
            old_name = get_next_world_name()
            (SAVE_DIR / ACTIVE_ID).rename(SAVE_DIR / old_name)

            # Create new world
            new_name = input(Style.BRIGHT + "Enter a name for the new world: " + Style.RESET_ALL).strip()
            if not new_name:
                new_name = "New World"
            (SAVE_DIR / ACTIVE_ID).mkdir()
            (SAVE_DIR / ACTIVE_ID / "name.txt").write_text(new_name)

            # Copy default PalWorldSettings.ini
            if DEFAULT_WS.exists():
                shutil.copy2(DEFAULT_WS, SAVE_DIR / ACTIVE_ID / "PalWorldSettings.ini")
            else:
                # Just create empty if default doesn’t exist
                (SAVE_DIR / ACTIVE_ID / "PalWorldSettings.ini").write_text("")

            print(Fore.GREEN + f"New world created: {new_name}" + Style.RESET_ALL)
            input(Fore.CYAN + "Press Enter to continue..." + Style.RESET_ALL)

        # ---------- Delete World ----------
        elif choice == "D":
            if not worlds:
                print(Fore.YELLOW + "No worlds available to delete!" + Style.RESET_ALL)
                input(Fore.CYAN + "Press Enter to continue..." + Style.RESET_ALL)
                continue
            while True:
                num = input(Style.BRIGHT + "Enter world number to delete: " + Style.RESET_ALL).strip()
                if not num.isdigit():
                    print(Fore.YELLOW + "Invalid input! Please enter a number." + Style.RESET_ALL)
                    continue
                num = int(num)
                if 1 <= num <= len(worlds):
                    break
                else:
                    print(Fore.YELLOW + "Number out of range!" + Style.RESET_ALL)
            sel_folder, sel_name, _ = worlds[num-1]
            confirm = input(Fore.YELLOW + Style.BRIGHT + f"Are you sure you want to DELETE {sel_name}? (Y/N) " + Style.RESET_ALL).strip().upper()
            if confirm == "Y":
                timestamp = int(time.time())
                deleted_name = f"{sel_folder}_{timestamp}"
                shutil.move(SAVE_DIR / sel_folder, TRASH_DIR / deleted_name)
                print(Fore.GREEN + f"{sel_name} moved to trash." + Style.RESET_ALL)
                input(Fore.CYAN + "Press Enter to continue..." + Style.RESET_ALL)

        # ---------- Undo Delete ----------
        elif choice == "U":
            deleted = list_deleted()
            if not deleted:
                print(Fore.YELLOW + "No deleted worlds to undo!" + Style.RESET_ALL)
                input(Fore.CYAN + "Press Enter to continue..." + Style.RESET_ALL)
                continue
            print(Fore.MAGENTA + Style.BRIGHT + "Deleted worlds:" + Style.RESET_ALL)
            for i, (_, friendly_name) in enumerate(deleted, start=1):
                print(Fore.WHITE + f"{i}. {friendly_name}" + Style.RESET_ALL)
            while True:
                num = input(Style.BRIGHT + "Enter number to restore: " + Style.RESET_ALL).strip()
                if not num.isdigit():
                    print(Fore.YELLOW + "Invalid input! Please enter a number." + Style.RESET_ALL)
                    continue
                num = int(num)
                if 1 <= num <= len(deleted):
                    break
                else:
                    print(Fore.YELLOW + "Number out of range!" + Style.RESET_ALL)
            folder_name, friendly_name = deleted[num-1]
            restored_name = safe_rename(SAVE_DIR, friendly_name)
            shutil.move(TRASH_DIR / folder_name, SAVE_DIR / restored_name)
            print(Fore.GREEN + f"Restored world: {restored_name}" + Style.RESET_ALL)
            input(Fore.CYAN + "Press Enter to continue..." + Style.RESET_ALL)

        elif choice == "C":
            deleted = list_deleted()
            if not deleted:
                print(Fore.YELLOW + "Trash is already empty!" + Style.RESET_ALL)
                input(Fore.CYAN + "Press Enter to continue..." + Style.RESET_ALL)
                continue
            print(Fore.MAGENTA + Style.BRIGHT + "Deleted worlds to be permanently removed:" + Style.RESET_ALL)
            for _, friendly_name in deleted:
                print(Fore.WHITE + f"- {friendly_name}" + Style.RESET_ALL)
            confirm = input(Fore.RED + Style.BRIGHT + "YOU WILL LOSE THESE SERVERS FOREVER! CONTINUE? (Y/N) " + Style.RESET_ALL).strip().upper()
            if confirm == "Y":
                for d in TRASH_DIR.iterdir():
                    if d.is_dir():
                        shutil.rmtree(d)
                print(Fore.GREEN + "Deleted servers cleared permanently!" + Style.RESET_ALL)
                input(Fore.CYAN + "Press Enter to continue..." + Style.RESET_ALL)

        # ---------- Rename World ----------
        elif choice == "R":
            worlds_all = [(ACTIVE_ID, active_name)] + [(f, n) for f, n, _ in list_worlds()]
            print(Fore.MAGENTA + Style.BRIGHT + "Worlds:" + Style.RESET_ALL)
            for i, (folder, name) in enumerate(worlds_all, start=1):
                print(Fore.WHITE + f"{i}. {name}" + Style.RESET_ALL + f" (Folder: {folder})")
            while True:
                num = input(Style.BRIGHT + "Enter world number to rename: " + Style.RESET_ALL).strip()
                if not num.isdigit():
                    print(Fore.YELLOW + "Invalid input! Please enter a number." + Style.RESET_ALL)
                    continue
                num = int(num)
                if 1 <= num <= len(worlds_all):
                    break
                else:
                    print(Fore.YELLOW + "Number out of range!" + Style.RESET_ALL)
            folder, old_name = worlds_all[num-1]
            new_name = input(Style.BRIGHT + f"Enter new name for {old_name}: " + Style.RESET_ALL).strip()
            if new_name:
                (SAVE_DIR / folder / "name.txt").write_text(new_name)
                print(Fore.GREEN + f"World renamed: {new_name}" + Style.RESET_ALL)
            input(Fore.CYAN + "Press Enter to continue..." + Style.RESET_ALL)

        # ---------- Launch Server ----------
        elif choice == "L":
            server_exe = PALSERVER_DIR / "PalServer.exe"
            if server_exe.exists():
                print(Fore.CYAN + "Launching PalServer.exe..." + Style.RESET_ALL)
                subprocess.Popen([str(server_exe)], cwd=PALSERVER_DIR)
                input(Fore.CYAN + "Press Enter to return to menu..." + Style.RESET_ALL)
            else:
                print(Fore.RED + "PalServer.exe not found!" + Style.RESET_ALL)
                input(Fore.CYAN + "Press Enter to continue..." + Style.RESET_ALL)
                
        # ---------- Paste Settings/Mods ----------
        elif choice == "P":
            available_worlds = [(f, (SAVE_DIR / f / "name.txt").read_text().strip() 
                                 if (SAVE_DIR / f / "name.txt").exists() else f)
                                for f in os.listdir(SAVE_DIR)
                                if (SAVE_DIR / f).is_dir() and f != ACTIVE_ID and not f.startswith("__trash__")]
            if not available_worlds:
                print(Fore.YELLOW + "No other worlds available to copy from!" + Style.RESET_ALL)
                input(Fore.CYAN + "Press Enter to continue..." + Style.RESET_ALL)
                continue
            
            print(Fore.MAGENTA + Style.BRIGHT + "Available worlds to copy from:" + Style.RESET_ALL)
            for i, (_, name) in enumerate(available_worlds, start=1):
                print(Fore.WHITE + f"{i}. {name}" + Style.RESET_ALL)

            while True:
                num = input(Style.BRIGHT + "Enter world number to copy from: " + Style.RESET_ALL).strip()
                if not num.isdigit():
                    print(Fore.YELLOW + "Invalid input! Please enter a number." + Style.RESET_ALL)
                    continue
                num = int(num)
                if 1 <= num <= len(available_worlds):
                    break
                else:
                    print(Fore.YELLOW + "Number out of range!" + Style.RESET_ALL)

            selected_world_id, selected_world_name = available_worlds[num-1]

            # Ask what to copy
            while True:
                print(Style.BRIGHT + "[1] Settings only" + Style.RESET_ALL)
                print(Style.BRIGHT + "[2] Mods only" + Style.RESET_ALL)
                print(Style.BRIGHT + "[3] Both Settings and Mods" + Style.RESET_ALL)
                choice_copy = input(Style.BRIGHT + "Enter choice: " + Style.RESET_ALL).strip()
                if choice_copy in ["1","2","3"]:
                    break
                else:
                    print(Fore.YELLOW + "Invalid choice!" + Style.RESET_ALL)

            do_settings = choice_copy in ["1","3"]
            do_mods = choice_copy in ["2","3"]

            # Red warning
            print(Fore.RED + Style.BRIGHT + "\nWARNING: This will overwrite the active world's " +
                  ("settings " if do_settings else "") +
                  ("mods " if do_mods else "") +
                  "with the selected world. You may lose your current options!\n" + Style.RESET_ALL)
            confirm = input(Fore.RED + Style.BRIGHT + "Proceed? (Y/N): " + Style.RESET_ALL).strip().upper()
            if confirm != "Y":
                print(Fore.YELLOW + "Operation cancelled." + Style.RESET_ALL)
                input(Fore.CYAN + "Press Enter to continue..." + Style.RESET_ALL)
                continue
            
            # Perform copy
            copy_from_world_to_active(selected_world_id, copy_settings=do_settings, copy_mods=do_mods)
            print(Fore.GREEN + f"Copied from {selected_world_name} to active world." + Style.RESET_ALL)
            input(Fore.CYAN + "Press Enter to continue..." + Style.RESET_ALL)



    except KeyboardInterrupt:
        # When Ctrl+C is pressed, just return to menu
        print(Fore.CYAN + "\nReturning to menu..." + Style.RESET_ALL)
        time.sleep(1)
        continue
