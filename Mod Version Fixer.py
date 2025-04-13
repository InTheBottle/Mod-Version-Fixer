# Attempt to import PyQt6 first, then fall back to PySide2 if PyQt6 is unavailable
try:
    from PyQt6.QtWidgets import QMessageBox, QFileDialog
    from PyQt6.QtGui import QIcon
except ImportError:
    try:
        from PySide2.QtWidgets import QMessageBox, QFileDialog
        from PySide2.QtGui import QIcon
    except ImportError:
        print("Error: Neither PyQt6 nor PySide2 could be imported.")

        class QMessageBox:
            @staticmethod
            def information(parent, title, message):
                print(f"INFO [{title}]: {message}")

            @staticmethod
            def warning(parent, title, message):
                print(f"WARNING [{title}]: {message}")

            @staticmethod
            def critical(parent, title, message):
                print(f"CRITICAL [{title}]: {message}")

        class QFileDialog:
            @staticmethod
            def getExistingDirectory(parent, caption, directory=""):
                return ""

        class QIcon:
            pass

import os
import configparser
import mobase
from typing import List

class FolderModVersionUpdater(mobase.IPluginTool):
    def __init__(self):
        super().__init__()
        self.__organizer = None  
        self.__parent_widget = None

    #
    # IPlugin interface
    #
    def init(self, organizer: mobase.IOrganizer) -> bool:
        self.__organizer = organizer  
        if not mobase:
            print("Error: mobase module not found.")
            return False
        if "QMessageBox" not in globals() or "QIcon" not in globals():
            print("Error: Required GUI library not found.")
            return False
        return True

    def name(self) -> str:
        return "Mod Version Fixer"

    def author(self) -> str:
        return "Bottle"

    def description(self) -> str:
        return (
            "Allows the user to select the mods folder (containing individual mod folders). "
            "For each mod folder, the plugin reads its meta.ini file and, if a 'newestVersion' is set "
            "and differs from the recorded 'version', updates meta.ini accordingly."
        )

    def version(self) -> mobase.VersionInfo:
        if hasattr(mobase, "VersionInfo") and hasattr(mobase, "ReleaseType"):
            return mobase.VersionInfo(1, 0, 1, mobase.ReleaseType.FINAL)
        else:
            print("Error: mobase.VersionInfo or mobase.ReleaseType not available.")
            return None

    def isActive(self) -> bool:
        return bool(mobase and "QMessageBox" in globals() and "QIcon" in globals())

    def settings(self) -> List:
        return []

    #
    # IPluginTool interface
    #
    def displayName(self) -> str:
        return "Mod Version Fixer"

    def tooltip(self) -> str:
        return (
            "Browse for your 'mods' folder (containing individual mod folders). "
            "The plugin scans each mod folder’s meta.ini file and, if 'version' differs from "
            "'newestVersion', it updates 'version' to match 'newestVersion'."
        )

    def icon(self) -> QIcon:
        if "QIcon" in globals():
            return QIcon()
        else:
            return None

    def setParentWidget(self, widget):
        self.__parent_widget = widget

    def display(self):
        if not self.isActive():
            if "QMessageBox" in globals():
                QMessageBox.warning(
                    self.__parent_widget,
                    "Plugin Error",
                    "Mod Version Fixer is not active. Check MO2 logs.",
                )
            else:
                print("Error: Plugin inactive and no GUI available.")
            return
        self.run()

    def run(self):
        """
        Attempts to pull the mods folder automatically from the organizer.
        If that fails (e.g., empty or invalid path), falls back to showing a folder
        selection dialog. Then, it processes each mod folder's meta.ini file, updating
        the version if needed, and finally refreshes MO2.
        """
        # Attempt to retrieve mods path directly from the organizer
        try:
            mods_folder = self.__organizer.modsPath()  # Use the API method provided by MO2
            if not mods_folder or not os.path.exists(mods_folder):
                raise ValueError("Invalid mods path obtained from organizer.")
        except Exception as e:
            print(f"Error retrieving mods path automatically: {e}")
            # Fallback to manual selection if automatic retrieval fails.
            mods_folder = QFileDialog.getExistingDirectory(
                self.__parent_widget,
                "Select Mods Folder",
                os.path.expanduser("~")
            )
            if not mods_folder:
                print("No folder selected; aborting update.")
                return

        updated = 0
        skipped = 0
        errors = 0
        updated_details = []

        print(f"Scanning mods folder: {mods_folder}")
        # Process each subdirectory (each mod folder)
        for item in os.listdir(mods_folder):
            mod_path = os.path.join(mods_folder, item)
            if not os.path.isdir(mod_path):
                continue

            meta_ini_path = os.path.join(mod_path, "meta.ini")
            if not os.path.exists(meta_ini_path):
                print(f"  Skipping '{item}': meta.ini not found.")
                skipped += 1
                continue

            config = configparser.ConfigParser()
            try:
                config.read(meta_ini_path, encoding="utf-8")
            except Exception as e:
                print(f"  Error reading meta.ini for '{item}': {e}")
                errors += 1
                continue

            if "General" not in config:
                print(f"  Skipping '{item}': [General] section not found in meta.ini.")
                skipped += 1
                continue

            general = config["General"]
            current_version_str = general.get("version", "").strip()
            newest_version_str = general.get("newestVersion", "").strip()

            if not newest_version_str:
                print(f"  Skipping '{item}': 'newestVersion' not set.")
                skipped += 1
                continue

            if not current_version_str:
                print(f"  '{item}': No recorded version; treating as '0.0.0'.")
                current_version_str = "0.0.0"

            # Compare raw strings; update if they differ
            if current_version_str != newest_version_str:
                print(f"  Updating '{item}': {current_version_str} → {newest_version_str}")
                general["version"] = newest_version_str
                try:
                    with open(meta_ini_path, "w", encoding="utf-8") as f:
                        config.write(f)
                    updated += 1
                    updated_details.append(f"{item}: {current_version_str} → {newest_version_str}")
                except Exception as e:
                    print(f"  Error writing updated meta.ini for '{item}': {e}")
                    errors += 1
            else:
                print(f"  '{item}' is already up-to-date (Recorded version: {current_version_str}).")

        # Build summary: show update details for updated mods, and only total counts for skipped and errors.
        summary_lines = [
            f"Mods folder scanned: {mods_folder}",
            f"Total mod folders processed: {len(os.listdir(mods_folder))}",
            f"Updated mods: {updated}",
            f"Skipped mods: {skipped}",
            f"Errors: {errors}"
        ]
        if updated_details:
            summary_lines.append("\nUpdated mod details:")
            for detail in updated_details:
                summary_lines.append(f"  • {detail}")

        summary_msg = "\n".join(summary_lines)
        print(summary_msg)

        if "QMessageBox" in globals():
            # Show the message box and wait for user dismissal.
            QMessageBox.information(self.__parent_widget, "Mod Version Fixer - Update Complete", summary_msg)
            # After the message box is closed (OK or X clicked), attempt to refresh MO2.
            if hasattr(self.__organizer, 'refresh'):
                try:
                    self.__organizer.refresh(True)
                    print("MO2 mod list refreshed (F5 simulated).")
                except Exception as e:
                    print(f"Error refreshing MO2: {e}")
            else:
                print("Organizer does not support refresh(bool).")
        else:
            print("--- Update Complete ---")
            print(summary_msg)

#
# Entry point for MO2 to load the plugin
#
def createPlugin() -> mobase.IPluginTool:
    try:
        if not mobase:
            raise ImportError("mobase module not found.")
        try:
            from PyQt6.QtWidgets import QMessageBox, QFileDialog
            from PyQt6.QtGui import QIcon
        except ImportError:
            from PySide2.QtWidgets import QMessageBox, QFileDialog
            from PySide2.QtGui import QIcon

        return FolderModVersionUpdater()
    except ImportError as e:
        print(f"Error creating plugin: Missing dependency - {e}")
        return None
    except Exception as e:
        print(f"Error creating plugin: {e}")
        return None
