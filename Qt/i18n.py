"""Traductions FR / EN pour l'interface Stealth Luma."""

from __future__ import annotations

DEFAULT_LANGUAGE = "fr"
SUPPORTED_LANGUAGES = ("fr", "en")

_STRINGS = {
    "fr": {
        "developed_by": "Développé par ShyninG",
        "profile": "Profil",
        "active_games": "Jeux/DLC Actif",
        "family_mode": "Mode Famille Steam",
        "steam_child_profiles": "Profils jeux",
        "steam_launch_profiles": "Profils actifs",
        "link_profile": "+ Profil jeu",
        "link_profile_btn": "Ajouter",
        "select_game_profile_to_link": "Sélectionnez un profil jeu à inclure au lancement.",
        "all_game_profiles_linked": "Tous les profils jeux sont déjà inclus.",
        "steam_no_launch_entries": "Aucun jeu à lancer. Ajoutez des profils jeux au profil Steam.",
        "active_games_over_limit": " - dépasse la limite de {0}",
        "active_games_at_limit": " - limite atteinte ({0})",
        "active_games_count": " ({0}/{1})",
        "create_profile": "+ Profil",
        "create_profile_tooltip": "Créer un profil manuel pour un jeu non détecté",
        "delete_profile": "Suppr.",
        "delete_profile_tooltip": "Supprimer le profil sélectionné",
        "remove": "Retirer",
        "add": "Ajouter",
        "editor_title": "Éditeur - jeux / DLC non détectés",
        "editor_col_id": "ID",
        "editor_col_name": "Nom",
        "editor_col_type": "Type",
        "editor_ph_id": "Saisir l'ID Steam",
        "editor_ph_name": "Saisir le nom",
        "editor_type_choose": "Choisir",
        "editor_add_row_tooltip": "Ajouter une ligne",
        "cancel": "Annuler",
        "ok": "OK",
        "installed_game": "Nom du profil",
        "profile_name_required": "Indiquez un nom de profil.",
        "profile_name_ph": "Ex. Mon jeu custom",
        "create_profile_btn": "Créer le profil",
        "save": "Enregistrer",
        "steam_path": "Chemin Steam",
        "greenluma_path": "Chemin {0}",
        "closing_steam": "Fermeture de Steam…",
        "launch": "Lancer",
        "tray_open": "Afficher Stealth Luma",
        "tray_close": "Quitter",
        "tray_running": "En cours d'exécution",
        "tray_minimized_body": (
            "L'application reste active dans la zone de notification. "
            "Clic droit sur l'icône pour la rouvrir."
        ),
        "settings": "Paramètres",
        "check_updates": "Vérifier les mises à jour au démarrage",
        "update_available": (
            "Une nouvelle version est disponible : {0}\n"
            "Version installée : {1}\n\n"
            "L'installateur désinstallera l'ancienne version puis installera la mise à jour. "
            "Vos profils seront conservés."
        ),
        "update_download": "Mettre à jour",
        "update_later": "Plus tard",
        "update_downloading": "Téléchargement de la version {0}…",
        "update_download_failed": "Échec du téléchargement de la mise à jour.\n{0}",
        "update_launching": "Lancement de l'installateur… Stealth Luma va se fermer.",
        "steam_folder_ph": "Dossier Steam",
        "glinject_ph": "Dossier GLinject",
        "glinject_auto_ph": "Dossier GLinject (automatique)",
        "restore": "Restaurer",
        "download_csrin": "Télécharger sur cs.rin.ru",
        "select_zip": "Sélectionner le ZIP téléchargé",
        "load": "Recharger les DLC",
        "importing": "Rechargement…",
        "load_tooltip_default": "Recharger les DLC du jeu sélectionné",
        "load_tooltip_select_game": "Sélectionnez un jeu dans la liste pour recharger ses DLC",
        "load_tooltip_profile": "Recharger les DLC du profil « {0} »",
        "load_tooltip_no_profile": "Aucun profil pour « {0} »",
        "load_tooltip_steam": "Réintégrer tous les profils jeux, recharger leurs DLC et actualiser la liste combinée",
        "steam_reloading": "Rechargement des profils jeux…",
        "steam_reload_done": "{0} profil(s) jeu rechargé(s), {1} entrée(s) au total (max {2}).",
        "steam_reload_partial": "Rechargement partiel : {0} erreur(s) sur {1}.",
        "settings_paths": "Chemins",
        "settings_steam_version": "Version Steam",
        "settings_app": "Application",
        "steam_version_label": "mer. 10 juin 2026",
        "greenluma_not_found": "{0} introuvable",
        "greenluma_install_text": (
            "Les fichiers mode furtif sont absents du dossier GLinject "
            "(DeleteSteamAppCache.exe, user32SF.dll).\n\n"
            "Téléchargez {0} 2026 sur cs.rin.ru, puis sélectionnez l'archive ZIP "
            "téléchargée pour l'installer automatiquement (mot de passe : cs.rin.ru)."
        ),
        "greenluma_installed": "{0} installé dans GLinject.\nDossier : {1}",
        "extracting": "Extraction en cours…",
        "select_archive_title": "Sélectionner l'archive {0}",
        "welcome_popup": (
            "Merci d'utiliser {0}.\n\n"
            "Ceci est uniquement un gestionnaire de jeux ; le moteur doit être installé "
            "séparément dans GLinject."
        ),
        "invalid_steam_path": "Chemin Steam invalide. Configurez Steam dans les paramètres.",
        "cannot_list_games": "Impossible de lister les jeux installés.",
        "select_installed_game": "Sélectionnez un jeu installé dans la liste.",
        "profile_exists": "Un profil existe déjà pour « {0} ».",
        "cannot_create_profile": "Impossible de créer le profil.",
        "creating_profile_dlc": "Création de « {0} » - chargement des DLC…",
        "steam_profile_no_delete": "Le profil du compte Steam ne peut pas être supprimé.",
        "confirm_delete_profile": "Supprimer le profil « {0} » et tous ses jeux ?",
        "select_game_not_dlc": "Sélectionnez un jeu (pas un DLC) dans la liste.",
        "no_profile_for_game": "Aucun profil pour « {0} ».",
        "loading_profile": "Chargement de « {0} »…",
        "cannot_load_config": "Impossible de charger la configuration. Consultez errors.log.",
        "profile_ready": "Profil « {0} » prêt : {1} entrée(s) (jeu + {2} DLC).",
        "profile_limit_reached": "\n\n{0} entrée(s) au total - limite de {1} par profil atteinte.",
        "loading_installed_games": "Chargement des jeux installés…",
        "all_games_have_profile": "Tous les jeux installés ont déjà un profil.",
        "steam_profile_family_only": (
            "Le profil Steam regroupe les profils jeux pour lancer plusieurs titres "
            "et DLC en une fois (max 168).\n"
            "Utilisez Recharger les DLC pour réintégrer les jeux retirés, "
            "ou + Profil pour un jeu non détecté."
        ),
        "profile_full": (
            "Ce profil a atteint la limite de {0} entrées.\n"
            "Créez un nouveau profil pour ajouter d'autres jeux."
        ),
        "fill_id_name": "Renseignez au minimum un ID et un nom pour chaque ligne.",
        "entries_added": "{0} entrée(s) ajoutée(s) au profil.",
        "entries_skipped": "\n\n{0} entrée(s) ignorée(s) (profil plein, max {1}).",
        "confirm_steam_restore": (
            "Steam va être fermé. Les fichiers mode furtif seront retirés "
            "(user32.dll, AppList, AppListManager.exe), steam.cfg sera supprimé "
            "et la dernière version officielle sera téléchargée.\n\n"
            "Attendez que la fenêtre de mise à jour Steam se ferme toute seule avant de relancer Steam.\n\n"
            "Continuer ?"
        ),
        "steam_restore_failed": "Restauration Steam échouée.\n\n{0}",
        "steam_restore_ok": (
            "Restauration lancée.\n\n"
            "• Fichiers mode furtif retirés (user32.dll, AppList, AppListManager.exe).\n"
            "• steam.cfg a été supprimé.\n"
            "• Attendez que la fenêtre de mise à jour Steam se ferme toute seule.\n"
            "• Relancez ensuite Steam normalement."
        ),
        "steam_downgrade_required": (
            "Steam n'est pas sur la version cible.\n\n"
            "La mise à jour est en cours (steam.cfg + version {0}).\n"
            "Attendez la fin de la mise à jour Steam avant de lancer."
        ),
        "no_steam_account": "Aucun compte Steam sélectionné.",
        "profile_too_many_entries": (
            "Ce profil contient {0} entrées (limite : {1}).\n\n"
            "Créez un nouveau profil et répartissez vos jeux, ou utilisez « Charger » "
            "pour une répartition automatique."
        ),
        "cannot_close_steam": "Impossible de fermer Steam. Fermez-le manuellement puis réessayez.",
        "stealth_launch_failed": "Échec du lancement mode furtif. Consultez errors.log.",
        "delete_cache_failed": "DeleteSteamAppCache.exe a échoué. Consultez errors.log.",
        "cannot_generate_applist": "Impossible de générer l'AppList. Consultez errors.log.",
        "applist_generated": "AppList générée dans le dossier Steam",
        "enter_path": "Veuillez saisir un chemin",
        "invalid_path": "Chemin invalide",
        "steam_exe_not_found": "Steam.exe introuvable dans ce dossier",
        "steam_not_detected": "Steam introuvable automatiquement. Indiquez le dossier d'installation.",
        "stealth_files_missing": "Fichiers mode furtif introuvables (DeleteSteamAppCache.exe, user32SF.dll)",
        "stealth_files_blocked_defender": (
            "Windows Defender a bloqué l'extraction des fichiers mode furtif.\n\n"
            "Ajoutez une exclusion dans Sécurité Windows pour :\n"
            "{0}\n\n"
            "Puis relancez Stealth Luma."
        ),
        "dlc_suffix": " [DLC]",
    },
    "en": {
        "developed_by": "Developed by ShyninG",
        "profile": "Profile",
        "active_games": "Active Games/DLC",
        "family_mode": "Steam Family Mode",
        "steam_child_profiles": "Game profiles",
        "steam_launch_profiles": "Active profiles",
        "link_profile": "+ Game profile",
        "link_profile_btn": "Add",
        "select_game_profile_to_link": "Select a game profile to include in the launch.",
        "all_game_profiles_linked": "All game profiles are already included.",
        "steam_no_launch_entries": "Nothing to launch. Add game profiles to the Steam profile.",
        "active_games_over_limit": " - exceeds limit of {0}",
        "active_games_at_limit": " - limit reached ({0})",
        "active_games_count": " ({0}/{1})",
        "create_profile": "+ Profile",
        "create_profile_tooltip": "Create a manual profile for an undetected game",
        "delete_profile": "Del.",
        "delete_profile_tooltip": "Delete the selected profile",
        "remove": "Remove",
        "add": "Add",
        "editor_title": "Editor - undetected games / DLC",
        "editor_col_id": "ID",
        "editor_col_name": "Name",
        "editor_col_type": "Type",
        "editor_ph_id": "Enter Steam ID",
        "editor_ph_name": "Enter name",
        "editor_type_choose": "Choose",
        "editor_add_row_tooltip": "Add a row",
        "cancel": "Cancel",
        "ok": "OK",
        "installed_game": "Profile name",
        "profile_name_required": "Enter a profile name.",
        "profile_name_ph": "e.g. My custom game",
        "create_profile_btn": "Create profile",
        "save": "Save",
        "steam_path": "Steam path",
        "greenluma_path": "{0} path",
        "closing_steam": "Closing Steam…",
        "launch": "Launch",
        "tray_open": "Show Stealth Luma",
        "tray_close": "Quit",
        "tray_running": "Running",
        "tray_minimized_body": (
            "The app is still running in the notification area. "
            "Right-click the icon to open it again."
        ),
        "settings": "Settings",
        "check_updates": "Check for updates on startup",
        "update_available": (
            "A new version is available: {0}\n"
            "Installed version: {1}\n\n"
            "The installer will remove the old version and install the update. "
            "Your profiles will be kept."
        ),
        "update_download": "Update",
        "update_later": "Later",
        "update_downloading": "Downloading version {0}…",
        "update_download_failed": "Update download failed.\n{0}",
        "update_launching": "Launching the installer… Stealth Luma will close.",
        "steam_folder_ph": "Steam folder",
        "glinject_ph": "GLinject folder",
        "glinject_auto_ph": "GLinject folder (automatic)",
        "restore": "Restore",
        "download_csrin": "Download on cs.rin.ru",
        "select_zip": "Select downloaded ZIP",
        "load": "Reload DLC",
        "importing": "Reloading…",
        "load_tooltip_default": "Reload DLC for the selected game",
        "load_tooltip_select_game": "Select a game in the list to reload its DLC",
        "load_tooltip_profile": "Reload DLC for profile « {0} »",
        "load_tooltip_no_profile": "No profile for « {0} »",
        "load_tooltip_steam": "Re-include all game profiles, reload their DLC and refresh the combined list",
        "steam_reloading": "Reloading game profiles…",
        "steam_reload_done": "{0} game profile(s) reloaded, {1} total entries (max {2}).",
        "steam_reload_partial": "Partial reload: {0} error(s) out of {1}.",
        "settings_paths": "Paths",
        "settings_steam_version": "Steam version",
        "settings_app": "Application",
        "steam_version_label": "Wed. Jun 10, 2026",
        "greenluma_not_found": "{0} not found",
        "greenluma_install_text": (
            "Stealth mode files are missing from the GLinject folder "
            "(DeleteSteamAppCache.exe, user32SF.dll).\n\n"
            "Download {0} 2026 on cs.rin.ru, then select the downloaded ZIP archive "
            "to install automatically (password: cs.rin.ru)."
        ),
        "greenluma_installed": "{0} installed in GLinject.\nFolder: {1}",
        "extracting": "Extracting…",
        "select_archive_title": "Select {0} archive",
        "welcome_popup": (
            "Thank you for using {0}.\n\n"
            "This is only a game manager; the engine must be installed separately in GLinject."
        ),
        "invalid_steam_path": "Invalid Steam path. Configure Steam in settings.",
        "cannot_list_games": "Unable to list installed games.",
        "select_installed_game": "Select an installed game from the list.",
        "profile_exists": "A profile already exists for « {0} ».",
        "cannot_create_profile": "Unable to create profile.",
        "creating_profile_dlc": "Creating « {0} » - loading DLC…",
        "steam_profile_no_delete": "The Steam account profile cannot be deleted.",
        "confirm_delete_profile": "Delete profile « {0} » and all its games?",
        "select_game_not_dlc": "Select a game (not a DLC) from the list.",
        "no_profile_for_game": "No profile for « {0} ».",
        "loading_profile": "Loading « {0} »…",
        "cannot_load_config": "Unable to load configuration. See errors.log.",
        "profile_ready": "Profile « {0} » ready: {1} entry/entries (game + {2} DLC).",
        "profile_limit_reached": "\n\n{0} total entries - limit of {1} per profile reached.",
        "loading_installed_games": "Loading installed games…",
        "all_games_have_profile": "All installed games already have a profile.",
        "steam_profile_family_only": (
            "The Steam profile groups game profiles to launch multiple titles "
            "and DLC at once (max 168).\n"
            "Use Reload DLC to re-include removed games, "
            "or + Profile for an undetected game."
        ),
        "profile_full": (
            "This profile has reached the limit of {0} entries.\n"
            "Create a new profile to add more games."
        ),
        "fill_id_name": "Enter at least an ID and a name for each row.",
        "entries_added": "{0} entry/entries added to profile.",
        "entries_skipped": "\n\n{0} entry/entries skipped (profile full, max {1}).",
        "confirm_steam_restore": (
            "Steam will be closed. Stealth mode files will be removed "
            "(user32.dll, AppList, AppListManager.exe), steam.cfg will be removed "
            "and the latest official version will be downloaded.\n\n"
            "Wait for the Steam update window to close on its own before relaunching Steam.\n\n"
            "Continue?"
        ),
        "steam_restore_failed": "Steam restore failed.\n\n{0}",
        "steam_restore_ok": (
            "Restore started.\n\n"
            "• Stealth mode files removed (user32.dll, AppList, AppListManager.exe).\n"
            "• steam.cfg has been removed.\n"
            "• Wait for the Steam update window to close on its own.\n"
            "• Then launch Steam normally."
        ),
        "steam_downgrade_required": (
            "Steam is not on the target version.\n\n"
            "Update in progress (steam.cfg + version {0}).\n"
            "Wait for the Steam update to finish before launching."
        ),
        "no_steam_account": "No Steam account selected.",
        "profile_too_many_entries": (
            "This profile contains {0} entries (limit: {1}).\n\n"
            "Create a new profile and split your games, or use « Load » "
            "for automatic distribution."
        ),
        "cannot_close_steam": "Unable to close Steam. Close it manually and try again.",
        "stealth_launch_failed": "Stealth mode launch failed. See errors.log.",
        "delete_cache_failed": "DeleteSteamAppCache.exe failed. See errors.log.",
        "cannot_generate_applist": "Unable to generate AppList. See errors.log.",
        "applist_generated": "AppList generated in the Steam folder",
        "enter_path": "Please enter a path",
        "invalid_path": "Invalid path",
        "steam_exe_not_found": "Steam.exe not found in this folder",
        "steam_not_detected": "Steam not detected automatically. Enter the installation folder.",
        "stealth_files_missing": "Stealth mode files not found (DeleteSteamAppCache.exe, user32SF.dll)",
        "stealth_files_blocked_defender": (
            "Windows Defender blocked extraction of stealth mode files.\n\n"
            "Add an exclusion in Windows Security for:\n"
            "{0}\n\n"
            "Then restart Stealth Luma."
        ),
        "dlc_suffix": " [DLC]",
    },
}


def normalize_language(code):
    if not code:
        return DEFAULT_LANGUAGE
    code = str(code).lower().split("-")[0]
    return code if code in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def current_language():
    try:
        import core
        return normalize_language(getattr(core.config, "language", DEFAULT_LANGUAGE))
    except Exception:
        return DEFAULT_LANGUAGE


def tr(key, *args, lang=None, **kwargs):
    language = normalize_language(lang or current_language())
    text = _STRINGS.get(language, _STRINGS[DEFAULT_LANGUAGE]).get(
        key, _STRINGS[DEFAULT_LANGUAGE].get(key, key)
    )
    if args:
        return text.format(*args)
    if kwargs:
        return text.format(**kwargs)
    return text
