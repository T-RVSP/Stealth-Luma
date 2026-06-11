from Qt.gui import Ui_MainWindow
from Qt.layouts import ModernLayoutBuilder
from Qt import i18n
from PyQt5.QtWidgets import (
    QMainWindow, QHeaderView, QShortcut, QListWidget, QListWidgetItem, QTableView,
    QStyledItemDelegate, QComboBox, QAbstractItemView, QFrame, QLineEdit, QStyle,
    QToolButton, QStyleOptionViewItem, QFileDialog, QSystemTrayIcon, QMenu, QAction,
    QApplication, QWidgetAction, QLabel, QWidget, QVBoxLayout, QPushButton,
)
from PyQt5.QtCore import Qt, QModelIndex, QVariant, QThread, pyqtSignal, QAbstractTableModel, QSize, QEvent, QTimer, QUrl
from PyQt5.QtGui import QKeySequence, QIcon, QPalette, QColor, QPainter, QDesktopServices
import os
import logging
import subprocess
import core
from Qt.theme import Colors, tray_menu_stylesheet

profile_manager = core.ProfileManager()
games = []

OVERLAY_WIDGETS = (
    "profile_create_window",
    "set_steam_path_window",
    "set_greenluma_path_window",
    "greenluma_install_window",
    "generic_popup",
    "closing_steam",
    "settings_window",
)

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.main_window = Ui_MainWindow()
        self.main_window.setupUi(self)
        self.setStyleSheet("")
        self.main_window.centralwidget.setStyleSheet("")
        self._layout_builder = ModernLayoutBuilder(self.main_window)
        self._layout_builder.build(self)
        self._overlay_widgets = [getattr(self.main_window, name) for name in OVERLAY_WIDGETS]
        self.import_steam_thread = None
        self.load_game_config_thread = None
        self.profile_games_thread = None
        self.extract_greenluma_thread = None
        self.steam_downgrade_thread = None
        self.steam_restore_thread = None
        self.update_check_thread = None
        self.update_download_thread = None
        self._greenluma_retry_callback = None
        self._settings_was_open = False
        self._tray_available = False
        self._in_tray = False
        self._stealth_user32_active = False
        self.setup()
        self.connect_components()

    def _app_icon(self):
        candidates = []
        if getattr(core.sys, "frozen", False):
            candidates.append(os.path.join(core.get_app_directory(), "icon.ico"))
            bundle_root = getattr(core.sys, "_MEIPASS", "")
            if bundle_root:
                candidates.append(os.path.join(bundle_root, "icon.ico"))
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            candidates.append(os.path.join(base_dir, "icon.ico"))
        for icon_path in candidates:
            if os.path.isfile(icon_path):
                return QIcon(icon_path)
        return QIcon()

    def setup_system_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logging.warning("Zone de notification Windows indisponible")
            return

        icon = self._app_icon()
        if icon.isNull():
            logging.warning("Icône zone de notification introuvable")
            return

        self.tray_icon = QSystemTrayIcon(icon, QApplication.instance())
        self.tray_icon.setToolTip(
            "{0} — {1}".format(core.APP_NAME, i18n.tr("tray_running"))
        )
        self.tray_menu = QMenu()
        self.tray_menu.setObjectName("tray_menu")
        self.tray_menu.setStyleSheet(tray_menu_stylesheet())

        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(14, 10, 14, 4)
        header_layout.setSpacing(2)
        self.tray_menu_title = QLabel(core.APP_NAME)
        self.tray_menu_title.setObjectName("tray_menu_title")
        self.tray_menu_subtitle = QLabel(i18n.tr("tray_running"))
        self.tray_menu_subtitle.setObjectName("tray_menu_subtitle")
        header_layout.addWidget(self.tray_menu_title)
        header_layout.addWidget(self.tray_menu_subtitle)
        header_action = QWidgetAction(self)
        header_action.setDefaultWidget(header_widget)
        self.tray_menu.addAction(header_action)
        self.tray_menu.addSeparator()

        self.tray_open_btn = self._create_tray_menu_button(
            i18n.tr("tray_open"), "tray_btn_open", self.show_from_tray
        )
        self.tray_close_btn = self._create_tray_menu_button(
            i18n.tr("tray_close"), "tray_btn_quit", self.quit_application
        )
        self.tray_menu.addAction(self._wrap_tray_menu_button(self.tray_open_btn))
        self.tray_menu.addAction(self._wrap_tray_menu_button(self.tray_close_btn))
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
        self._tray_available = True
        logging.info("Icône zone de notification initialisée")

    def _create_tray_menu_button(self, text, object_name, callback):
        button = QPushButton(text)
        button.setObjectName(object_name)
        button.setFlat(True)
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(callback)
        return button

    def _wrap_tray_menu_button(self, button):
        action = QWidgetAction(self)
        action.setDefaultWidget(button)
        return action

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_from_tray()

    def minimize_to_tray(self):
        if not self._tray_available:
            logging.warning("Réduction zone notification ignorée : tray indisponible")
            self.showMinimized()
            return
        for overlay in self._overlay_widgets:
            if not overlay.isHidden():
                self.toggle_widget(overlay, True)
        self._in_tray = True
        self.tray_icon.show()
        self.tray_icon.showMessage(
            core.APP_NAME,
            i18n.tr("tray_minimized_body"),
            self._app_icon(),
            5000,
        )
        QApplication.processEvents()
        self.hide()
        logging.info("Application réduite dans la zone de notification")

    def show_from_tray(self):
        self._in_tray = False
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_application(self):
        try:
            steam_dir = core.config.steam_path if core.config else ""
            if core.stealth_user32_needs_restore(steam_dir or None):
                core.restore_steam_user32(steam_dir or None)
            self._stealth_user32_active = False
        except Exception:
            logging.exception("Échec de la restauration user32.dll à la fermeture")
        if getattr(self, "tray_icon", None):
            self.tray_icon.hide()
        QApplication.instance().quit()

    def changeEvent(self, event):
        if (
            event.type() == QEvent.WindowStateChange
            and self.windowState() & Qt.WindowMinimized
            and not self._in_tray
        ):
            self.setWindowState(Qt.WindowNoState)
            self.minimize_to_tray()
            return
        super().changeEvent(event)

    def closeEvent(self, event):
        self.quit_application()
        event.accept()

    def setup(self):
        self.setup_system_tray()
        self.setWindowIcon(self._app_icon())
        self.setMinimumSize(960, 640)
        self.resize(1180, 760)

        # Hide Other Windows
        self.main_window.profile_create_window.setHidden(True)
        self.main_window.set_steam_path_window.setHidden(True)
        self.main_window.set_greenluma_path_window.setHidden(True)
        self.main_window.greenluma_install_window.setHidden(True)
        self.main_window.closing_steam.setHidden(True)
        self.main_window.generic_popup.setHidden(True)
        self.main_window.settings_window.setHidden(True)
        #-------

        self.setWindowTitle(core.APP_NAME)
        self.main_window.version_label.setText("v{0}".format(core.CURRENT_VERSION))
        self.main_window.no_hook_checkbox.hide()
        self.populate_list(self.main_window.games_list, games)
        self.main_window.games_list.dropEvent = self.drop_event_handler
        self.editor_model = EditorTableModel()
        table = self.main_window.search_result
        table.setStyleSheet("")
        table.setModel(self.editor_model)
        self.cell_delegate = CellEditorDelegate(table)
        self.type_delegate = TypeDelegate(table)
        self.delete_delegate = DeleteRowDelegate(table)
        table.setItemDelegateForColumn(0, self.cell_delegate)
        table.setItemDelegateForColumn(1, self.cell_delegate)
        table.setItemDelegateForColumn(2, self.type_delegate)
        table.setItemDelegateForColumn(3, self.delete_delegate)
        self.delete_delegate.delete_clicked.connect(self.remove_editor_row)
        self.setup_editor_table()
        self.setup_steam_path()
        self.sync_steam_profiles()
        current_profile = self.main_window.profile_selector.currentText()
        if current_profile and current_profile in profile_manager.profiles:
            profile = profile_manager.profiles[current_profile]
            self.show_profile_games(profile)
            self.update_profile_toolbar(profile)
            if core.is_game_profile(profile):
                self.sync_applist_for_profile(profile)
        self.setup_greenluma_path()
        if core.glinject_extract_was_blocked():
            self.show_popup(
                i18n.tr("stealth_files_blocked_defender", core.get_glinject_path())
            )
        self.maybe_run_initial_steam_downgrade()
        try:
            if core.stealth_user32_needs_restore():
                core.restore_steam_user32_if_needed()
        except Exception:
            logging.exception("Échec restauration user32.dll au démarrage")
        if not core.config.manager_msg:
            self.show_popup(i18n.tr("welcome_popup", core.APP_NAME), self.acknowledge_manager, lambda: core.sys.exit())

        # Settings Window Setup
        self.main_window.update_checkbox.setChecked(core.config.check_update)

        # Shortcuts
        del_game = QShortcut(QKeySequence(Qt.Key_Delete), self.main_window.games_list)
        del_game.activated.connect(self.remove_selected)

        del_editor = QShortcut(QKeySequence(Qt.Key_Delete), self.main_window.search_result)
        del_editor.activated.connect(self.remove_editor_rows)

        self._apply_ui_language()
        self._sync_overlay_stack()
        QTimer.singleShot(800, self.maybe_check_for_updates)

    def _apply_ui_language(self):
        ui = self.main_window
        ui.label_profile.setText(i18n.tr("profile"))
        ui.label_games_list.setText(i18n.tr("active_games"))
        ui.create_profile.setText(i18n.tr("create_profile"))
        ui.create_profile.setToolTip(i18n.tr("create_profile_tooltip"))
        ui.delete_profile.setText(i18n.tr("delete_profile"))
        ui.delete_profile.setToolTip(i18n.tr("delete_profile_tooltip"))
        ui.remove_game.setText(i18n.tr("remove"))
        ui.add_to_profile.setText(i18n.tr("add"))
        self._layout_builder.editor_label.setText(i18n.tr("editor_title"))
        ui.generate_btn.hide()
        ui.cancel_profile_btn.setText(i18n.tr("cancel"))
        ui.label_profile_name.setText(i18n.tr("installed_game"))
        ui.create_profile_btn.setText(i18n.tr("create_profile_btn"))
        ui.save_steam_path.setText(i18n.tr("save"))
        ui.cancel_steam_path_btn.setText(i18n.tr("cancel"))
        ui.label_steam_path.setText(i18n.tr("steam_path"))
        ui.save_greenluma_path.setText(i18n.tr("save"))
        ui.cancel_greenluma_path_btn.setText(i18n.tr("cancel"))
        ui.label_greenluma_path.setText(i18n.tr("greenluma_path", core.APP_NAME))
        ui.popup_btn1.setText(i18n.tr("ok"))
        ui.popup_btn2.setText(i18n.tr("cancel"))
        ui.label_close_steam.setText(i18n.tr("closing_steam"))
        ui.run_GreenLuma_btn.setText(i18n.tr("launch"))
        ui.settings_label_main.setText(i18n.tr("settings"))
        ui.settings_label_steam.setText(i18n.tr("steam_path"))
        ui.settings_label_greenluma.hide()
        ui.settings_greenluma_path.hide()
        ui.update_checkbox.setText(i18n.tr("check_updates"))
        ui.steam_path.setPlaceholderText(i18n.tr("steam_folder_ph"))
        ui.greenluma_path.setPlaceholderText(i18n.tr("glinject_ph"))
        ui.settings_steam_path.setPlaceholderText(i18n.tr("steam_folder_ph"))
        ui.settings_greenluma_path.setPlaceholderText(i18n.tr("glinject_auto_ph"))
        ui.settings_cancel_btn.setText(i18n.tr("cancel"))
        ui.settings_steam_restore_btn.setText(i18n.tr("restore"))
        ui.greenluma_install_download_btn.setText(i18n.tr("download_csrin"))
        ui.greenluma_install_select_zip_btn.setText(i18n.tr("select_zip"))
        ui.greenluma_install_cancel_btn.setText(i18n.tr("cancel"))
        if hasattr(self, "tray_open_btn"):
            self.tray_open_btn.setText(i18n.tr("tray_open"))
        if hasattr(self, "tray_close_btn"):
            self.tray_close_btn.setText(i18n.tr("tray_close"))
        if hasattr(self, "tray_menu_subtitle"):
            self.tray_menu_subtitle.setText(i18n.tr("tray_running"))
        if hasattr(self, "tray_icon"):
            self.tray_icon.setToolTip(
                "{0} — {1}".format(core.APP_NAME, i18n.tr("tray_running"))
            )
        self._layout_builder.apply_language()
        self._refresh_editor_table_labels()
        self.refresh_steam_settings_status()
        profile_name = ui.profile_selector.currentText()
        if profile_name in profile_manager.profiles:
            self.show_profile_games(profile_manager.profiles[profile_name])
            self.update_profile_toolbar(profile_manager.profiles[profile_name])

    def set_language(self, language):
        language = i18n.normalize_language(language)
        if language == i18n.current_language():
            self._layout_builder.update_language_buttons()
            return
        with core.get_config() as config:
            config.language = language
        self._apply_ui_language()

    def _refresh_editor_table_labels(self):
        if not hasattr(self, "editor_model"):
            return
        table = self.main_window.search_result
        header = table.horizontalHeader()
        if isinstance(header, EditorTableHeader):
            header._add_btn.setToolTip(i18n.tr("editor_add_row_tooltip"))
        self.editor_model.refresh_labels()
        table.viewport().update()

    def maybe_run_initial_steam_downgrade(self):
        if core.config.steam_downgrade_done:
            return False
        if not core.is_valid_steam_path(core.config.steam_path):
            return False
        if self.steam_downgrade_thread is not None and self.steam_downgrade_thread.isRunning():
            return False

        logging.info("Downgrade Steam automatique (premier lancement)")
        self.steam_downgrade_thread = SteamDowngradeThread(core.DEFAULT_STEAM_DOWNGRADE_URL)
        self.steam_downgrade_thread.signal.connect(self.on_initial_steam_downgrade_finished)
        self.steam_downgrade_thread.start()
        return True

    def on_initial_steam_downgrade_finished(self, result):
        if isinstance(result, Exception):
            core.logging.exception(result)
            return

        with core.get_config() as config:
            config.steam_downgrade_done = True

        logging.info("Downgrade Steam automatique terminé : %s", result)
        self.refresh_steam_settings_status()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cw = self.centralWidget()
        for overlay in self._overlay_widgets:
            if not overlay.isHidden():
                self._layout_builder.position_overlay(overlay, cw)
        self._sync_overlay_stack()

    def _sync_overlay_stack(self):
        modal_open = any(not w.isHidden() for w in self._overlay_widgets)
        self.main_window.main_panel.setEnabled(not modal_open)
        self._layout_builder.sync_overlay_stack(self._overlay_widgets)

    def connect_components(self):
        # Profils
        self.main_window.profile_selector.currentTextChanged.connect(self.select_profile)
        self.main_window.create_profile.clicked.connect(self.show_create_profile_dialog)
        self.main_window.create_profile_btn.clicked.connect(self.create_profile)
        self.main_window.cancel_profile_btn.clicked.connect(
            lambda: self.toggle_widget(self.main_window.profile_create_window, True)
        )
        self.main_window.delete_profile.clicked.connect(self.confirm_delete_profile)
        self.main_window.remove_game.clicked.connect(self.remove_selected)

        # Steam Path
        self.main_window.save_steam_path.clicked.connect(self.set_steam_path)
        self.main_window.cancel_steam_path_btn.clicked.connect(lambda: self.toggle_widget(self.main_window.set_steam_path_window))

        # GreenLuma Path
        self.main_window.save_greenluma_path.clicked.connect(self.set_greenluma_path)
        self.main_window.cancel_greenluma_path_btn.clicked.connect(lambda: self.toggle_widget(self.main_window.set_greenluma_path_window))

        self.main_window.greenluma_install_download_btn.clicked.connect(self.open_greenluma_download_page)
        self.main_window.greenluma_install_select_zip_btn.clicked.connect(self.select_greenluma_zip)
        self.main_window.greenluma_install_cancel_btn.clicked.connect(self.hide_greenluma_install_dialog)

        self.main_window.settings_steam_restore_btn.clicked.connect(self.confirm_steam_restore)

        # Éditeur central
        self.main_window.add_to_profile.clicked.connect(self.add_editor_to_profile)
        self.main_window.search_result.clicked.connect(self._edit_table_on_click)

        self._layout_builder.load_installed_btn.clicked.connect(self.load_selected_game_configuration)
        self.main_window.games_list.itemSelectionChanged.connect(self._update_load_button_state)

        # Main Buttons
        self.main_window.run_GreenLuma_btn.clicked.connect(self.run_GreenLuma)

        # Settings Window
        self.main_window.settings_btn.clicked.connect(self.open_settings)
        self.main_window.settings_cancel_btn.clicked.connect(self.cancel_settings)
        self.main_window.settings_steam_path.editingFinished.connect(self.persist_settings)
        self.main_window.update_checkbox.stateChanged.connect(lambda *_: self.persist_settings())

        self._layout_builder.lang_fr_btn.clicked.connect(lambda: self.set_language("fr"))
        self._layout_builder.lang_en_btn.clicked.connect(lambda: self.set_language("en"))

    # Profile Functions
    def sync_steam_profiles(self):
        if not core.is_valid_steam_path(core.config.steam_path):
            self.refresh_profile_selector()
            return False

        last_profile = core.config.last_profile
        synced, renamed = core.sync_profiles_from_steam(
            profile_manager,
            core.config.steam_path,
            last_profile=last_profile,
        )
        if synced:
            with core.get_config() as config:
                if config.last_profile in renamed:
                    config.last_profile = renamed[config.last_profile]
                elif config.last_profile not in profile_manager.profiles:
                    if profile_manager.profiles:
                        config.last_profile = sorted(profile_manager.profiles.keys(), key=str.lower)[0]
                    else:
                        config.last_profile = ""

        self.refresh_profile_selector()
        return synced

    def select_profile(self, name):
        if not name or name not in profile_manager.profiles:
            return

        with core.get_config() as config:
            config.last_profile = name

        profile = profile_manager.profiles[name]
        self.show_profile_games(profile)
        self.update_profile_toolbar(profile)
        if core.is_game_profile(profile):
            self.sync_applist_for_profile(profile)

    def update_profile_toolbar(self, profile):
        is_steam = core.is_steam_account_profile(profile)
        load_btn = self._layout_builder.load_installed_btn
        load_btn.setVisible(not is_steam)
        self.main_window.create_profile.setEnabled(True)
        self.main_window.delete_profile.setVisible(not is_steam)
        self._update_load_button_state()

    def _update_load_button_state(self):
        profile_name = self.main_window.profile_selector.currentText()
        profile = profile_manager.profiles.get(profile_name)
        load_btn = self._layout_builder.load_installed_btn
        if not profile or core.is_steam_account_profile(profile):
            load_btn.setEnabled(False)
            return

        selected_game = self._get_selected_main_game()
        if not selected_game:
            load_btn.setEnabled(False)
            load_btn.setToolTip(i18n.tr("load_tooltip_select_game"))
            return

        target = core.find_game_profile(profile_manager, selected_game)
        if target:
            load_btn.setEnabled(True)
            load_btn.setToolTip(i18n.tr("load_tooltip_profile", target.name))
        else:
            load_btn.setEnabled(False)
            load_btn.setToolTip(i18n.tr("load_tooltip_no_profile", selected_game.name))

    def _get_selected_main_game(self):
        items = self.main_window.games_list.selectedItems()
        if not items:
            return None

        profile_name = self.main_window.profile_selector.currentText()
        profile = profile_manager.profiles.get(profile_name)
        if not profile:
            return None

        label = items[0].text().replace(i18n.tr("dlc_suffix"), "")
        for game in profile.games:
            if game.type == "Game" and game.name == label:
                return game

        main_game = core.get_profile_main_game(profile, core.config.steam_path)
        if main_game and main_game.name == label:
            return main_game

        return None

    def show_profile_games(self, profile):
        list_ = self.main_window.games_list
        self.populate_list(list_, profile.games)

        if core.is_steam_account_profile(profile):
            self.main_window.label_games_list.setText(i18n.tr("family_mode"))
            return

        count = len(profile.games)
        if count > core.APPLIST_MAX_ENTRIES:
            suffix = i18n.tr("active_games_over_limit", core.APPLIST_MAX_ENTRIES)
        elif count == core.APPLIST_MAX_ENTRIES:
            suffix = i18n.tr("active_games_at_limit", core.APPLIST_MAX_ENTRIES)
        else:
            suffix = i18n.tr("active_games_count", count, core.APPLIST_MAX_ENTRIES)
        self.main_window.label_games_list.setText("{0}{1}".format(i18n.tr("active_games"), suffix))

        main_game = core.get_profile_main_game(profile, core.config.steam_path)
        if main_game:
            for index in range(list_.count()):
                item = list_.item(index)
                if item.text().replace(i18n.tr("dlc_suffix"), "") == main_game.name and i18n.tr("dlc_suffix") not in item.text():
                    list_.setCurrentItem(item)
                    break

    def show_create_profile_dialog(self):
        if not core.is_valid_steam_path(core.config.steam_path):
            self.show_popup(i18n.tr("invalid_steam_path"))
            return

        game_list = self._layout_builder.profile_game_list
        game_list.clear()
        game_list.addItem(i18n.tr("loading_installed_games"))
        self.main_window.create_profile_btn.setEnabled(False)
        self.toggle_widget(self.main_window.profile_create_window)

        self.profile_games_thread = InstalledBaseGamesThread(core.config.steam_path)
        self.profile_games_thread.signal.connect(self.on_profile_games_loaded)
        self.profile_games_thread.start()

    def on_profile_games_loaded(self, games):
        game_list = self._layout_builder.profile_game_list
        game_list.clear()
        self.main_window.create_profile_btn.setEnabled(True)

        if isinstance(games, Exception):
            logging.exception(games)
            self.show_popup(i18n.tr("cannot_list_games"))
            self.toggle_widget(self.main_window.profile_create_window, True)
            return

        available = []
        for game in games:
            if core.find_game_profile(profile_manager, game):
                continue
            available.append(game)

        if not available:
            game_list.addItem(i18n.tr("all_games_have_profile"))
            self.main_window.create_profile_btn.setEnabled(False)
            return

        for game in available:
            item = QListWidgetItem(game.name)
            item.setData(Qt.UserRole, game)
            game_list.addItem(item)

    def create_profile(self):
        game_list = self._layout_builder.profile_game_list
        item = game_list.currentItem()
        if not item:
            self.show_popup(i18n.tr("select_installed_game"))
            return

        game = item.data(Qt.UserRole)
        if not isinstance(game, core.Game):
            self.show_popup(i18n.tr("select_installed_game"))
            return

        if profile_manager.profile_exists(game.name) or core.find_game_profile(profile_manager, game):
            self.show_popup(i18n.tr("profile_exists", game.name))
            return

        if not profile_manager.create_profile(
            game.name,
            games=[game],
            source_app_id=game.id,
        ):
            self.show_popup(i18n.tr("cannot_create_profile"))
            return

        with core.get_config() as config:
            config.last_profile = game.name

        self.refresh_profile_selector()
        self.main_window.profile_selector.setCurrentText(game.name)
        self.toggle_widget(self.main_window.profile_create_window, True)

        ui = self.main_window
        ui.create_profile_btn.setEnabled(False)
        ui.create_profile_btn.setText(i18n.tr("importing"))
        self.main_window.label_games_list.setText(i18n.tr("creating_profile_dlc", game.name))

        self.load_game_config_thread = LoadGameConfigurationThread(
            core.config.steam_path,
            game.id,
            game.name,
            game.name,
        )
        self.load_game_config_thread.signal.connect(self.on_game_configuration_loaded)
        self.load_game_config_thread.start()

    def confirm_delete_profile(self):
        name = self.main_window.profile_selector.currentText()
        if not name or name not in profile_manager.profiles:
            return

        profile = profile_manager.profiles[name]
        if core.is_steam_account_profile(profile):
            self.show_popup(i18n.tr("steam_profile_no_delete"))
            return

        self.show_popup(
            i18n.tr("confirm_delete_profile", name),
            lambda: self.delete_profile(name),
        )

    def delete_profile(self, name):
        self.hide_popup()
        if name not in profile_manager.profiles:
            return

        if core.is_steam_account_profile(profile_manager.profiles[name]):
            return

        profile_manager.remove_profile(name)

        with core.get_config() as config:
            if config.last_profile == name:
                if profile_manager.profiles:
                    config.last_profile = sorted(profile_manager.profiles.keys(), key=str.lower)[0]
                else:
                    config.last_profile = ""

        self.refresh_profile_selector()
        if profile_manager.profiles:
            selected = self.main_window.profile_selector.currentText()
            if selected in profile_manager.profiles:
                profile = profile_manager.profiles[selected]
                self.show_profile_games(profile)
                self.update_profile_toolbar(profile)
        else:
            self.populate_list(self.main_window.games_list, [])
            self.main_window.label_games_list.setText(i18n.tr("active_games"))

    def load_selected_game_configuration(self):
        if not core.is_valid_steam_path(core.config.steam_path):
            self.show_popup(i18n.tr("invalid_steam_path"))
            return

        selected_game = self._get_selected_main_game()
        if not selected_game:
            self.show_popup(i18n.tr("select_game_not_dlc"))
            return

        target_profile = core.find_game_profile(profile_manager, selected_game)
        if not target_profile:
            self.show_popup(i18n.tr("no_profile_for_game", selected_game.name))
            return

        if self.load_game_config_thread and self.load_game_config_thread.isRunning():
            return

        btn = self._layout_builder.load_installed_btn
        btn.setEnabled(False)
        btn.setText(i18n.tr("importing"))
        self.main_window.label_games_list.setText(i18n.tr("loading_profile", target_profile.name))

        self.load_game_config_thread = LoadGameConfigurationThread(
            core.config.steam_path,
            selected_game.id,
            selected_game.name,
            target_profile.name,
        )
        self.load_game_config_thread.signal.connect(self.on_game_configuration_loaded)
        self.load_game_config_thread.start()

    def on_game_configuration_loaded(self, result):
        btn = self._layout_builder.load_installed_btn
        btn.setText(i18n.tr("load"))
        self.main_window.create_profile_btn.setEnabled(True)
        self.main_window.create_profile_btn.setText(i18n.tr("create_profile_btn"))

        if isinstance(result, Exception):
            logging.exception(result)
            profile_name = self.main_window.profile_selector.currentText()
            if profile_name in profile_manager.profiles:
                self.show_profile_games(profile_manager.profiles[profile_name])
            self.update_profile_toolbar(profile_manager.profiles.get(profile_name))
            self.show_popup(i18n.tr("cannot_load_config"))
            return

        profile_name, total, applied, truncated = result
        if profile_name not in profile_manager.profiles:
            return

        with core.get_config() as config:
            config.last_profile = profile_name

        self.refresh_profile_selector()
        self.main_window.profile_selector.setCurrentText(profile_name)
        profile = profile_manager.profiles[profile_name]
        self.show_profile_games(profile)
        self.update_profile_toolbar(profile)
        self.sync_applist_for_profile(profile)

        dlc_count = max(0, applied - 1)
        message = i18n.tr("profile_ready", profile_name, applied, dlc_count)
        if truncated:
            message += i18n.tr("profile_limit_reached", total, core.APPLIST_MAX_ENTRIES)
        self.show_popup(message)

    def refresh_profile_selector(self):
        selector = self.main_window.profile_selector
        selector.blockSignals(True)
        selector.clear()

        profiles = sorted(profile_manager.profiles.values(), key=lambda item: item.name.lower())
        if not profiles:
            selector.blockSignals(False)
            self.populate_list(self.main_window.games_list, [])
            return

        last_profile = core.config.last_profile
        if last_profile in profile_manager.profiles:
            selector.addItem(last_profile)
            for profile in profiles:
                if profile.name != last_profile:
                    selector.addItem(profile.name)
        else:
            for profile in profiles:
                selector.addItem(profile.name)

        selector.blockSignals(False)

    # Éditeur manuel (panneau central)
    def setup_editor_table(self):
        table = self.main_window.search_result
        table.setFrameShape(QFrame.NoFrame)
        table.setSelectionBehavior(QTableView.SelectItems)
        table.setSelectionMode(QTableView.ExtendedSelection)
        table.setAlternatingRowColors(False)
        table.setWordWrap(False)
        table.setTextElideMode(Qt.ElideRight)
        table.setShowGrid(True)
        table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setCornerButtonEnabled(False)
        table.setEditTriggers(QAbstractItemView.EditKeyPressed)

        v_header = table.verticalHeader()
        v_header.setVisible(False)
        v_header.setDefaultSectionSize(36)
        v_header.setMinimumSectionSize(36)

        h_header = EditorTableHeader(Qt.Horizontal, table)
        h_header.setObjectName("editor_table_header")
        table.setHorizontalHeader(h_header)
        h_header.add_row_clicked.connect(self.add_editor_row)
        h_header.setStretchLastSection(False)
        h_header.setMinimumHeight(32)
        h_header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        h_header.setSectionResizeMode(0, QHeaderView.Fixed)
        h_header.setSectionResizeMode(1, QHeaderView.Stretch)
        h_header.setSectionResizeMode(2, QHeaderView.Fixed)
        h_header.setSectionResizeMode(3, QHeaderView.Fixed)
        table.setColumnWidth(0, 96)
        table.setColumnWidth(2, 76)
        table.setColumnWidth(3, 40)

        palette = table.palette()
        palette.setColor(QPalette.Base, QColor(Colors.INPUT_BG))
        palette.setColor(QPalette.AlternateBase, QColor(Colors.INPUT_BG))
        palette.setColor(QPalette.Text, QColor(Colors.TEXT))
        palette.setColor(QPalette.Highlight, QColor(Colors.INPUT_BG))
        palette.setColor(QPalette.HighlightedText, QColor(Colors.TEXT))
        table.setPalette(palette)

    def _edit_table_on_click(self, index):
        if index.isValid() and index.column() != EditorTableModel.ACTION_COLUMN:
            self.main_window.search_result.edit(index)

    def remove_editor_row(self, row):
        self.editor_model.remove_rows([row])

    def add_editor_row(self):
        self.editor_model.add_row()
        table = self.main_window.search_result
        table.selectRow(self.editor_model.rowCount() - 1)
        table.edit(table.model().index(self.editor_model.rowCount() - 1, 0))

    def remove_editor_rows(self):
        selection = self.main_window.search_result.selectionModel().selectedRows()
        if not selection:
            return
        rows = sorted({index.row() for index in selection}, reverse=True)
        self.editor_model.remove_rows(rows)

    def add_editor_to_profile(self):
        profile_name = self.main_window.profile_selector.currentText()
        profile = profile_manager.profiles[profile_name]
        if core.is_steam_account_profile(profile):
            self.show_popup(i18n.tr("steam_profile_family_only"))
            return

        added = 0
        skipped = 0

        for row in self.editor_model.rows:
            app_id, name, app_type = row[0].strip(), row[1].strip(), row[2].strip()
            if not app_id or not name:
                skipped += 1
                continue
            if app_type not in ("Game", "DLC"):
                skipped += 1
                continue
            game = core.Game(app_id, name, app_type)
            if game in profile.games:
                continue
            if len(profile.games) >= core.APPLIST_MAX_ENTRIES:
                skipped += 1
                continue
            profile.add_game(game)
            added += 1

        if added:
            profile.export_profile()
            self.show_profile_games(profile)
            self.sync_applist_for_profile(profile)

        if skipped and not added:
            if len(profile.games) >= core.APPLIST_MAX_ENTRIES:
                self.show_popup(i18n.tr("profile_full", core.APPLIST_MAX_ENTRIES))
            else:
                self.show_popup(i18n.tr("fill_id_name"))
        elif added:
            msg = i18n.tr("entries_added", added)
            if skipped:
                msg += i18n.tr("entries_skipped", skipped, core.APPLIST_MAX_ENTRIES)
            self.show_popup(msg)

    def populate_list(self, list_, data):
        list_.clear()
        for item in data:
            label = item.name
            if item.type == "DLC":
                label = "{0}{1}".format(item.name, i18n.tr("dlc_suffix"))
            list_.addItem(label)

    def remove_selected(self):
        items = self.main_window.games_list.selectedItems()
        if len(items) == 0:
            return

        profile_name = self.main_window.profile_selector.currentText()
        profile = profile_manager.profiles[profile_name]
        if core.is_steam_account_profile(profile):
            return

        for item in items:
            game_name = item.text().replace(i18n.tr("dlc_suffix"), "")
            profile.remove_game(game_name)

        self.show_profile_games(profile)
        profile.export_profile()
        self.sync_applist_for_profile(profile)

    # Settings Functions
    def open_settings(self):
        widget = self.main_window.settings_window
        if widget.isHidden():
            self._load_settings_fields()
            self.refresh_steam_settings_status()
            self.toggle_widget(widget)
            return

        self.persist_settings()
        self.toggle_widget(widget, True)

    def cancel_settings(self):
        self._load_settings_fields()
        self.toggle_widget(self.main_window.settings_window, True)

    def _load_settings_fields(self):
        ui = self.main_window
        ui.settings_steam_path.setText(core.config.steam_path)
        ui.update_checkbox.setChecked(core.config.check_update)

    def refresh_steam_settings_status(self):
        label = getattr(self.main_window, "settings_steam_version_label", None)
        if label is not None:
            label.setText(i18n.tr("steam_version_label"))

    def persist_settings(self):
        previous_steam_path = core.config.steam_path
        with core.get_config() as config:
            config.steam_path = self.main_window.settings_steam_path.text()
            core.ensure_greenluma_path(config)
            config.check_update = self.main_window.update_checkbox.isChecked()

        if os.path.normcase(previous_steam_path or "") != os.path.normcase(core.config.steam_path or ""):
            self.sync_steam_profiles()

    def _refresh_greenluma_runtime_path(self):
        with core.get_config() as config:
            config.no_hook = False
            core.ensure_greenluma_path(config)

    def _greenluma_runtime_ready(self):
        self._refresh_greenluma_runtime_path()
        return core.is_valid_greenluma_path(core.config.greenluma_path)

    def open_greenluma_download_page(self):
        QDesktopServices.openUrl(QUrl(core.GREENLUMA_DOWNLOAD_URL))

    def show_greenluma_install_dialog(self, retry_callback=None):
        self._greenluma_retry_callback = retry_callback
        ui = self.main_window
        ui.greenluma_install_status.setText("")
        ui.greenluma_install_download_btn.setEnabled(True)
        ui.greenluma_install_select_zip_btn.setEnabled(True)
        self.toggle_widget(ui.greenluma_install_window)

    def hide_greenluma_install_dialog(self):
        self._greenluma_retry_callback = None
        self.toggle_widget(self.main_window.greenluma_install_window, True)

    def select_greenluma_zip(self):
        zip_path, _ = QFileDialog.getOpenFileName(
            self,
            i18n.tr("select_archive_title", core.APP_NAME),
            "",
            "Archives ZIP (*.zip)",
        )
        if not zip_path:
            return

        ui = self.main_window
        ui.greenluma_install_status.setText(i18n.tr("extracting"))
        ui.greenluma_install_download_btn.setEnabled(False)
        ui.greenluma_install_select_zip_btn.setEnabled(False)

        self.extract_greenluma_thread = ExtractGreenLumaThread(zip_path)
        self.extract_greenluma_thread.signal.connect(self.on_greenluma_extracted)
        self.extract_greenluma_thread.start()

    def on_greenluma_extracted(self, result):
        ui = self.main_window
        ui.greenluma_install_download_btn.setEnabled(True)
        ui.greenluma_install_select_zip_btn.setEnabled(True)

        if isinstance(result, Exception):
            core.logging.exception(result)
            ui.greenluma_install_status.setText(str(result))
            return

        self._refresh_greenluma_runtime_path()
        ui.greenluma_install_status.setText(
            i18n.tr("greenluma_installed", core.APP_NAME, core.config.greenluma_path)
        )

        retry = self._greenluma_retry_callback
        self._greenluma_retry_callback = None
        QTimer.singleShot(800, self.hide_greenluma_install_dialog)
        if retry and self._greenluma_runtime_ready():
            QTimer.singleShot(900, retry)

    def confirm_steam_restore(self):
        self._settings_was_open = not self.main_window.settings_window.isHidden()
        if self._settings_was_open:
            self.toggle_widget(self.main_window.settings_window, True)

        self.show_popup(
            i18n.tr("confirm_steam_restore"),
            self.start_steam_restore,
            self._cancel_steam_restore,
        )

    def _cancel_steam_restore(self):
        self.hide_popup()
        self._reopen_settings_if_needed()

    def _reopen_settings_if_needed(self):
        if not getattr(self, "_settings_was_open", False):
            return
        self._settings_was_open = False
        self._load_settings_fields()
        self.refresh_steam_settings_status()
        self.toggle_widget(self.main_window.settings_window)

    def start_steam_restore(self):
        self.hide_popup()
        self._settings_was_open = False
        ui = self.main_window
        ui.settings_steam_restore_btn.setEnabled(False)

        self.steam_restore_thread = SteamRestoreThread()
        self.steam_restore_thread.signal.connect(self.on_steam_restore_finished)
        self.steam_restore_thread.start()

    def on_steam_restore_finished(self, result):
        ui = self.main_window
        ui.settings_steam_restore_btn.setEnabled(True)

        if isinstance(result, Exception):
            core.logging.exception(result)
            self.show_popup(i18n.tr("steam_restore_failed", result))
            return

        self.refresh_steam_settings_status()
        self.show_popup(i18n.tr("steam_restore_ok"))

    # Generation Functions
    def run_GreenLuma(self):
        self.hide_popup()

        if not core.is_valid_steam_path(core.config.steam_path):
            self.show_popup(i18n.tr("invalid_steam_path"))
            return

        if not self._greenluma_runtime_ready():
            self.show_greenluma_install_dialog(retry_callback=self.run_GreenLuma)
            return

        profile_name = self.main_window.profile_selector.currentText()
        if profile_name not in profile_manager.profiles:
            self.show_popup(i18n.tr("no_steam_account"))
            return

        profile = profile_manager.profiles[profile_name]

        if core.profile_exceeds_applist_limit(profile):
            self.show_popup(
                i18n.tr(
                    "profile_too_many_entries",
                    len(profile.games),
                    core.APPLIST_MAX_ENTRIES,
                )
            )
            return

        self._refresh_greenluma_runtime_path()
        gl_path = core.config.greenluma_path

        core.logging.info("Validation des fichiers mode furtif")
        for fname in core.STEALTH_REQUIRED_FILES:
            test_path = os.path.join(gl_path, fname)
            if not os.path.isfile(test_path):
                core.logging.error("%s introuvable : %s", fname, test_path)
                self.show_greenluma_install_dialog(retry_callback=self.run_GreenLuma)
                return

        if self.is_steam_running():
            core.logging.info("Fermeture de Steam")
            self.toggle_widget(self.main_window.closing_steam)
            if not core.close_steam_for_downgrade():
                self.toggle_widget(self.main_window.closing_steam, True)
                self.show_popup(i18n.tr("cannot_close_steam"))
                return
            self.toggle_widget(self.main_window.closing_steam, True)
            core.time.sleep(1)

        try:
            core.run_delete_steam_app_cache(gl_path)
            if profile.games:
                self.sync_applist_for_profile(profile)
            core.deploy_stealth_files_to_steam(glinject_path=gl_path)
            self._stealth_user32_active = True
            core.launch_steam()
            logging.info("Steam lancé en mode furtif")
            self.minimize_to_tray()
        except OSError as err:
            core.logging.exception(err)
            self.show_popup(i18n.tr("stealth_launch_failed"))
        except subprocess.CalledProcessError as err:
            core.logging.exception(err)
            self.show_popup(i18n.tr("delete_cache_failed"))
        except RuntimeError as err:
            self.show_popup(str(err))

    def sync_applist_for_profile(self, profile, popup=False):
        if not profile:
            return False

        if not core.is_valid_steam_path(core.config.steam_path):
            logging.info("AppList non synchronisée : chemin Steam invalide")
            return False

        if core.profile_exceeds_applist_limit(profile):
            logging.warning(
                "AppList non synchronisée : profil %s dépasse %d entrées",
                profile.name,
                core.APPLIST_MAX_ENTRIES,
            )
            return False

        try:
            core.createFiles(profile.games)
        except (OSError, RuntimeError) as err:
            logging.exception(err)
            if popup:
                self.show_popup(i18n.tr("cannot_generate_applist"))
            return False

        logging.info("AppList synchronisée dans Steam (%d entrée(s))", len(profile.games))
        if popup:
            self.show_popup(i18n.tr("applist_generated"))
        return True

    # Util Functions
    def toggle_hidden(self, widget):
        widget.setHidden(not widget.isHidden())
        self.repaint()

    def toggle_widget(self, widget, force_close=False):
        if force_close:
            widget.setHidden(True)
            widget.setEnabled(False)
            self._sync_overlay_stack()
            return

        if widget.isHidden():
            self._layout_builder.position_overlay(widget, self.centralWidget())
            widget.setEnabled(True)
            widget.setHidden(False)
        else:
            widget.setHidden(True)
            widget.setEnabled(False)

        self._sync_overlay_stack()

    def acknowledge_manager(self):
        with core.get_config() as config:
            config.manager_msg = True
        self.hide_popup()

    def set_steam_path(self):
        path = self.main_window.steam_path.text().strip()
        if path == "":
            self.main_window.label_steam_error.setText(i18n.tr("enter_path"))
            return

        if not os.path.isdir(path):
            self.main_window.label_steam_error.setText(i18n.tr("invalid_path"))
            return

        if not core.is_valid_steam_path(path):
            self.main_window.label_steam_error.setText(i18n.tr("steam_exe_not_found"))
            return

        path = os.path.abspath(path)
        with core.get_config() as config:
            config.steam_path = path
            core.ensure_greenluma_path(config)

        self.main_window.settings_steam_path.setText(path)
        self.sync_steam_profiles()
        self.maybe_run_initial_steam_downgrade()
        self.toggle_widget(self.main_window.set_steam_path_window)

    def setup_steam_path(self):
        with core.get_config() as config:
            found = core.ensure_steam_path(config)

        self.main_window.settings_steam_path.setText(core.config.steam_path)
        if found:
            return

        guess = core.detect_steam_path()
        self.main_window.steam_path.setText(guess)
        self.main_window.label_steam_error.setText(
            i18n.tr("steam_not_detected") if not guess else ""
        )
        self.toggle_widget(self.main_window.set_steam_path_window)
        self.main_window.steam_path.setFocus()

    def set_greenluma_path(self):
        path = self.main_window.greenluma_path.text().strip()
        if path == "":
            self.main_window.label_greenluma_error.setText(i18n.tr("enter_path"))
            return

        if not os.path.isdir(path):
            self.main_window.label_greenluma_error.setText(i18n.tr("invalid_path"))
            return

        path = os.path.abspath(path)
        runtime = core.find_greenluma_runtime_path(path)
        if not core.is_valid_greenluma_path(runtime):
            if core.glinject_extract_was_blocked():
                self.main_window.label_greenluma_error.setText(
                    i18n.tr("stealth_files_blocked_defender", core.get_glinject_path())
                )
            else:
                self.main_window.label_greenluma_error.setText(i18n.tr("stealth_files_missing"))
            return

        with core.get_config() as config:
            config.greenluma_path = runtime

        self.main_window.settings_greenluma_path.setText(core.get_glinject_path())
        self.toggle_widget(self.main_window.set_greenluma_path_window)

    def setup_greenluma_path(self):
        with core.get_config() as config:
            core.ensure_greenluma_path(config)

    def drop_event_handler(self, event):
        self.add_selected()

    def hide_popup(self, event=None):
        self.toggle_widget(self.main_window.generic_popup, True)
        self.main_window.popup_btn1.setText(i18n.tr("ok"))
        self.main_window.popup_btn2.setText(i18n.tr("cancel"))

    def maybe_check_for_updates(self):
        if not core.config.check_update or "-NoUpdate" in core.sys.argv:
            return
        if self.update_check_thread and self.update_check_thread.isRunning():
            return
        self.update_check_thread = UpdateCheckThread()
        self.update_check_thread.signal.connect(self._on_update_check_finished)
        self.update_check_thread.start()

    def _on_update_check_finished(self, info):
        if not info:
            return
        ui = self.main_window
        ui.popup_btn1.setText(i18n.tr("update_download"))
        ui.popup_btn2.setText(i18n.tr("update_later"))
        self.show_popup(
            i18n.tr(
                "update_available",
                info.get("version", "?"),
                core.CURRENT_VERSION,
            ),
            lambda: self._start_update_download(info),
            self.hide_popup,
        )

    def _start_update_download(self, info):
        self.hide_popup()
        version = info.get("version", "")
        self.show_popup(i18n.tr("update_downloading", version))
        self.main_window.popup_btn1.setEnabled(False)
        self.main_window.popup_btn2.setEnabled(False)
        self.update_download_thread = UpdateDownloadThread(
            info.get("download_url", ""),
            version,
        )
        self.update_download_thread.signal.connect(self._on_update_download_finished)
        self.update_download_thread.start()

    def _on_update_download_finished(self, result):
        self.main_window.popup_btn1.setEnabled(True)
        self.main_window.popup_btn2.setEnabled(True)
        if isinstance(result, Exception):
            core.logging.exception(result)
            self.show_popup(i18n.tr("update_download_failed", result))
            return
        self.show_popup(
            i18n.tr("update_launching"),
            lambda: self._launch_downloaded_update(result),
        )

    def _launch_downloaded_update(self, installer_path):
        try:
            core.launch_setup_installer(installer_path)
        except Exception as err:
            core.logging.exception(err)
            self.show_popup(i18n.tr("update_download_failed", err))
            return
        self.quit_application()

    def show_popup(self, message, ok_callback=None, cx_callback=None):
        self.main_window.popup_text.setText(message)
        if ok_callback is None:
            ok_callback = self.hide_popup
        if cx_callback is None:
            cx_callback = self.hide_popup
        # Remove old callbacks
        try:
            self.main_window.popup_btn1.clicked.disconnect()
        except TypeError:
            pass
        try:
            self.main_window.popup_btn2.clicked.disconnect()
        except TypeError:
            pass
        self.main_window.popup_btn1.clicked.connect(ok_callback)
        self.main_window.popup_btn2.clicked.connect(cx_callback)

        if self.main_window.generic_popup.isHidden():
            self._layout_builder.position_overlay(
                self.main_window.generic_popup,
                self.centralWidget(),
            )
        self.toggle_widget(self.main_window.generic_popup)
        self.main_window.popup_btn1.setFocus()

    def is_steam_running(self):
        return core.is_steam_running()


class UpdateCheckThread(QThread):
    signal = pyqtSignal("PyQt_PyObject")

    def run(self):
        self.signal.emit(core.check_for_application_update())


class UpdateDownloadThread(QThread):
    signal = pyqtSignal("PyQt_PyObject")

    def __init__(self, download_url, version):
        super().__init__()
        self.download_url = download_url
        self.version = version

    def run(self):
        try:
            path = core.download_setup_installer(self.download_url, self.version)
            self.signal.emit(path)
        except Exception as err:
            self.signal.emit(err)


class SteamRestoreThread(QThread):
    signal = pyqtSignal("PyQt_PyObject")

    def run(self):
        try:
            core.perform_steam_restore()
            self.signal.emit(True)
        except Exception as err:
            self.signal.emit(err)


class SteamDowngradeThread(QThread):
    signal = pyqtSignal("PyQt_PyObject")

    def __init__(self, raw_url):
        super().__init__()
        self.raw_url = raw_url

    def run(self):
        try:
            package_url = core.perform_steam_downgrade(self.raw_url)
            self.signal.emit(package_url)
        except Exception as err:
            self.signal.emit(err)


class ExtractGreenLumaThread(QThread):
    signal = pyqtSignal("PyQt_PyObject")

    def __init__(self, zip_path):
        super().__init__()
        self.zip_path = zip_path

    def run(self):
        try:
            core.extract_greenluma_archive(self.zip_path)
            self.signal.emit(True)
        except Exception as err:
            self.signal.emit(err)


class InstalledBaseGamesThread(QThread):
    signal = pyqtSignal("PyQt_PyObject")

    def __init__(self, steam_path):
        super().__init__()
        self.steam_path = steam_path

    def run(self):
        try:
            self.signal.emit(core.get_installed_base_games(self.steam_path))
        except Exception as err:
            logging.exception(err)
            self.signal.emit(err)


class LoadGameConfigurationThread(QThread):
    signal = pyqtSignal("PyQt_PyObject")

    def __init__(self, steam_path, app_id, game_name, profile_name):
        super().__init__()
        self.steam_path = steam_path
        self.app_id = app_id
        self.game_name = game_name
        self.profile_name = profile_name

    def run(self):
        try:
            configuration = core.build_game_configuration(
                self.steam_path,
                self.app_id,
                self.game_name,
            )
            profile = profile_manager.profiles[self.profile_name]
            total, applied = core.apply_game_configuration(profile, configuration)
            truncated = total > applied
            self.signal.emit((self.profile_name, total, applied, truncated))
        except Exception as err:
            logging.exception(err)
            self.signal.emit(err)


class EditorTableModel(QAbstractTableModel):
    TYPES = ("Game", "DLC")
    ACTION_COLUMN = 3

    @classmethod
    def headers(cls):
        return [
            i18n.tr("editor_col_id"),
            i18n.tr("editor_col_name"),
            i18n.tr("editor_col_type"),
            "",
        ]

    @classmethod
    def type_placeholder(cls):
        return i18n.tr("editor_type_choose")

    @classmethod
    def field_placeholders(cls):
        return {
            0: i18n.tr("editor_ph_id"),
            1: i18n.tr("editor_ph_name"),
        }

    def __init__(self, rows=None, parent=None):
        super().__init__(parent=parent)
        self.rows = rows or []

    def refresh_labels(self):
        self.headerDataChanged.emit(Qt.Horizontal, 0, self.columnCount() - 1)

    def rowCount(self, parent=QModelIndex()):
        return len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 4

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        if index.column() == self.ACTION_COLUMN:
            return QVariant()
        if role in (Qt.DisplayRole, Qt.EditRole):
            value = self.rows[index.row()][index.column()]
            if index.column() == 2 and role == Qt.DisplayRole:
                return value if value in self.TYPES else self.type_placeholder()
            return value
        if index.column() == 2 and role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        return QVariant()

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False
        if index.column() == self.ACTION_COLUMN:
            return False
        value = str(value).strip()
        if index.column() == 2:
            if value == self.type_placeholder():
                value = ""
            elif value not in self.TYPES:
                value = ""
        self.rows[index.row()][index.column()] = value
        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
        return True

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers()[section]
        return QVariant()

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        if index.column() == self.ACTION_COLUMN:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def add_row(self, app_id="", name="", app_type=""):
        row = len(self.rows)
        self.beginInsertRows(QModelIndex(), row, row)
        stored_type = app_type if app_type in self.TYPES else ""
        self.rows.append([app_id, name, stored_type])
        self.endInsertRows()

    def remove_rows(self, row_indices):
        for row in sorted(set(row_indices), reverse=True):
            if row < 0 or row >= len(self.rows):
                continue
            self.beginRemoveRows(QModelIndex(), row, row)
            del self.rows[row]
            self.endRemoveRows()


class EditorTableHeader(QHeaderView):
    """Bouton + dans l'en-tête de la dernière colonne ; les lignes n'ont que la croix."""
    add_row_clicked = pyqtSignal()
    ACTION_COLUMN = 3
    ADD_BTN_SIZE = 22

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setSectionsClickable(False)
        self._add_btn = QToolButton(self)
        self._add_btn.setText("+")
        self._add_btn.setObjectName("editor_header_add_btn")
        self._add_btn.setCursor(Qt.PointingHandCursor)
        self._add_btn.setToolTip(i18n.tr("editor_add_row_tooltip"))
        self._add_btn.clicked.connect(self.add_row_clicked.emit)
        self.sectionResized.connect(self._reposition_add_btn)
        self.geometriesChanged.connect(self._reposition_add_btn)

    def showEvent(self, event):
        super().showEvent(event)
        self._reposition_add_btn()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_add_btn()

    def _reposition_add_btn(self, *_args):
        if self.count() <= self.ACTION_COLUMN:
            self._add_btn.hide()
            return
        x = self.sectionViewportPosition(self.ACTION_COLUMN)
        width = self.sectionSize(self.ACTION_COLUMN)
        btn_w = btn_h = self.ADD_BTN_SIZE
        y = max(0, (self.height() - btn_h) // 2)
        self._add_btn.setFixedSize(btn_w, btn_h)
        self._add_btn.move(x + (width - btn_w) // 2, y)
        self._add_btn.raise_()
        self._add_btn.show()


class DeleteRowDelegate(QStyledItemDelegate):
    delete_clicked = pyqtSignal(int)

    def paint(self, painter, option, index):
        painter.save()
        if option.state & QStyle.State_MouseOver:
            painter.fillRect(option.rect, QColor(Colors.SURFACE_ELEVATED))
        painter.setPen(QColor(Colors.DANGER))
        font = painter.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(option.rect, Qt.AlignCenter, "×")
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() not in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
            return False
        if event.button() != Qt.LeftButton:
            return False
        hit_rect = option.rect.adjusted(-4, -2, 4, 2)
        if not hit_rect.contains(event.pos()):
            return False
        if event.type() == QEvent.MouseButtonRelease:
            self.delete_clicked.emit(index.row())
            return True
        return True


class CellEditorDelegate(QStyledItemDelegate):
    MARGIN_H = 4
    MARGIN_V = 3

    def _placeholders(self):
        return EditorTableModel.field_placeholders()

    def _cell_text(self, index):
        value = str(index.data(Qt.EditRole) or "").strip()
        if value:
            return value
        return self._placeholders().get(index.column(), "")

    def _is_placeholder(self, index):
        value = str(index.data(Qt.EditRole) or "").strip()
        return not value and index.column() in self._placeholders()

    def paint(self, painter, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        options.text = self._cell_text(index)
        if self._is_placeholder(index):
            options.palette.setColor(QPalette.Text, QColor(Colors.TEXT_DIM))
        widget = option.widget
        if widget:
            widget.style().drawControl(QStyle.CE_ItemViewItem, options, painter, widget)

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setFrame(False)
        editor.setObjectName("editor_cell_input")
        placeholder = self._placeholders().get(index.column())
        if placeholder:
            editor.setPlaceholderText(placeholder)
        return editor

    def setEditorData(self, editor, index):
        value = index.data(Qt.EditRole)
        editor.setText(str(value) if value else "")

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(
            option.rect.adjusted(self.MARGIN_H, self.MARGIN_V, -self.MARGIN_H, -self.MARGIN_V)
        )

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        return QSize(size.width(), 36)


class TypeDelegate(QStyledItemDelegate):
    TYPES = EditorTableModel.TYPES
    MARGIN_H = 4
    MARGIN_V = 3

    def _placeholder(self):
        return EditorTableModel.type_placeholder()

    def _display_text(self, index):
        value = index.data(Qt.EditRole)
        if value in self.TYPES:
            return value
        return self._placeholder()

    def paint(self, painter, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        options.text = self._display_text(index)
        if options.text == self._placeholder():
            options.palette.setColor(QPalette.Text, QColor(Colors.TEXT_DIM))
        options.displayAlignment = Qt.AlignCenter
        widget = option.widget
        if widget:
            widget.style().drawControl(QStyle.CE_ItemViewItem, options, painter, widget)

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.setObjectName("editor_cell_combo")
        editor.addItems(list(self.TYPES))
        current = index.data(Qt.EditRole)
        if current in self.TYPES:
            editor.setCurrentText(current)
        else:
            editor.setCurrentIndex(-1)
        QTimer.singleShot(0, editor.showPopup)
        return editor

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(
            option.rect.adjusted(self.MARGIN_H, self.MARGIN_V, -self.MARGIN_H, -self.MARGIN_V)
        )

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 36)

    def setEditorData(self, editor, index):
        current = index.data(Qt.EditRole)
        if current in self.TYPES:
            editor.setCurrentText(current)
        else:
            editor.setCurrentIndex(-1)

    def setModelData(self, editor, model, index):
        text = editor.currentText()
        if text in self.TYPES:
            model.setData(index, text, Qt.EditRole)
