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
                          "Enter full path to your PalServer folder ( ex. C:\\Program Files(x86)\\Steam\\SteamApps\\common\\PalServer ): " + 
                          Style.RESET_ALL).strip()
    config['DEFAULT'] = {'palserver_dir': palserver_dir}
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)

config.read(CONFIG_FILE)
PALSERVER_DIR = Path(config['DEFAULT']['palserver_dir'])
SAVE_DIR = PALSERVER_DIR / "Pal" / "Saved" / "SaveGames" / "0"

# ---------- Determine active world ----------
GUS_FILE = PALSERVER_DIR / "Pal" / "Saved" / "Config" / "WindowsServer" / "GameUserSettings.ini"
ACTIVE_ID = None

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

# ---------- Functions ----------
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

def get_valid_index(prompt, max_val):
    """Ask user for a number between 1 and max_val. Returns a valid integer or None if invalid input."""
    try:
        num = int(input(Style.BRIGHT + prompt + Style.RESET_ALL))
        if 1 <= num <= max_val:
            return num
        else:
            print(Fore.YELLOW + "Number out of range!" + Style.RESET_ALL)
    except ValueError:
        print(Fore.YELLOW + "Invalid input! Please enter a number." + Style.RESET_ALL)
    return None

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
            idx = 1
            while (SAVE_DIR / f"world{idx}").exists():
                idx += 1
            (SAVE_DIR / ACTIVE_ID).rename(SAVE_DIR / f"world{idx}")
            (SAVE_DIR / sel_folder).rename(SAVE_DIR / ACTIVE_ID)
            print(Fore.GREEN + f"Activated world: {sel_name}" + Style.RESET_ALL)
            input(Fore.CYAN + "Press Enter to continue..." + Style.RESET_ALL)

        elif choice == "N":
            idx = 1
            while (SAVE_DIR / f"world{idx}").exists():
                idx += 1
            (SAVE_DIR / ACTIVE_ID).rename(SAVE_DIR / f"world{idx}")
            new_name = input(Style.BRIGHT + "Enter a name for the new world: " + Style.RESET_ALL).strip()
            if not new_name:
                new_name = f"New World {idx}"
            (SAVE_DIR / ACTIVE_ID).mkdir()
            (SAVE_DIR / ACTIVE_ID / "name.txt").write_text(new_name)
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

        elif choice == "L":
            server_exe = PALSERVER_DIR / "PalServer.exe"
            if server_exe.exists():
                print(Fore.CYAN + "Launching PalServer.exe..." + Style.RESET_ALL)
                subprocess.Popen([str(server_exe)], cwd=PALSERVER_DIR)
                input(Fore.CYAN + "Press Enter to return to menu..." + Style.RESET_ALL)
            else:
                print(Fore.RED + "PalServer.exe not found!" + Style.RESET_ALL)
                input(Fore.CYAN + "Press Enter to continue..." + Style.RESET_ALL)
    
    except KeyboardInterrupt:
        # When Ctrl+C is pressed, just return to menu
        print(Fore.CYAN + "\nReturning to menu..." + Style.RESET_ALL)
        time.sleep(1)
        continue