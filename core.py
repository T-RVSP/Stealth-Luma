import cloudscraper
import hashlib
import os
import re
import requests
import subprocess
import shutil
import json
import time
import sys
import logging
import tempfile

if sys.platform == "win32":
    import winreg
from contextlib import contextmanager
from bs4 import BeautifulSoup as parser
from requests.exceptions import ConnectionError, ConnectTimeout
from cloudscraper.exceptions import CloudflareException, CaptchaException

def _resolve_base_path():
    local = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
    if local:
        return os.path.abspath(os.path.join(local, "GLR_Manager"))
    return os.path.abspath(os.path.join(os.path.expanduser("~"), "GLR_Manager"))


BASE_PATH = _resolve_base_path()
PROFILES_PATH = os.path.join(BASE_PATH, "Profiles")
INSTALL_MANIFEST_PATH = os.path.join(BASE_PATH, "install_manifest.json")
STEAM_BACKUP_DIR = os.path.join(BASE_PATH, "steam_backup")
STEALTH_USER32_META_PATH = os.path.join(STEAM_BACKUP_DIR, "user32_meta.json")
STEALTH_SESSION_MARKER = os.path.join(BASE_PATH, "stealth_user32_active.json")
LOG_DIR = BASE_PATH


def get_log_path(filename):
    os.makedirs(LOG_DIR, exist_ok=True)
    return os.path.abspath(os.path.join(LOG_DIR, filename))


def setup_logging():
    handlers = [logging.StreamHandler()]
    try:
        handlers.insert(
            0,
            logging.FileHandler(get_log_path("errors.log"), mode="w", encoding="utf-8"),
        )
    except OSError:
        pass
    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(levelname)s] %(message)s",
        handlers=handlers,
        force=True,
    )
CURRENT_VERSION = "1.6.9"
APP_NAME = "Stealth Luma"
GITHUB_REPO = "T-RVSP/Stealth-Luma"
GITHUB_API_LATEST_RELEASE = "https://api.github.com/repos/{0}/releases/latest".format(GITHUB_REPO)
GITHUB_RELEASES_LATEST = "https://github.com/{0}/releases/latest".format(GITHUB_REPO)
SETUP_INSTALLER_PREFIX = "Stealth-Luma-Setup-"
APP_EXE_NAME = "Stealth Luma"
GLINJECT_DIR_NAME = "GLinject"
GLINJECT_EXTRACT_BLOCKED = False
GREENLUMA_DOWNLOAD_URL = "https://cs.rin.ru/forum/viewtopic.php?f=29&t=103709"
GREENLUMA_ZIP_PASSWORD = "cs.rin.ru"
STEALTH_DELETE_CACHE_EXE = "DeleteSteamAppCache.exe"
STEALTH_USER32_SOURCE = "user32SF.dll"
STEALTH_USER32_TARGET = "user32.dll"
STEALTH_APPLIST_MANAGER = "AppListManager.exe"
STEALTH_REQUIRED_FILES = (STEALTH_DELETE_CACHE_EXE, STEALTH_USER32_SOURCE)
APPLIST_MAX_ENTRIES = 168
STEAM_WAYBACK_CALENDAR_URL = "https://web.archive.org/web/20260000000000*/http://media.steampowered.com/client/"
DEFAULT_STEAM_DOWNGRADE_URL = (
    "https://web.archive.org/web/20260619061028if_/http://media.steampowered.com/client/"
)
DEFAULT_STEAM_VERSION_LABEL = "mer. 10 juin 2026"
STEAM_CFG_LINES = (
    "BootStrapperInhibitAll=Enable",
    "BootStrapperForceSelfUpdate=False",
)


def get_app_directory():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_glinject_path():
    if getattr(sys, "frozen", False):
        path = os.path.join(BASE_PATH, GLINJECT_DIR_NAME)
    else:
        path = os.path.join(get_app_directory(), GLINJECT_DIR_NAME)
    os.makedirs(path, exist_ok=True)
    return os.path.abspath(path)


def migrate_legacy_glinject():
    """Copie GLinject depuis l'ancien emplacement (Program Files) vers AppData."""
    if not getattr(sys, "frozen", False):
        return
    legacy = os.path.join(get_app_directory(), GLINJECT_DIR_NAME)
    dest = get_glinject_path()
    if os.path.normcase(legacy) == os.path.normcase(dest) or not os.path.isdir(legacy):
        return
    for name in os.listdir(legacy):
        src = os.path.join(legacy, name)
        if not os.path.isfile(src):
            continue
        dst = os.path.join(dest, name)
        if not os.path.isfile(dst) and _copy_stealth_file(src, dst):
            logging.info("Fichier mode furtif migré : %s", name)


def get_bundled_glinject_directory():
    """Dossier GLinject embarqué dans l'exécutable PyInstaller (_MEIPASS)."""
    if not getattr(sys, "frozen", False):
        return ""
    bundle_root = getattr(sys, "_MEIPASS", "")
    if not bundle_root:
        return ""
    bundled = os.path.join(bundle_root, GLINJECT_DIR_NAME)
    return bundled if os.path.isdir(bundled) else ""


def _is_defender_block_error(err):
    if getattr(err, "winerror", None) == 225:
        return True
    message = str(err).lower()
    return (
        "virus" in message
        or "indésirable" in message
        or "potentially unwanted" in message
    )


def _copy_stealth_file(src, dst):
    global GLINJECT_EXTRACT_BLOCKED
    try:
        shutil.copy2(src, dst)
        return True
    except OSError as err:
        if _is_defender_block_error(err):
            GLINJECT_EXTRACT_BLOCKED = True
            logging.error(
                "Extraction bloquée par l'antivirus Windows : %s (%s)",
                os.path.basename(dst),
                err,
            )
        else:
            logging.exception("Échec de copie mode furtif : %s -> %s", src, dst)
        return False


def glinject_extract_was_blocked():
    return GLINJECT_EXTRACT_BLOCKED


def extract_bundled_glinject(force=False):
    """Déploie les fichiers mode furtif embarqués vers GLinject/ (AppData si installé)."""
    global GLINJECT_EXTRACT_BLOCKED
    GLINJECT_EXTRACT_BLOCKED = False
    migrate_legacy_glinject()
    bundled = get_bundled_glinject_directory()
    if not bundled:
        return is_valid_greenluma_path(get_glinject_path())

    dest = get_glinject_path()
    os.makedirs(dest, exist_ok=True)
    extracted = False

    for name in os.listdir(bundled):
        src = os.path.join(bundled, name)
        if not os.path.isfile(src):
            continue
        dst = os.path.join(dest, name)
        if (
            force
            or not os.path.isfile(dst)
            or os.path.getsize(src) != os.path.getsize(dst)
        ):
            if _copy_stealth_file(src, dst):
                extracted = True

    if extracted:
        logging.info("Fichiers mode furtif extraits vers %s", dest)
    return is_valid_greenluma_path(dest)

class Game:
    def __init__(self, id, name, type):
        self.id = id.strip()
        self.name = name.strip()
        self.type = type.strip()

    def to_JSON(self):
        return {"id": self.id, "name": self.name, "type": self.type}

    def to_string(self):
        return "ID: {0}\nName: {1}\nType: {2}\n".format(self.id, self.name, self.type)

    def to_list(self):
        return [self.id, self.name, self.type]

    def __eq__(self, value):
        return self.id == value.id and self.name == value.name and self.type == value.type

    def __getitem__(self, index):
        values_list = list(vars(self).values())
        return values_list[index]

    @staticmethod
    def from_JSON(data):
        return Game(data["id"], data["name"], data["type"])

    @staticmethod
    def from_table_list(list):
        games = []
        for i in range(int(len(list) / 3)):
            games.append(Game(list[i * 3], list[i * 3 + 1], list[i * 3 + 2]))

        return games

class Profile:
    def __init__(
        self,
        name="default",
        games=None,
        steam_id="",
        source_app_id="",
        linked_game_profiles=None,
        excluded_game_profiles=None,
    ):
        self.name = name
        self.games = games if games is not None else []
        self.steam_id = str(steam_id or "")
        self.source_app_id = str(source_app_id or "")
        self.linked_game_profiles = list(linked_game_profiles or [])
        self.excluded_game_profiles = list(excluded_game_profiles or [])

    def add_game(self, game):
        self.games.append(game)

    def remove_game(self, game):
        if type(game) is Game:
            self.games.remove(game)
        else:
            for game_ in self.games:
                if game_.name == game:
                    self.games.remove(game_)
                    break

    def profile_filename(self):
        if self.steam_id:
            return "{0}.json".format(self.steam_id)
        safe_name = re.sub(r'[<>:"/\\|?*]', "_", self.name).strip() or "profile"
        return "{0}.json".format(safe_name)

    def profile_filepath(self, path=PROFILES_PATH):
        return os.path.join(path, self.profile_filename())

    def export_profile(self, path=PROFILES_PATH):
        data = {
            "name": self.name,
            "steam_id": self.steam_id,
            "source_app_id": self.source_app_id,
            "linked_game_profiles": list(self.linked_game_profiles),
            "excluded_game_profiles": list(self.excluded_game_profiles),
            "games": [game.to_JSON() for game in self.games],
        }
        with open(self.profile_filepath(path), "w", encoding="utf-8") as outfile:
            json.dump(data, outfile, indent=4, ensure_ascii=False)

    def __eq__(self, value):
        return self.name == value.name

    @staticmethod
    def from_JSON(data):
        return Profile(
            data.get("name", "default"),
            [Game.from_JSON(game) for game in data.get("games", [])],
            data.get("steam_id", ""),
            data.get("source_app_id", ""),
            data.get("linked_game_profiles", []),
            data.get("excluded_game_profiles", []),
        )

class ProfileManager:
    def __init__(self):
        self.profiles = {}
        self.load_profiles()

    def load_profiles(self):
        if not os.path.exists(PROFILES_PATH):
            os.makedirs(PROFILES_PATH)

        for filename in os.listdir(PROFILES_PATH):
            if os.path.splitext(filename)[1] != ".json":
                continue
            filepath = os.path.join(PROFILES_PATH, filename)
            with open(filepath, "r", encoding="utf-8") as file:
                try:
                    data = json.load(file)
                    self.register_profile(Profile.from_JSON(data))
                except (UnicodeDecodeError, json.JSONDecodeError) as e:
                    logging.exception(e)

    def register_profile(self, profile):
        self.profiles[profile.name] = profile

    def create_profile(self, name, games=None, steam_id="", source_app_id=""):
        if name == "" or name in self.profiles:
            return False

        self.register_profile(Profile(name, games, steam_id=steam_id, source_app_id=source_app_id))
        self.profiles[name].export_profile(PROFILES_PATH)
        return True

    def profile_exists(self, name):
        return name in self.profiles

    def unique_profile_name(self, desired):
        if desired not in self.profiles:
            return desired
        index = 2
        while True:
            candidate = "{0} ({1})".format(desired, index)
            if candidate not in self.profiles:
                return candidate
            index += 1

    def rename_profile(self, old_name, new_name):
        if not new_name or old_name == new_name or old_name not in self.profiles:
            return

        profile = self.profiles.pop(old_name)
        old_path = profile.profile_filepath(PROFILES_PATH)
        profile.name = new_name
        self.profiles[new_name] = profile
        profile.export_profile(PROFILES_PATH)

        if os.path.isfile(old_path) and os.path.normcase(old_path) != os.path.normcase(profile.profile_filepath(PROFILES_PATH)):
            try:
                os.remove(old_path)
            except OSError as err:
                logging.warning("Impossible de supprimer l'ancien profil %s : %s", old_path, err)

    def remove_profile(self, profile_name):
        if profile_name not in self.profiles:
            return

        profile = self.profiles.pop(profile_name)
        filepath = profile.profile_filepath(PROFILES_PATH)
        if os.path.isfile(filepath):
            os.remove(filepath)

class Config:
    def __init__(self, steam_path="", greenluma_path="", no_hook=False, version=CURRENT_VERSION, last_profile="default", check_update=True, use_steamdb=False, manager_msg=False, steam_downgrade_done=False, steam_downgrade_url="", language="fr"):
        self.steam_path = steam_path
        self.greenluma_path = greenluma_path
        self.no_hook = no_hook
        self.version = version
        self.last_profile = last_profile
        self.check_update = check_update
        self.use_steamdb = use_steamdb
        self.manager_msg = manager_msg
        self.steam_downgrade_done = steam_downgrade_done
        self.steam_downgrade_url = steam_downgrade_url
        self.language = language

    def export_config(self):
        with open("{}/config.json".format(BASE_PATH), "w") as outfile:
            json.dump(vars(self), outfile, indent=4)

    @staticmethod
    def from_JSON(data):
        config = Config()
        for key, value in data.items():
            if key in vars(config).keys():
                setattr(config, key, value)

        return config

    @staticmethod
    def load_config():
        if not os.path.isfile("{}/config.json".format(BASE_PATH)):
            if not os.path.exists(BASE_PATH):
                os.makedirs(BASE_PATH)

            config = Config()
            ensure_steam_path(config)
            ensure_greenluma_path(config)
            config.export_config()
            return config
        else:
            with open("{}/config.json".format(BASE_PATH), "r") as file_:
                try:
                    data = json.load(file_)
                    config = Config.from_JSON(data)
                except Exception as e:
                    logging.exception(e)
                    config = Config()

                config.no_hook = False
                config.version = CURRENT_VERSION
                if not hasattr(config, "language") or not config.language:
                    config.language = "fr"
                ensure_steam_path(config)
                ensure_greenluma_path(config)
                config.export_config()
                return config

class ConfigNotLoadedException(Exception):
    pass


def is_valid_steam_path(path):
    return bool(path) and os.path.isdir(path) and os.path.isfile(os.path.join(path, "Steam.exe"))


def is_valid_greenluma_path(path):
    """Vérifie que GLinject contient les fichiers du mode furtif (Steam Families)."""
    if not path or not os.path.isdir(path):
        return False
    return all(os.path.isfile(os.path.join(path, name)) for name in STEALTH_REQUIRED_FILES)


def find_greenluma_runtime_path(glinject_root=None, stealth=False):
    """Retourne le dossier GLinject contenant les fichiers mode furtif."""
    root = os.path.abspath(glinject_root or get_glinject_path())
    if is_valid_greenluma_path(root):
        return root
    return root


def greenluma_is_installed(stealth=False):
    return is_valid_greenluma_path(find_greenluma_runtime_path())


def extract_greenluma_archive(zip_path):
    """Extrait l'archive Stealth Luma dans GLinject/ avec le mot de passe cs.rin.ru."""
    import pyzipper

    zip_path = os.path.abspath(zip_path)
    if not os.path.isfile(zip_path):
        raise FileNotFoundError("Fichier ZIP introuvable.")

    dest = get_glinject_path()
    password = GREENLUMA_ZIP_PASSWORD.encode("utf-8")
    last_error = None

    for zip_cls in (pyzipper.AESZipFile, pyzipper.ZipFile):
        try:
            with zip_cls(zip_path) as archive:
                archive.pwd = password
                archive.extractall(dest)
            last_error = None
            break
        except Exception as err:
            last_error = err

    if last_error is not None:
        raise RuntimeError("Impossible d'extraire l'archive. Vérifiez le mot de passe et le fichier ZIP.") from last_error

    if not greenluma_is_installed():
        raise RuntimeError(
            "Archive extraite, mais les fichiers mode furtif sont introuvables dans GLinject "
            "(DeleteSteamAppCache.exe, user32SF.dll). "
            "Vérifiez que vous avez sélectionné la bonne archive {0} 2026.".format(APP_NAME)
        )

    logging.info("%s extrait dans %s", APP_NAME, dest)
    return dest


def _registry_steam_paths():
    if sys.platform != "win32":
        return []

    paths = []
    keys = (
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
    )
    value_names = ("InstallPath", "SteamPath")

    for hkey, subkey in keys:
        try:
            with winreg.OpenKey(hkey, subkey) as key:
                for name in value_names:
                    try:
                        value, _ = winreg.QueryValueEx(key, name)
                        if value:
                            paths.append(value.replace("/", os.sep))
                    except OSError:
                        pass
        except OSError:
            pass

    return paths


def _default_steam_paths():
    candidates = []
    for env_name in ("ProgramFiles(x86)", "ProgramFiles"):
        base = os.environ.get(env_name)
        if base:
            candidates.append(os.path.join(base, "Steam"))

    # Emplacements fréquents si les variables d'environnement sont absentes
    candidates.extend([
        r"C:\Program Files (x86)\Steam",
        r"C:\Program Files\Steam",
    ])
    return candidates


def _steam_from_running_process():
    try:
        import psutil
    except ImportError:
        return ""

    for process in psutil.process_iter(["exe"]):
        try:
            exe = process.info.get("exe")
            if exe and os.path.basename(exe).lower() == "steam.exe":
                return os.path.dirname(exe)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    return ""


def detect_steam_path():
    """Tente de localiser automatiquement l'installation Steam."""
    seen = set()
    candidates = []

    def add(path):
        if not path:
            return
        norm = os.path.normcase(os.path.abspath(path))
        if norm not in seen:
            seen.add(norm)
            candidates.append(os.path.abspath(path))

    for path in _registry_steam_paths():
        add(path)

    add(_steam_from_running_process())

    for path in _default_steam_paths():
        add(path)

    for path in candidates:
        if is_valid_steam_path(path):
            logging.info("Steam détecté automatiquement : %s", path)
            return path

    return ""


def _registry_steam_exe():
    if sys.platform != "win32":
        return ""

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            value, _ = winreg.QueryValueEx(key, "SteamExe")
            if value:
                path = os.path.abspath(value.replace("/", os.sep))
                if os.path.isfile(path):
                    return path
    except OSError:
        pass

    return ""


def get_steam_exe_path():
    global config
    if config and is_valid_steam_path(config.steam_path):
        return os.path.join(os.path.abspath(config.steam_path), "Steam.exe")

    registry_exe = _registry_steam_exe()
    if registry_exe:
        return registry_exe

    raise RuntimeError("Steam introuvable. Configurez le chemin Steam dans les paramètres.")


def get_steam_directory():
    return os.path.dirname(get_steam_exe_path())


def normalize_steam_downgrade_url(raw_url):
    """Transforme une URL Wayback en URL overridepackageurl valide pour Steam."""
    url = raw_url.strip()
    if not url:
        raise ValueError("Veuillez coller une URL Wayback Machine.")

    match = re.search(r"web\.archive\.org/web/(\d+)(?:if_)?/(.+)", url, re.IGNORECASE)
    if not match:
        raise ValueError(
            "URL Wayback invalide. Copiez le lien depuis le calendrier media.steampowered.com "
            "(clic droit sur l'heure → Copier l'adresse du lien)."
        )

    timestamp = match.group(1)
    original = match.group(2).strip().rstrip("/")
    if not original.startswith(("http://", "https://")):
        original = "https://{0}".format(original.lstrip("/"))

    return "http://web.archive.org/web/{0}if_/{1}".format(timestamp, original)


def get_target_steam_downgrade_url():
    return normalize_steam_downgrade_url(DEFAULT_STEAM_DOWNGRADE_URL)


def needs_steam_downgrade(config):
    steam_path = getattr(config, "steam_path", "") or ""
    if not is_valid_steam_path(steam_path):
        return False
    return not has_steam_cfg(steam_path)


def is_steam_running():
    try:
        import psutil
    except ImportError:
        return False

    targets = {"steam.exe", "steamservice.exe", "steamwebhelper.exe"}
    for process in psutil.process_iter(["name"]):
        try:
            name = (process.info.get("name") or "").lower()
            if name in targets:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    return False


def close_steam_for_downgrade(timeout=30):
    if not is_steam_running():
        return True

    try:
        steam_exe = get_steam_exe_path()
        steam_dir = get_steam_directory()
        subprocess.run([steam_exe, "-shutdown"], cwd=steam_dir, timeout=15)
    except Exception as err:
        logging.warning("Steam -shutdown a échoué : %s", err)

    deadline = time.time() + timeout
    while time.time() < deadline:
        if not is_steam_running():
            return True
        time.sleep(0.5)

    if sys.platform == "win32":
        for process_name in ("steam.exe", "SteamService.exe", "steamwebhelper.exe"):
            subprocess.run(
                ["taskkill", "/f", "/im", process_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        time.sleep(2)

    return not is_steam_running()


def write_steam_cfg(steam_dir=None):
    target_dir = steam_dir or get_steam_directory()
    cfg_path = os.path.join(target_dir, "steam.cfg")
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write("\n".join(STEAM_CFG_LINES) + "\n")
    logging.info("steam.cfg créé : %s", cfg_path)
    return cfg_path


def get_steam_cfg_path(steam_dir=None):
    target_dir = steam_dir or get_steam_directory()
    return os.path.join(target_dir, "steam.cfg")


def has_steam_cfg(steam_dir=None):
    return os.path.isfile(get_steam_cfg_path(steam_dir))


def remove_steam_cfg(steam_dir=None):
    cfg_path = get_steam_cfg_path(steam_dir)
    if os.path.isfile(cfg_path):
        os.remove(cfg_path)
        logging.info("steam.cfg supprimé : %s", cfg_path)
        return True
    return False


def perform_steam_downgrade(raw_url):
    package_url = normalize_steam_downgrade_url(raw_url)
    steam_exe = get_steam_exe_path()
    steam_dir = get_steam_directory()

    if not close_steam_for_downgrade():
        raise RuntimeError(
            "Impossible de fermer Steam. Fermez-le complètement (y compris la zone de notification) puis réessayez."
        )

    write_steam_cfg(steam_dir)
    subprocess.Popen(
        [
            steam_exe,
            "-forcesteamupdate",
            "-forcepackagedownload",
            "-overridepackageurl",
            package_url,
            "-exitsteam",
        ],
        cwd=steam_dir,
    )
    logging.info("Downgrade Steam lancé avec %s", package_url)
    return package_url


def perform_steam_restore():
    """Supprime les fichiers mode furtif, steam.cfg et force la mise à jour officielle."""
    steam_exe = get_steam_exe_path()
    steam_dir = get_steam_directory()

    if not close_steam_for_downgrade():
        raise RuntimeError(
            "Impossible de fermer Steam. Fermez-le complètement (y compris la zone de notification) puis réessayez."
        )

    remove_stealth_files_from_steam(steam_dir)
    remove_steam_cfg(steam_dir)
    subprocess.Popen(
        [
            steam_exe,
            "-forcesteamupdate",
            "-forcepackagedownload",
            "-exitsteam",
        ],
        cwd=steam_dir,
    )
    logging.info("Restauration Steam lancée (mise à jour officielle)")
    return True


def _parse_vdf_quoted_value(block, key):
    match = re.search(r'"{0}"\s+"((?:\\.|[^"\\])*)"'.format(re.escape(key)), block)
    if not match:
        return ""
    return match.group(1).replace('\\"', '"').replace("\\\\", "\\")


def get_steam_saved_accounts(steam_path):
    """Retourne les comptes Steam mémorisés (pseudo + identifiant) depuis loginusers.vdf."""
    if not is_valid_steam_path(steam_path):
        return []

    vdf_path = os.path.join(steam_path, "config", "loginusers.vdf")
    if not os.path.isfile(vdf_path):
        logging.info("loginusers.vdf introuvable : %s", vdf_path)
        return []

    try:
        with open(vdf_path, "r", encoding="utf-8", errors="ignore") as file_:
            content = file_.read()
    except OSError as err:
        logging.warning("Impossible de lire loginusers.vdf : %s", err)
        return []

    accounts = []
    seen_ids = set()
    for block_match in re.finditer(r'"(\d{17})"\s*\{', content):
        steam_id = block_match.group(1)
        if steam_id in seen_ids:
            continue

        start = block_match.end()
        depth = 1
        index = start
        while index < len(content) and depth > 0:
            char = content[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            index += 1

        block = content[start:index - 1]
        account_name = _parse_vdf_quoted_value(block, "AccountName")
        persona_name = _parse_vdf_quoted_value(block, "PersonaName")
        display_name = persona_name or account_name or steam_id
        most_recent = _parse_vdf_quoted_value(block, "MostRecent") == "1"

        accounts.append({
            "steam_id": steam_id,
            "account_name": account_name,
            "persona_name": display_name,
            "most_recent": most_recent,
        })
        seen_ids.add(steam_id)

    accounts.sort(key=lambda item: item["persona_name"].lower())
    logging.info("%d compte(s) Steam détecté(s)", len(accounts))
    return accounts


def get_default_steam_profile_name(profile_manager, steam_path):
    """Retourne le pseudo Steam à sélectionner au démarrage de l'application."""
    if not profile_manager:
        return ""

    accounts = get_steam_saved_accounts(steam_path)
    if accounts:
        ordered = [a for a in accounts if a.get("most_recent")] + [
            a for a in accounts if not a.get("most_recent")
        ]
        for account in ordered:
            persona_name = account["persona_name"]
            if persona_name in profile_manager.profiles:
                profile = profile_manager.profiles[persona_name]
                if is_steam_account_profile(profile):
                    return persona_name
            for profile in profile_manager.profiles.values():
                if profile.steam_id == account["steam_id"]:
                    return profile.name

    for profile in sorted(profile_manager.profiles.values(), key=lambda item: item.name.lower()):
        if is_steam_account_profile(profile):
            return profile.name

    return ""


PROFILE_SELECTOR_CHILD_PREFIX = "   "


def get_game_profiles_for_selector(profile_manager):
    game_profiles = [
        profile
        for profile in profile_manager.profiles.values()
        if is_game_profile(profile)
    ]
    game_profiles.sort(key=lambda item: item.name.lower())
    return game_profiles


def merge_linked_profile_games(steam_profile, profile_manager):
    """Fusionne les jeux/DLC des profils jeux liés (max 168 entrées)."""
    games = []
    seen_ids = set()
    for linked_name in getattr(steam_profile, "linked_game_profiles", []):
        child = profile_manager.profiles.get(linked_name)
        if not child or not is_game_profile(child):
            continue
        for game in child.games:
            if game.id in seen_ids:
                continue
            seen_ids.add(game.id)
            games.append(game)
            if len(games) >= APPLIST_MAX_ENTRIES:
                return games
    return games


def get_launch_games_for_profile(profile, profile_manager):
    if is_steam_account_profile(profile):
        return merge_linked_profile_games(profile, profile_manager)
    return list(profile.games)


def include_game_profile_in_steam(steam_profile, game_profile_name):
    """Réintègre un profil jeu au lancement Steam (retrait de la liste d'exclusion)."""
    excluded = getattr(steam_profile, "excluded_game_profiles", None)
    if excluded is None:
        steam_profile.excluded_game_profiles = []
        return
    if game_profile_name in steam_profile.excluded_game_profiles:
        steam_profile.excluded_game_profiles.remove(game_profile_name)


def exclude_game_profile_from_steam(steam_profile, game_profile_name):
    """Retire un profil jeu du lancement Steam et mémorise l'exclusion."""
    if not hasattr(steam_profile, "excluded_game_profiles"):
        steam_profile.excluded_game_profiles = []
    if game_profile_name not in steam_profile.excluded_game_profiles:
        steam_profile.excluded_game_profiles.append(game_profile_name)

    linked = getattr(steam_profile, "linked_game_profiles", [])
    if game_profile_name in linked:
        linked.remove(game_profile_name)


def ensure_steam_profile_links(profile_manager, steam_path):
    """Associe automatiquement les profils jeux au profil Steam principal."""
    steam_name = get_default_steam_profile_name(profile_manager, steam_path)
    if not steam_name or steam_name not in profile_manager.profiles:
        return False

    steam_profile = profile_manager.profiles[steam_name]
    if not is_steam_account_profile(steam_profile):
        return False

    if not hasattr(steam_profile, "linked_game_profiles"):
        steam_profile.linked_game_profiles = []
    if not hasattr(steam_profile, "excluded_game_profiles"):
        steam_profile.excluded_game_profiles = []

    valid_game_names = {
        child.name for child in get_game_profiles_for_selector(profile_manager)
    }
    changed = False

    linked = getattr(steam_profile, "linked_game_profiles", [])
    pruned_linked = [name for name in linked if name in valid_game_names]
    if pruned_linked != linked:
        steam_profile.linked_game_profiles = pruned_linked
        changed = True

    excluded = getattr(steam_profile, "excluded_game_profiles", [])
    pruned_excluded = [name for name in excluded if name in valid_game_names]
    if pruned_excluded != excluded:
        steam_profile.excluded_game_profiles = pruned_excluded
        changed = True

    excluded = set(steam_profile.excluded_game_profiles)
    for child in get_game_profiles_for_selector(profile_manager):
        if child.name in excluded:
            continue
        if child.name not in steam_profile.linked_game_profiles:
            steam_profile.linked_game_profiles.append(child.name)
            changed = True

    steam_profile.linked_game_profiles.sort(key=str.lower)
    if changed:
        steam_profile.export_profile(PROFILES_PATH)
    return changed


def refresh_steam_launch_profiles(profile_manager, steam_path, steam_profile):
    """Synchronise les profils installés, réintègre les profils retirés, recharge les DLC."""
    if not is_valid_steam_path(steam_path) or not is_steam_account_profile(steam_profile):
        return {"linked": 0, "reloaded": 0, "errors": []}

    steam_profile.excluded_game_profiles = []
    sync_installed_game_profiles(profile_manager, steam_path, load_dlc=False)
    ensure_steam_profile_links(profile_manager, steam_path)

    reloaded = 0
    errors = []
    for linked_name in list(getattr(steam_profile, "linked_game_profiles", [])):
        child = profile_manager.profiles.get(linked_name)
        if not child:
            continue
        main_game = get_profile_main_game(child, steam_path)
        if not main_game:
            continue
        try:
            configuration = build_game_configuration(steam_path, main_game.id, main_game.name)
            apply_game_configuration(child, configuration)
            reloaded += 1
        except Exception as err:
            logging.exception("Impossible de recharger %s : %s", linked_name, err)
            errors.append(linked_name)

    steam_profile.export_profile(PROFILES_PATH)
    return {
        "linked": len(getattr(steam_profile, "linked_game_profiles", [])),
        "reloaded": reloaded,
        "errors": errors,
    }


def remove_game_profile_from_steam_links(profile_manager, game_profile_name):
    """Retire un profil jeu des listes liées des profils Steam."""
    changed = False
    for profile in profile_manager.profiles.values():
        if not is_steam_account_profile(profile):
            continue
        linked = getattr(profile, "linked_game_profiles", [])
        if game_profile_name in linked:
            linked.remove(game_profile_name)
            profile.export_profile(PROFILES_PATH)
            changed = True
    return changed


def get_ordered_profile_names(profile_manager, steam_path=""):
    """Pseudo Steam en tête, puis profils jeux par ordre alphabétique."""
    if not profile_manager:
        return []

    steam_profiles = []
    game_profiles = []
    for profile in profile_manager.profiles.values():
        if is_steam_account_profile(profile):
            steam_profiles.append(profile)
        else:
            game_profiles.append(profile)

    default_steam = get_default_steam_profile_name(profile_manager, steam_path)
    steam_profiles.sort(
        key=lambda item: (item.name != default_steam, item.name.lower())
    )
    game_profiles.sort(key=lambda item: item.name.lower())
    return [profile.name for profile in steam_profiles + game_profiles]


def sync_profiles_from_steam(profile_manager, steam_path, last_profile=""):
    """Synchronise les profils locaux avec les comptes enregistrés sur Steam."""
    accounts = get_steam_saved_accounts(steam_path)
    if not accounts:
        return False, {}

    renamed = {}
    by_steam_id = {}
    for profile in profile_manager.profiles.values():
        if profile.steam_id:
            by_steam_id[profile.steam_id] = profile

    active_ids = set()
    for account in accounts:
        steam_id = account["steam_id"]
        persona_name = account["persona_name"]
        active_ids.add(steam_id)

        if steam_id in by_steam_id:
            profile = by_steam_id[steam_id]
            if profile.name != persona_name:
                old_name = profile.name
                profile_manager.rename_profile(old_name, persona_name)
                renamed[old_name] = persona_name
                profile = profile_manager.profiles[persona_name]
            profile.steam_id = steam_id
            profile.export_profile(PROFILES_PATH)
            continue

        if persona_name in profile_manager.profiles:
            profile = profile_manager.profiles[persona_name]
            legacy_path = profile.profile_filepath(PROFILES_PATH)
            profile.steam_id = steam_id
            profile.export_profile(PROFILES_PATH)
            if os.path.isfile(legacy_path) and os.path.normcase(legacy_path) != os.path.normcase(profile.profile_filepath(PROFILES_PATH)):
                try:
                    os.remove(legacy_path)
                except OSError as err:
                    logging.warning("Impossible de supprimer l'ancien profil %s : %s", legacy_path, err)
            by_steam_id[steam_id] = profile
            continue

        profile_manager.create_profile(persona_name, games=[], steam_id=steam_id)
        by_steam_id[steam_id] = profile_manager.profiles[persona_name]

    for profile_name, profile in list(profile_manager.profiles.items()):
        if profile.steam_id and profile.steam_id in active_ids:
            if not hasattr(profile, "linked_game_profiles"):
                profile.linked_game_profiles = []
            if not hasattr(profile, "excluded_game_profiles"):
                profile.excluded_game_profiles = []
            continue

    for profile_name, profile in list(profile_manager.profiles.items()):
        if profile.steam_id and profile.steam_id not in active_ids:
            profile_manager.remove_profile(profile_name)
        elif profile_name == "default" and not profile.steam_id and not profile.games:
            profile_manager.remove_profile(profile_name)

    return True, renamed


def collect_existing_game_ids(profile_manager):
    seen = set()
    for profile in profile_manager.profiles.values():
        for game in profile.games:
            seen.add(game.id)
    return seen


def import_games_into_profiles(profile_manager, games, start_profile_name, steam_id=""):
    """Répartit les jeux sur un ou plusieurs profils (max APPLIST_MAX_ENTRIES chacun)."""
    if not games or start_profile_name not in profile_manager.profiles:
        return {}

    existing_ids = collect_existing_game_ids(profile_manager)
    new_games = [game for game in games if game.id not in existing_ids]
    if not new_games:
        return {}

    results = {}
    remaining = new_games[:]
    base_name = start_profile_name.split(" (")[0]

    def fill_profile(profile_name, steam_account_id=""):
        nonlocal remaining
        if not remaining:
            return

        if profile_name not in profile_manager.profiles:
            profile_manager.create_profile(profile_name, steam_id=steam_account_id)

        profile = profile_manager.profiles[profile_name]
        space = APPLIST_MAX_ENTRIES - len(profile.games)
        if space <= 0:
            return

        chunk = remaining[:space]
        remaining = remaining[space:]
        for game in chunk:
            if game not in profile.games:
                profile.add_game(game)
        profile.export_profile(PROFILES_PATH)
        results[profile_name] = results.get(profile_name, 0) + len(chunk)

    fill_profile(start_profile_name, steam_id)
    part = 2
    while remaining:
        suffix_name = profile_manager.unique_profile_name("{0} ({1})".format(base_name, part))
        fill_profile(suffix_name)
        part += 1

    return results


def profile_exceeds_applist_limit(profile, profile_manager=None):
    if is_steam_account_profile(profile) and profile_manager is not None:
        return len(merge_linked_profile_games(profile, profile_manager)) > APPLIST_MAX_ENTRIES
    return bool(profile) and len(profile.games) > APPLIST_MAX_ENTRIES


def remove_uninstalled_game_profiles(profile_manager, steam_path):
    """Supprime les profils auto-créés dont le jeu n'est plus installé."""
    if not is_valid_steam_path(steam_path):
        return []

    installed_ids = set(scan_installed_steam_apps(steam_path).keys())
    removed = []
    for profile_name, profile in list(profile_manager.profiles.items()):
        if is_steam_account_profile(profile):
            continue
        if not profile.source_app_id:
            continue
        if str(profile.source_app_id) in installed_ids:
            continue
        profile_manager.remove_profile(profile_name)
        remove_game_profile_from_steam_links(profile_manager, profile_name)
        removed.append(profile_name)

    removed.sort(key=str.lower)
    return removed


def sync_installed_game_profiles(profile_manager, steam_path, load_dlc=False):
    """Crée ou retire les profils liés aux jeux installés sur Steam."""
    if not is_valid_steam_path(steam_path):
        return {"created": [], "removed": []}

    removed = remove_uninstalled_game_profiles(profile_manager, steam_path)
    created = []
    for game in get_installed_base_games(steam_path):
        if find_game_profile(profile_manager, game) or profile_manager.profile_exists(game.name):
            continue
        if not profile_manager.create_profile(game.name, games=[game], source_app_id=game.id):
            continue
        created.append(game)
        if load_dlc:
            try:
                configuration = build_game_configuration(steam_path, game.id, game.name)
                apply_game_configuration(profile_manager.profiles[game.name], configuration)
            except Exception as err:
                logging.exception("Impossible de charger la configuration de %s : %s", game.name, err)

    return {"created": created, "removed": removed}


def is_steam_account_profile(profile):
    return bool(profile and profile.steam_id)


def is_game_profile(profile):
    return bool(profile) and not profile.steam_id


def is_installed_game_profile(profile, steam_path=None):
    """Profil lié à un jeu installé (créé automatiquement)."""
    if not profile or not profile.source_app_id:
        return False
    path = steam_path or ""
    if is_valid_steam_path(path):
        return str(profile.source_app_id) in scan_installed_steam_apps(path)
    return True


def can_delete_profile(profile, steam_path=None):
    if not is_game_profile(profile):
        return False
    return not is_installed_game_profile(profile, steam_path)


def get_installed_base_games(steam_path):
    """Jeux installés (sans DLC) pour la création de profils."""
    if not is_valid_steam_path(steam_path):
        return []

    installed = scan_installed_steam_apps(steam_path)
    if not installed:
        return []

    cache = _load_steam_app_cache()
    games = []
    for appid, manifest_name in installed.items():
        if _should_skip_steam_app(appid, manifest_name):
            continue

        metadata = get_steam_app_metadata(appid, cache, include_dlc_list=False)
        if metadata.get("type") == "dlc":
            continue
        if metadata.get("type") not in ("game", "demo", "beta"):
            continue

        name = manifest_name or metadata.get("name") or appid
        games.append(Game(appid, name, "Game"))

    _save_steam_app_cache(cache)
    games.sort(key=lambda item: item.name.lower())
    return games


def find_game_profile(profile_manager, game):
    if not game:
        return None

    for profile in profile_manager.profiles.values():
        if is_steam_account_profile(profile):
            continue
        if profile.source_app_id and profile.source_app_id == str(game.id):
            return profile
        if profile.name == game.name:
            return profile

    return None


def get_profile_main_game(profile, steam_path=None):
    if not profile:
        return None

    for game in profile.games:
        if game.type == "Game":
            return game

    if profile.source_app_id:
        return Game(profile.source_app_id, profile.name, "Game")

    if steam_path and is_valid_steam_path(steam_path):
        installed = scan_installed_steam_apps(steam_path)
        if profile.name in installed.values():
            for appid, name in installed.items():
                if name == profile.name:
                    return Game(appid, name, "Game")

    return None


def build_game_configuration(steam_path, app_id, game_name):
    """Construit la configuration complète (jeu + DLC) pour un titre installé."""
    installed = scan_installed_steam_apps(steam_path)
    cache = _load_steam_app_cache()
    main_game = Game(str(app_id), game_name, "Game")
    result = [main_game]
    seen_ids = {main_game.id}

    dlcs = fetch_game_dlcs(app_id, game_name)
    metadata = get_steam_app_metadata(app_id, cache)

    if not dlcs:
        for dlc_id in metadata.get("dlc", []):
            dlc_id = str(dlc_id)
            if dlc_id in seen_ids:
                continue
            dlc_name = resolve_steam_app_name(dlc_id, cache, installed)
            dlcs.append(Game(dlc_id, dlc_name, "DLC"))

    _cache_dlc_names(dlcs, cache)
    for dlc in dlcs:
        if dlc.id not in seen_ids:
            result.append(dlc)
            seen_ids.add(dlc.id)

    _save_steam_app_cache(cache)
    return result


def apply_game_configuration(profile, configuration):
    """Applique une configuration jeu/DLC à un profil (limite AppList incluse)."""
    total = len(configuration)
    profile.games = configuration[:APPLIST_MAX_ENTRIES]
    profile.export_profile(PROFILES_PATH)
    return total, len(profile.games)


def ensure_steam_path(config):
    if is_valid_steam_path(config.steam_path):
        config.steam_path = os.path.abspath(config.steam_path)
        return True

    detected = detect_steam_path()
    if detected:
        config.steam_path = detected
        return True

    return False


def ensure_greenluma_path(config):
    config.no_hook = False
    extract_bundled_glinject()
    glinject = get_glinject_path()
    runtime = find_greenluma_runtime_path(glinject)
    config.greenluma_path = runtime

    if is_valid_greenluma_path(runtime):
        logging.info("%s (mode furtif) trouvé dans GLinject : %s", APP_NAME, runtime)
    else:
        logging.info(
            "Dossier GLinject prêt : %s - fichiers mode furtif manquants (DeleteSteamAppCache.exe, user32SF.dll)",
            glinject,
        )

    return True


def get_steam_applist_path(steam_dir=None):
    target_dir = steam_dir or get_steam_directory()
    return os.path.join(target_dir, "AppList")


def run_delete_steam_app_cache(glinject_path=None):
    """Étape 1 du mode furtif : purge le cache applicatif Steam."""
    glinject = os.path.abspath(glinject_path or get_glinject_path())
    exe_path = os.path.join(glinject, STEALTH_DELETE_CACHE_EXE)
    if not os.path.isfile(exe_path):
        raise FileNotFoundError(
            "{0} introuvable dans GLinject.".format(STEALTH_DELETE_CACHE_EXE)
        )
    subprocess.run([exe_path], cwd=glinject, check=True)
    logging.info("DeleteSteamAppCache.exe exécuté")


def _steam_user32_backup_path():
    return os.path.join(STEAM_BACKUP_DIR, "user32.dll.bak")


def _file_digest(path):
    digest = hashlib.md5()
    with open(path, "rb") as file_:
        for chunk in iter(lambda: file_.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _get_injected_user32_source():
    return os.path.join(get_glinject_path(), STEALTH_USER32_SOURCE)


def is_steam_user32_injected(steam_dir=None, user32_path=None):
    """True si user32.dll Steam est la copie injectée (user32SF.dll)."""
    steam_dir = steam_dir or get_steam_directory()
    user32_path = user32_path or os.path.join(steam_dir, STEALTH_USER32_TARGET)
    injected_src = _get_injected_user32_source()
    if not os.path.isfile(user32_path) or not os.path.isfile(injected_src):
        return False
    try:
        return _file_digest(user32_path) == _file_digest(injected_src)
    except OSError:
        return False


def _backup_is_valid_original(backup_path):
    if not os.path.isfile(backup_path):
        return False
    injected_src = _get_injected_user32_source()
    if not os.path.isfile(injected_src):
        return True
    try:
        return _file_digest(backup_path) != _file_digest(injected_src)
    except OSError:
        return False


def _load_steam_user32_meta():
    if not os.path.isfile(STEALTH_USER32_META_PATH):
        return {}
    try:
        with open(STEALTH_USER32_META_PATH, "r", encoding="utf-8") as file_:
            return json.load(file_)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_steam_user32_meta(meta):
    os.makedirs(STEAM_BACKUP_DIR, exist_ok=True)
    with open(STEALTH_USER32_META_PATH, "w", encoding="utf-8") as file_:
        json.dump(meta, file_)


def mark_stealth_user32_deployed(steam_dir):
    os.makedirs(BASE_PATH, exist_ok=True)
    with open(STEALTH_SESSION_MARKER, "w", encoding="utf-8") as file_:
        json.dump({"steam_path": os.path.abspath(steam_dir)}, file_)


def clear_stealth_user32_marker():
    if os.path.isfile(STEALTH_SESSION_MARKER):
        os.remove(STEALTH_SESSION_MARKER)


def stealth_user32_needs_restore(steam_dir=None):
    if os.path.isfile(STEALTH_SESSION_MARKER):
        return True
    steam_dir = steam_dir or get_steam_directory()
    if not steam_dir:
        return False
    return is_steam_user32_injected(steam_dir)


def backup_steam_user32(steam_dir=None):
    """Sauvegarde user32.dll Steam avant toute modification par Stealth Luma."""
    steam_dir = steam_dir or get_steam_directory()
    if not steam_dir or not os.path.isdir(steam_dir):
        return False

    user32_path = os.path.join(steam_dir, STEALTH_USER32_TARGET)
    backup_path = _steam_user32_backup_path()
    meta = _load_steam_user32_meta()

    if not os.path.isfile(user32_path):
        if "had_original" not in meta:
            meta["had_original"] = False
            _save_steam_user32_meta(meta)
        return False

    if is_steam_user32_injected(steam_dir, user32_path):
        if os.path.isfile(backup_path) and _backup_is_valid_original(backup_path):
            return True
        logging.warning(
            "user32.dll Steam déjà injecté, sauvegarde ignorée pour ne pas écraser l'original"
        )
        return bool(os.path.isfile(backup_path) and _backup_is_valid_original(backup_path))

    if not os.path.isfile(backup_path):
        os.makedirs(STEAM_BACKUP_DIR, exist_ok=True)
        shutil.copy2(user32_path, backup_path)
        logging.info("Sauvegarde Steam : %s -> %s", user32_path, backup_path)

    meta["had_original"] = True
    _save_steam_user32_meta(meta)
    return True


def write_install_manifest(install_dir, language, steam_path=""):
    os.makedirs(BASE_PATH, exist_ok=True)
    manifest = {
        "install_dir": os.path.abspath(install_dir),
        "language": language,
        "steam_path": os.path.abspath(steam_path) if steam_path else "",
        "version": CURRENT_VERSION,
    }
    with open(INSTALL_MANIFEST_PATH, "w", encoding="utf-8") as file_:
        json.dump(manifest, file_, indent=4)
    return manifest


def load_install_manifest():
    if not os.path.isfile(INSTALL_MANIFEST_PATH):
        return {}
    try:
        with open(INSTALL_MANIFEST_PATH, "r", encoding="utf-8") as file_:
            return json.load(file_)
    except (OSError, json.JSONDecodeError) as err:
        logging.exception(err)
        return {}


def create_initial_config(language, install_dir=None):
    os.makedirs(BASE_PATH, exist_ok=True)
    config = Config(language=language, version=CURRENT_VERSION, manager_msg=True)
    ensure_steam_path(config)
    if install_dir:
        runtime = find_greenluma_runtime_path(os.path.join(install_dir, GLINJECT_DIR_NAME))
        if is_valid_greenluma_path(runtime):
            config.greenluma_path = runtime
    else:
        ensure_greenluma_path(config)
    config.export_config()
    if is_valid_steam_path(config.steam_path):
        backup_steam_user32(config.steam_path)
    return config


def run_install_setup(language, install_dir):
    """Configuration initiale après installation (langue, manifeste, sauvegarde Steam)."""
    install_dir = os.path.abspath(install_dir)
    manifest = load_install_manifest()
    config_path = os.path.join(BASE_PATH, "config.json")
    if (
        manifest.get("install_dir") == install_dir
        and manifest.get("language") == language
        and manifest.get("version") == CURRENT_VERSION
        and os.path.isfile(config_path)
    ):
        logging.info("Configuration initiale déjà effectuée")
        return 0
    config = create_initial_config(language, install_dir=install_dir)
    write_install_manifest(
        install_dir,
        language,
        steam_path=config.steam_path,
    )
    logging.info("Configuration initiale terminée (%s)", language)
    return 0


def run_uninstall_restore():
    """Restaure Steam avant suppression des fichiers (appelé par le désinstallateur Inno)."""
    manifest = load_install_manifest()
    steam_path = manifest.get("steam_path") or ""
    restore_steam_after_uninstall(steam_dir=steam_path or None)
    logging.info("Restauration Steam terminée")
    return 0


def restore_steam_user32(steam_dir=None, restart_steam=False):
    """Restaure ou supprime user32.dll injecté dans le dossier Steam."""
    steam_dir = steam_dir or get_steam_directory()
    if not steam_dir or not os.path.isdir(steam_dir):
        logging.warning("Restauration user32 ignorée : chemin Steam introuvable")
        return False

    user32_dst = os.path.join(steam_dir, STEALTH_USER32_TARGET)
    backup_path = _steam_user32_backup_path()
    meta = _load_steam_user32_meta()

    if not os.path.isfile(user32_dst) and not os.path.isfile(backup_path) and not meta:
        clear_stealth_user32_marker()
        return False

    steam_was_running = is_steam_running()
    had_original = meta.get("had_original")
    if had_original is None:
        if os.path.isfile(backup_path) and _backup_is_valid_original(backup_path):
            had_original = True
        elif os.path.isfile(user32_dst) and is_steam_user32_injected(steam_dir, user32_dst):
            had_original = False

    restored = False
    for attempt in range(5):
        if is_steam_running():
            if not close_steam_for_downgrade(timeout=25):
                logging.warning(
                    "Steam encore actif avant restauration user32 (tentative %s/5)",
                    attempt + 1,
                )
            time.sleep(1)

        try:
            if had_original is False:
                if os.path.isfile(user32_dst):
                    os.remove(user32_dst)
                    logging.info(
                        "user32.dll supprimé du dossier Steam (absent à l'origine)"
                    )
                clear_stealth_user32_marker()
                restored = True
                break

            if os.path.isfile(backup_path) and _backup_is_valid_original(backup_path):
                shutil.copy2(backup_path, user32_dst)
                logging.info("user32.dll Steam restauré depuis la sauvegarde")
                clear_stealth_user32_marker()
                restored = True
                break

            if os.path.isfile(user32_dst) and is_steam_user32_injected(steam_dir, user32_dst):
                os.remove(user32_dst)
                logging.info("user32.dll injecté supprimé du dossier Steam")
                clear_stealth_user32_marker()
                restored = True
                break

            if not os.path.isfile(user32_dst):
                clear_stealth_user32_marker()
                restored = True
                break

            logging.warning("Restauration user32 impossible : fichier non reconnu comme injecté")
            break
        except OSError as err:
            logging.warning(
                "Échec restauration user32 (tentative %s/5) : %s", attempt + 1, err
            )
            if attempt == 4:
                logging.exception(err)
            else:
                time.sleep(1.5)

    if restored and (restart_steam or steam_was_running):
        launch_steam(steam_dir)
        logging.info("Steam relancé sans user32.dll injecté")

    return restored


def restore_steam_user32_if_needed():
    """Restaure user32.dll si une session furtive est active ou a été interrompue."""
    setup_logging()
    if not stealth_user32_needs_restore():
        return False
    manifest = load_install_manifest()
    steam_path = manifest.get("steam_path") or ""
    if config.steam_path:
        steam_path = steam_path or config.steam_path
    return restore_steam_user32(steam_path or None)


def restore_steam_after_uninstall(steam_dir=None):
    """Restaure les fichiers Steam modifiés par Stealth Luma."""
    manifest = load_install_manifest()
    steam_dir = steam_dir or manifest.get("steam_path") or detect_steam_path()
    if not steam_dir or not os.path.isdir(steam_dir):
        logging.warning("Restauration Steam ignorée : chemin Steam introuvable")
        return False

    remove_stealth_files_from_steam(steam_dir)
    remove_steam_cfg(steam_dir)
    return True


def remove_stealth_files_from_steam(steam_dir=None):
    """Retire user32.dll injecté, AppList et AppListManager.exe du dossier Steam."""
    steam_dir = steam_dir or get_steam_directory()
    if not steam_dir or not os.path.isdir(steam_dir):
        logging.warning("Nettoyage mode furtif ignoré : chemin Steam introuvable")
        return False

    restore_steam_user32(steam_dir)

    applist_path = get_steam_applist_path(steam_dir)
    if os.path.isdir(applist_path):
        shutil.rmtree(applist_path)
        logging.info("Dossier AppList Steam supprimé : %s", applist_path)

    manager_path = os.path.join(steam_dir, STEALTH_APPLIST_MANAGER)
    if os.path.isfile(manager_path):
        os.remove(manager_path)
        logging.info("%s supprimé du dossier Steam", STEALTH_APPLIST_MANAGER)

    return True


def remove_local_app_data():
    if os.path.isdir(BASE_PATH):
        shutil.rmtree(BASE_PATH)
        logging.info("Données locales supprimées : %s", BASE_PATH)


def deploy_stealth_files_to_steam(steam_dir=None, glinject_path=None):
    """Étapes 2-3 : copie user32SF.dll (renommé user32.dll) et AppListManager.exe vers Steam."""
    steam_dir = steam_dir or get_steam_directory()
    glinject = os.path.abspath(glinject_path or get_glinject_path())
    backup_steam_user32(steam_dir)

    user32_dst = os.path.join(steam_dir, STEALTH_USER32_TARGET)
    meta = _load_steam_user32_meta()
    if "had_original" not in meta:
        meta["had_original"] = (
            os.path.isfile(user32_dst)
            and not is_steam_user32_injected(steam_dir, user32_dst)
        )
        _save_steam_user32_meta(meta)

    user32_src = os.path.join(glinject, STEALTH_USER32_SOURCE)
    if not os.path.isfile(user32_src):
        raise FileNotFoundError(
            "{0} introuvable dans GLinject.".format(STEALTH_USER32_SOURCE)
        )

    shutil.copy2(user32_src, user32_dst)
    logging.info("%s copié vers %s", STEALTH_USER32_SOURCE, user32_dst)

    manager_src = os.path.join(glinject, STEALTH_APPLIST_MANAGER)
    if os.path.isfile(manager_src):
        shutil.copy2(manager_src, os.path.join(steam_dir, STEALTH_APPLIST_MANAGER))
        logging.info("%s copié vers le dossier Steam", STEALTH_APPLIST_MANAGER)

    mark_stealth_user32_deployed(steam_dir)


def launch_steam(steam_dir=None):
    steam_dir = os.path.abspath(steam_dir) if steam_dir else get_steam_directory()
    steam_exe = os.path.join(steam_dir, "Steam.exe")
    if not os.path.isfile(steam_exe):
        steam_exe = get_steam_exe_path()
        steam_dir = get_steam_directory()
    subprocess.Popen([steam_exe], cwd=steam_dir)
    logging.info("Steam lancé depuis %s", steam_dir)


STEAM_APP_CACHE_PATH = os.path.join(BASE_PATH, "steam_app_cache.json")
STEAM_SKIP_APPIDS = {
    "228980",   # Steamworks Common Redistributables
    "1070560",  # Steam Linux Runtime
    "1391110",  # Steam Linux Runtime
    "1493710",  # Proton
    "1628350",  # Steamworks Common Redistributables
}
STEAM_SKIP_NAME_PARTS = (
    "steamworks",
    "proton",
    "steam linux runtime",
    "directx",
    "redistributable",
    "vcredist",
)


def _parse_acf_value(content, key):
    match = re.search(rf'"{re.escape(key)}"\s+"((?:\\.|[^"\\])*)"', content)
    if not match:
        return ""
    return match.group(1).replace("\\\\", "\\").replace('\\"', '"')


def get_steam_library_folders(steam_path):
    folders = []
    seen = set()

    def add(path):
        if not path:
            return
        abs_path = os.path.abspath(path)
        key = os.path.normcase(abs_path)
        if key not in seen and os.path.isdir(abs_path):
            seen.add(key)
            folders.append(abs_path)

    add(steam_path)

    for rel_path in ("steamapps/libraryfolders.vdf", "config/libraryfolders.vdf"):
        vdf_path = os.path.join(steam_path, rel_path)
        if not os.path.isfile(vdf_path):
            continue
        try:
            with open(vdf_path, "r", encoding="utf-8", errors="ignore") as file_:
                content = file_.read()
            for match in re.finditer(r'"path"\s+"((?:\\.|[^"\\])*)"', content):
                add(match.group(1).replace("\\\\", "\\"))
        except OSError as err:
            logging.warning("Impossible de lire %s : %s", vdf_path, err)
        break

    return folders


def scan_installed_steam_apps(steam_path):
    installed = {}

    for library in get_steam_library_folders(steam_path):
        steamapps = os.path.join(library, "steamapps")
        if not os.path.isdir(steamapps):
            continue

        for filename in os.listdir(steamapps):
            if not filename.startswith("appmanifest_") or not filename.endswith(".acf"):
                continue

            manifest_path = os.path.join(steamapps, filename)
            try:
                with open(manifest_path, "r", encoding="utf-8", errors="ignore") as file_:
                    content = file_.read()
            except OSError:
                continue

            appid = _parse_acf_value(content, "appid")
            name = _parse_acf_value(content, "name")
            if appid and name:
                installed[appid] = name

    return installed


def _should_skip_steam_app(appid, name):
    if appid in STEAM_SKIP_APPIDS:
        return True
    name_lower = name.lower()
    return any(part in name_lower for part in STEAM_SKIP_NAME_PARTS)


def _load_steam_app_cache():
    if not os.path.isfile(STEAM_APP_CACHE_PATH):
        return {}
    try:
        with open(STEAM_APP_CACHE_PATH, "r", encoding="utf-8") as file_:
            return json.load(file_)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_steam_app_cache(cache):
    try:
        os.makedirs(BASE_PATH, exist_ok=True)
        with open(STEAM_APP_CACHE_PATH, "w", encoding="utf-8") as file_:
            json.dump(cache, file_)
    except OSError as err:
        logging.warning("Impossible d'enregistrer le cache Steam : %s", err)


def get_steam_app_metadata(appid, cache=None, include_dlc_list=True):
    if cache is None:
        cache = _load_steam_app_cache()

    cached = cache.get(str(appid))
    if cached:
        has_name = bool(cached.get("name"))
        has_dlc = "dlc" in cached
        if has_name and (not include_dlc_list or has_dlc):
            return cached

    filters = "basic,dlc" if include_dlc_list else "basic"
    metadata = {"type": "game", "name": "", "dlc": cached.get("dlc", []) if cached else []}
    try:
        response = requests.get(
            "https://store.steampowered.com/api/appdetails",
            params={"appids": appid, "filters": filters},
            timeout=12,
        )
        payload = response.json().get(str(appid), {})
        if payload.get("success"):
            data = payload.get("data", {})
            metadata = {
                "type": data.get("type", "game"),
                "name": data.get("name", ""),
                "dlc": data.get("dlc", metadata.get("dlc", [])),
            }
    except (ConnectionError, ConnectTimeout, ValueError, requests.RequestException) as err:
        logging.debug("Métadonnées Steam indisponibles pour %s : %s", appid, err)

    cache[str(appid)] = metadata
    return metadata


def resolve_steam_app_name(appid, cache, installed):
    appid = str(appid)
    if appid in installed:
        return installed[appid]

    cached = cache.get(appid)
    if cached and cached.get("name"):
        return cached["name"]

    metadata = get_steam_app_metadata(appid, cache, include_dlc_list=False)
    if metadata.get("name"):
        return metadata["name"]

    return "DLC {0}".format(appid)


def _steam_store_slug(name):
    slug = re.sub(r"[^\w\s-]", "", name)
    return slug.replace(" ", "_")


def fetch_game_dlcs(appid, game_name):
    """Récupère tous les DLC d'un jeu avec leurs noms (1 requête par page de 64)."""
    slug = _steam_store_slug(game_name) if game_name else "game"
    all_dlcs = []
    start = 0
    page_size = 64

    while True:
        try:
            response = requests.get(
                "https://store.steampowered.com/dlc/{0}/{1}/ajaxgetfilteredrecommendations".format(appid, slug),
                params={"sort": "newreleases", "count": page_size, "start": start},
                timeout=15,
            )
        except (ConnectionError, ConnectTimeout, requests.RequestException) as err:
            logging.debug("Liste DLC indisponible pour %s : %s", appid, err)
            break

        if not response.text.startswith("{"):
            break

        payload = response.json()
        if not payload.get("success"):
            break

        dlcs = parseDlcs(payload.get("results_html", ""))
        all_dlcs.extend(dlcs)
        start += page_size
        total = payload.get("total_count", 0)
        if start >= total or not dlcs:
            break

    return all_dlcs


def _cache_dlc_names(dlcs, cache):
    for dlc in dlcs:
        cache[str(dlc.id)] = {"type": "dlc", "name": dlc.name, "dlc": []}


def get_installed_games_with_extensions(steam_path):
    """Retourne les jeux installés et tous leurs DLC/extensions (via l'API Steam)."""
    if not is_valid_steam_path(steam_path):
        return []

    installed = scan_installed_steam_apps(steam_path)
    if not installed:
        return []

    cache = _load_steam_app_cache()
    result = []
    seen_ids = set()
    game_ids = []

    for appid, manifest_name in installed.items():
        if _should_skip_steam_app(appid, manifest_name):
            continue

        metadata = get_steam_app_metadata(appid, cache)
        app_type = metadata.get("type", "game")
        if app_type == "dlc":
            continue
        if app_type in ("game", "demo", "beta"):
            game_ids.append(appid)

    for appid in sorted(game_ids, key=lambda app_id: installed[app_id].lower()):
        name = installed[appid]
        result.append(Game(appid, name, "Game"))
        seen_ids.add(appid)

        metadata = get_steam_app_metadata(appid, cache)
        dlcs = fetch_game_dlcs(appid, name)

        if not dlcs:
            for dlc_id in metadata.get("dlc", []):
                dlc_id = str(dlc_id)
                if dlc_id in seen_ids:
                    continue
                dlc_name = resolve_steam_app_name(dlc_id, cache, installed)
                dlcs.append(Game(dlc_id, dlc_name, "DLC"))

        _cache_dlc_names(dlcs, cache)
        for dlc in dlcs:
            if dlc.id not in seen_ids:
                result.append(dlc)
                seen_ids.add(dlc.id)

    for appid, manifest_name in installed.items():
        if appid in seen_ids or _should_skip_steam_app(appid, manifest_name):
            continue

        metadata = get_steam_app_metadata(appid, cache)
        if metadata.get("type") == "dlc":
            result.append(Game(appid, manifest_name, "DLC"))
            seen_ids.add(appid)

    _save_steam_app_cache(cache)

    logging.info("%d entrée(s) importée(s) depuis la bibliothèque Steam", len(result))
    return result


#-------------
setup_logging()
logging.info("%s %s", APP_NAME, CURRENT_VERSION)
config = Config.load_config()
query_filter = re.compile("[ \u00a9\u00ae\u2122]")

@contextmanager
def get_config():
    global config
    try:
        if config:
            yield config
        else:
            config = Config.load_config()
    finally:
        config.export_config()

def createFiles(games, steam_dir=None):
    """Génère l'AppList dans le dossier Steam (remplace AppListManager.exe)."""
    if not is_valid_steam_path(config.steam_path):
        raise RuntimeError("Chemin Steam invalide. Configurez Steam dans les paramètres.")

    applist_path = get_steam_applist_path(steam_dir)
    if os.path.exists(applist_path):
        shutil.rmtree(applist_path)
        time.sleep(0.5)

    os.makedirs(applist_path, exist_ok=True)

    for i in range(len(games)):
        with open(os.path.join(applist_path, "{0}.txt".format(i)), "w") as file:
            file.write(games[i].id)

    logging.info("AppList créée dans %s (%d entrée(s))", applist_path, len(games))

def parseSteamDB(html):
    p = parser(html, "html.parser")

    rows = p.find_all("tr", class_="app")

    games = []
    for row in rows:
        data = row("td")
        if data[1].get_text() != "Unknown":
            game = Game(data[0].get_text(), data[2].get_text(), data[1].get_text())
            games.append(game)

    return games

def parseDlcs(html):
    p = parser(html, "html.parser")

    dlcs = p.find_all("div", class_="recommendation")

    games = []
    for dlc in dlcs:
        appid = dlc.find("a")["data-ds-appid"]
        name = dlc.find("span", class_="color_created").get_text()
        games.append(Game(appid, name, "DLC"))

    return games

def getDlcs(storeUrl):
    if "app/" not in storeUrl:
        return []
    appinfo = storeUrl.split("app/")[1].split("/")
    appid = appinfo[0]
    game_name = appinfo[1].replace("_", " ").replace("-", " ") if len(appinfo) > 1 and appinfo[1] else ""
    return fetch_game_dlcs(appid, game_name)

def parseGames(html, query):
    query = query_filter.sub("", query.lower())
    p = parser(html, "html.parser")

    results = p.find_all("a", class_="search_result_row")

    games = []
    for result in results:
        if result.has_attr("data-ds-appid"):
            appid = result["data-ds-appid"]
            name = result.find("span", class_="title").get_text()
            # Filter out garbage
            if "," not in appid and query in query_filter.sub("", name.lower()):
                games.append(Game(appid, name, "Game"))
                games.extend(getDlcs(result["href"]))

    return games

def queryfy(input_):
    arr = input_.split()
    result = arr.pop(0)
    for word in arr:
        result = result + "+" + word
    print(result)
    return result

def queryGames(query):
    try:
        if config.use_steamdb and False:
            scraper = cloudscraper.create_scraper()
            params = {"a": "app", "q": query, "type": -1, "category": 0}
            response = scraper.get("https://steamdb.info/search/", params=params)
            return parseSteamDB(response.content)
        else:
            params = {"term": query, "count": 25, "start": 0, "category1": 998}
            response = requests.get("https://store.steampowered.com/search/results", params=params)
            return parseGames(response.text, query)
    except (ConnectionError, ConnectTimeout, CloudflareException, CaptchaException) as err:
        logging.exception(err)
        return err

def normalize_version_tag(tag):
    if not tag:
        return ""
    return str(tag).strip().lstrip("vV")


def version_tuple(version_string):
    version_string = normalize_version_tag(version_string)
    parts = []
    for piece in re.split(r"[.\-+]", version_string):
        if piece.isdigit():
            parts.append(int(piece))
        elif piece:
            break
    return tuple(parts)


def is_remote_version_newer(remote_version, local_version):
    remote = version_tuple(remote_version)
    local = version_tuple(local_version)
    if not remote:
        return False
    return remote > local


def fetch_latest_release_info():
    """Récupère la dernière release GitHub et l'URL du installateur .exe."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "{0}/{1}".format(APP_NAME, CURRENT_VERSION),
    }
    response = requests.get(GITHUB_API_LATEST_RELEASE, headers=headers, timeout=20)
    response.raise_for_status()
    payload = response.json()
    tag = normalize_version_tag(payload.get("tag_name", ""))
    download_url = ""
    for asset in payload.get("assets", []):
        name = asset.get("name", "")
        if name.startswith(SETUP_INSTALLER_PREFIX) and name.lower().endswith(".exe"):
            download_url = asset.get("browser_download_url", "")
            break
    if not download_url and tag:
        download_url = (
            "https://github.com/{0}/releases/download/v{1}/{2}{1}.exe".format(
                GITHUB_REPO, tag, SETUP_INSTALLER_PREFIX
            )
        )
    return {
        "version": tag,
        "download_url": download_url,
        "page_url": payload.get("html_url", GITHUB_RELEASES_LATEST),
    }


def check_for_application_update():
    """Retourne les infos de release si une version plus récente est disponible."""
    if "-NoUpdate" in sys.argv or not config.check_update:
        return None
    try:
        info = fetch_latest_release_info()
        if not info.get("version") or not info.get("download_url"):
            logging.warning("Release GitHub sans installateur détectable")
            return None
        if is_remote_version_newer(info["version"], CURRENT_VERSION):
            logging.info(
                "Mise à jour disponible : %s (actuel %s)",
                info["version"],
                CURRENT_VERSION,
            )
            return info
        logging.info("Application à jour (%s)", CURRENT_VERSION)
    except Exception as err:
        logging.exception("Échec de la vérification des mises à jour : %s", err)
    return None


def download_setup_installer(download_url, version):
    """Télécharge l'installateur de mise à jour vers le dossier temporaire."""
    if not download_url:
        raise ValueError("URL de téléchargement vide")

    filename = "{0}{1}.exe".format(SETUP_INSTALLER_PREFIX, version)
    dest = os.path.join(tempfile.gettempdir(), filename)
    headers = {
        "User-Agent": "{0}/{1}".format(APP_NAME, CURRENT_VERSION),
        "Accept": "application/octet-stream",
    }
    with requests.get(
        download_url,
        headers=headers,
        stream=True,
        timeout=120,
        allow_redirects=True,
    ) as response:
        response.raise_for_status()
        with open(dest, "wb") as outfile:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    outfile.write(chunk)

    if not os.path.isfile(dest) or os.path.getsize(dest) < 1024:
        raise OSError("Fichier téléchargé invalide ou incomplet")

    logging.info("Installateur téléchargé : %s", dest)
    return dest


def launch_setup_installer(installer_path):
    """Lance l'installateur (désinstalle l'ancienne version via Inno Setup)."""
    installer_path = os.path.abspath(installer_path)
    if not os.path.isfile(installer_path):
        raise FileNotFoundError(installer_path)
    if sys.platform == "win32":
        os.startfile(installer_path)
    else:
        subprocess.Popen([installer_path], close_fds=True)
    logging.info("Installateur lancé : %s", installer_path)


def runUpdater():
    """Conservé pour compatibilité : la vérification est faite dans l'interface."""
    return
