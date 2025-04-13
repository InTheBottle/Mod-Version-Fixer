try:
    from PyQt6.QtWidgets import (
        QMessageBox, QFileDialog, QDialog, QCheckBox, QVBoxLayout, QHBoxLayout,
        QDialogButtonBox, QScrollArea, QWidget, QLabel, QLineEdit
    )
    from PyQt6.QtGui import QIcon
    from PyQt6.QtCore import Qt
except ImportError:
    try:
        from PySide2.QtWidgets import (
            QMessageBox, QFileDialog, QDialog, QCheckBox, QVBoxLayout, QHBoxLayout,
            QDialogButtonBox, QScrollArea, QWidget, QLabel, QLineEdit
        )
        from PySide2.QtGui import QIcon
        from PySide2.QtCore import Qt
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
            @staticmethod
            def question(parent, title, message, buttons):
                print(f"QUESTION [{title}]: {message}")
                return 16384

        class QFileDialog:
            @staticmethod
            def getExistingDirectory(parent, caption, directory=""):
                return ""
        class QIcon:
            pass
        class QDialog:
            pass
        class QCheckBox:
            pass
        class QVBoxLayout:
            pass
        class QHBoxLayout:
            pass
        class QDialogButtonBox:
            pass
        class QScrollArea:
            pass
        class QWidget:
            pass
        class QLabel:
            pass
        class QLineEdit:
            pass
        class Qt:
            StrongFocus = None
            WheelFocus = None
            ScrollBarAsNeeded = None

import os
import configparser
import mobase
from typing import List

def parse_numeric_version(v_str: str):
    parts = v_str.split(".")
    version_nums = []
    for part in parts:
        try:
            version_nums.append(int(part))
        except ValueError:
            return None
    while len(version_nums) > 1 and version_nums[-1] == 0:
        version_nums.pop()
    return tuple(version_nums)

class ModSelectionDialog(QDialog):
    def __init__(self, mods, parent=None):
        """
        Initializes the dialog.
        :param mods: List of dictionaries for mods with mismatches.
                     Each dictionary has keys: 'mod', 'current', and 'newest'.
        """
        super().__init__(parent)
        self.setWindowTitle("Select Mods to Update")
        self.resize(550, 450)

        self.mods = mods  
        self.checkboxes = []

        mainLayout = QVBoxLayout(self)

        instructLabel = QLabel(
            "Select which mods meta.ini's you want to fix. Use \"Select All\" to toggle all quickly."
        )
        mainLayout.addWidget(instructLabel)

        self.searchBox = QLineEdit(self)
        self.searchBox.setPlaceholderText("Search mods...")
        self.searchBox.textChanged.connect(self.filterCheckboxes)
        mainLayout.addWidget(self.searchBox)

        self.selectAllCheckbox = QCheckBox("Select All")
        self.selectAllCheckbox.stateChanged.connect(self.toggleSelectAll)
        mainLayout.addWidget(self.selectAllCheckbox)

        scrollArea = QScrollArea(self)
        scrollArea.setWidgetResizable(True)

        focus_policies = []
        if hasattr(Qt, "StrongFocus") and Qt.StrongFocus is not None:
            focus_policies.append(Qt.StrongFocus)
        if hasattr(Qt, "WheelFocus") and Qt.WheelFocus is not None:
            focus_policies.append(Qt.WheelFocus)
        for policy in focus_policies:
            try:
                scrollArea.setFocusPolicy(policy)
                break
            except Exception:
                pass

        if hasattr(Qt, "ScrollBarAsNeeded") and Qt.ScrollBarAsNeeded is not None:
            scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        mainLayout.addWidget(scrollArea)

        container = QWidget()
        containerLayout = QVBoxLayout(container)
        containerLayout.setContentsMargins(10, 10, 10, 10)
        containerLayout.setSpacing(8)

        for mod in mods:
            cb_text = f"{mod['mod']}: {mod['current']} → {mod['newest']}"
            cb = QCheckBox(cb_text)
            containerLayout.addWidget(cb)
            self.checkboxes.append(cb)

        containerLayout.addStretch(1)
        scrollArea.setWidget(container)

        buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        mainLayout.addWidget(buttonBox)

        self.setLayout(mainLayout)

    def toggleSelectAll(self, state):
        """Check or uncheck all boxes depending on the 'Select All' checkbox state."""
        allChecked = (state == 2)
        for cb in self.checkboxes:
            cb.setChecked(allChecked)

    def filterCheckboxes(self, text):
        """
        Filters the list of checkboxes based on the search text.
        Only checkboxes whose text (case-insensitive) contains the search string remain visible.
        """
        filter_text = text.lower()
        for cb in self.checkboxes:
            cb.setVisible(filter_text in cb.text().lower())

    def getSelectedMods(self):
        """Return a list of mod dictionaries for which the checkbox is checked."""
        selected = []
        for mod, cb in zip(self.mods, self.checkboxes):
            if cb.isChecked():
                selected.append(mod)
        return selected

class FolderModVersionUpdater(mobase.IPluginTool):
    def __init__(self):
        super().__init__()
        self.__organizer = None  
        self.__parent_widget = None

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
            "Scans the mods folder for mods whose meta.ini 'version' differs from 'newestVersion' "
            "using a numeric comparison (ignoring trailing zeros). Displays only the total count "
            "of mismatched mods in the confirmation message, and then shows a searchable list for selections."
        )

    def version(self) -> mobase.VersionInfo:
        if hasattr(mobase, "VersionInfo") and hasattr(mobase, "ReleaseType"):
            return mobase.VersionInfo(1, 1, 0, mobase.ReleaseType.FINAL)
        else:
            print("Error: mobase.VersionInfo or mobase.ReleaseType not available.")
            return None

    def isActive(self) -> bool:
        return bool(mobase and "QMessageBox" in globals() and "QIcon" in globals())

    def settings(self) -> List:
        return []

    def displayName(self) -> str:
        return "Mod Version Fixer"

    def tooltip(self) -> str:
        return (
            "Scans your mods folder for mismatched 'version' and 'newestVersion' with numeric comparisons, "
            "and shows only a count in the summary, plus a searchable list."
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
                    "Mod Version Fixer is not active. Check MO2 logs."
                )
            else:
                print("Error: Plugin inactive and no GUI available.")
            return
        self.run()

    def run(self):
        try:
            mods_folder = self.__organizer.modsPath()
            if not mods_folder or not os.path.exists(mods_folder):
                raise ValueError("Invalid mods path obtained from organizer.")
        except Exception as e:
            print(f"Error retrieving mods path automatically: {e}")
            mods_folder = QFileDialog.getExistingDirectory(
                self.__parent_widget,
                "Select Mods Folder",
                os.path.expanduser("~")
            )
            if not mods_folder:
                print("No folder selected; aborting update.")
                return

        total_mods = 0
        skipped = 0
        errors = 0
        mods_to_update = []

        print(f"Scanning mods folder: {mods_folder}")
        for item in os.listdir(mods_folder):
            mod_path = os.path.join(mods_folder, item)
            if not os.path.isdir(mod_path):
                continue
            total_mods += 1

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

            cur_tuple = parse_numeric_version(current_version_str)
            new_tuple = parse_numeric_version(newest_version_str)

            if cur_tuple is None or new_tuple is None:
                mismatch = (current_version_str != newest_version_str)
            else:
                mismatch = (cur_tuple != new_tuple)

            if mismatch:
                mods_to_update.append({
                    "mod": item,
                    "meta_ini_path": meta_ini_path,
                    "config": config,
                    "current": current_version_str,
                    "newest": newest_version_str
                })
                print(f"  Found mismatch in '{item}': {current_version_str} → {newest_version_str}")

        if not mods_to_update:
            QMessageBox.information(
                self.__parent_widget,
                "Mod Version Fixer",
                "All mods are up-to-date. No changes needed."
            )
            return

        summary_msg = (
            f"Mods folder scanned: {mods_folder}\n"
            f"Total mod folders processed: {total_mods}\n"
            f"Mismatched mods: {len(mods_to_update)}\n\n"
            "Would you like to proceed with updating these mismatched meta.ini files?"
        )

        ret = QMessageBox.question(
            self.__parent_widget,
            "Confirm Update",
            summary_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if ret != QMessageBox.StandardButton.Yes:
            print("User cancelled the update. No changes performed.")
            return

        selection_dialog = ModSelectionDialog(mods_to_update, parent=self.__parent_widget)
        if selection_dialog.exec() == QDialog.DialogCode.Accepted:
            selected_mods = selection_dialog.getSelectedMods()
            if not selected_mods:
                QMessageBox.information(
                    self.__parent_widget,
                    "Mod Version Fixer",
                    "No mods selected. No changes performed."
                )
                return

            updated = 0
            for mod in selected_mods:
                mod["config"]["General"]["version"] = mod["newest"]
                try:
                    with open(mod["meta_ini_path"], "w", encoding="utf-8") as f:
                        mod["config"].write(f)
                    updated += 1
                    print(f"Updated '{mod['mod']}': {mod['current']} → {mod['newest']}")
                except Exception as e:
                    print(f"  Error writing updated meta.ini for '{mod['mod']}': {e}")
                    errors += 1

            final_summary = (
                f"Update complete.\n\n"
                f"Total mods processed: {total_mods}\n"
                f"Mods updated: {updated}\n"
                f"Mods skipped: {skipped}\n"
                f"Errors: {errors}"
            )
            QMessageBox.information(
                self.__parent_widget,
                "Mod Version Fixer - Update Complete",
                final_summary
            )

            if hasattr(self.__organizer, 'refresh'):
                try:
                    self.__organizer.refresh(True)
                    print("MO2 mod list refreshed (F5 simulated).")
                except Exception as e:
                    print(f"Error refreshing MO2: {e}")
            else:
                print("Organizer does not support refresh(bool).")
        else:
            QMessageBox.information(
                self.__parent_widget,
                "Mod Version Fixer",
                "No changes made. Please check for updates as needed."
            )
            print("User cancelled the checkbox dialog. No changes performed.")

def createPlugin() -> mobase.IPluginTool:
    try:
        if not mobase:
            raise ImportError("mobase module not found.")
        try:
            from PyQt6.QtWidgets import (
                QMessageBox, QFileDialog, QDialog, QCheckBox, QVBoxLayout, QHBoxLayout,
                QDialogButtonBox, QScrollArea, QWidget, QLabel, QLineEdit
            )
            from PyQt6.QtGui import QIcon
            from PyQt6.QtCore import Qt
        except ImportError:
            from PySide2.QtWidgets import (
                QMessageBox, QFileDialog, QDialog, QCheckBox, QVBoxLayout, QHBoxLayout,
                QDialogButtonBox, QScrollArea, QWidget, QLabel, QLineEdit
            )
            from PySide2.QtGui import QIcon
            from PySide2.QtCore import Qt

        return FolderModVersionUpdater()
    except ImportError as e:
        print(f"Error creating plugin: Missing dependency - {e}")
        return None
    except Exception as e:
        print(f"Error creating plugin: {e}")
        return None
