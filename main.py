from pathlib import Path

from PyQt6.QtCore import QTimer, QUrl, QSettings, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QToolBar,
)
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
import sys


class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("Solar", "SolarBrowser")
        self._configure_web_profile()

        self.tab_widget = QTabWidget()
        self.tab_widget.setMovable(True)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self.tab_widget)

        self.navigation_bar = QToolBar("Navigation")
        self.navigation_bar.setMovable(True)
        self.navigation_bar.setAllowedAreas(Qt.ToolBarArea.AllToolBarAreas)
        saved_area = self._load_saved_toolbar_area()
        self._saved_nav_area = saved_area
        self.addToolBar(saved_area, self.navigation_bar)
        back_button = QPushButton("<")
        back_button.clicked.connect(lambda: self._call_current_view(lambda view: view.back()))
        self.navigation_bar.addWidget(back_button)

        forward_button = QPushButton(">")
        forward_button.clicked.connect(lambda: self._call_current_view(lambda view: view.forward()))
        self.navigation_bar.addWidget(forward_button)

        reload_button = QPushButton("R")
        reload_button.clicked.connect(lambda: self._call_current_view(lambda view: view.reload()))
        self.navigation_bar.addWidget(reload_button)

        new_tab_button = QPushButton("+")
        new_tab_button.clicked.connect(lambda: self._add_new_tab())
        self.navigation_bar.addWidget(new_tab_button)

        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.load_url)
        self.navigation_bar.addWidget(self.url_bar)
        self._add_new_tab()

    def load_url(self):
        url = self.url_bar.text()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url 
        view = self._current_view()
        if view:
            view.setUrl(QUrl(url))

    def update_url_bar(self, url):
        view = self._current_view()
        if view and view.url() == url:
            self.url_bar.setText(url.toString())
            self.url_bar.setCursorPosition(0)
    

    def update_icon(self, icon: QIcon):
        self.setWindowIcon(icon)

    def _configure_web_profile(self):
        storage_dir = Path.home() / ".solar_browser"
        storage_dir.mkdir(parents=True, exist_ok=True)
        self.profile = QWebEngineProfile("SolarBrowser", self)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        self.profile.setPersistentStoragePath(str(storage_dir))
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        cache_dir = storage_dir / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.profile.setCachePath(str(cache_dir))

    def _configure_page_rendering(self, page: QWebEnginePage):
        attr_enum = QWebEngineSettings.WebAttribute
        attrs = (
            attr_enum.WebGLEnabled,
            attr_enum.Accelerated2dCanvasEnabled,
            attr_enum.FocusOnNavigationEnabled,
            attr_enum.SpatialNavigationEnabled,
        )
        settings = page.settings()
        for attr in attrs:
            settings.setAttribute(attr, False)

    def _current_view(self):
        widget = self.tab_widget.currentWidget()
        return widget if isinstance(widget, QWebEngineView) else None

    def _call_current_view(self, fn):
        view = self._current_view()
        if view:
            fn(view)

    def _add_new_tab(self, start_url="https://google.com"):
        view = QWebEngineView(self)
        page = QWebEnginePage(self.profile, view)
        view.setPage(page)
        self._configure_page_rendering(page)
        view.setUrl(QUrl(start_url))
        view.page().iconChanged.connect(lambda icon, view=view: self._update_tab_icon(view, icon))
        view.urlChanged.connect(lambda url, view=view: self._on_view_url_changed(view, url))
        view.titleChanged.connect(lambda title, view=view: self._update_tab_title(view, title))
        page.featurePermissionRequested.connect(
            lambda origin, feature, page=page: self._handle_feature_permission(page, origin, feature)
        )
        index = self.tab_widget.addTab(view, "New Tab")
        self.tab_widget.setCurrentIndex(index)

    def _on_tab_changed(self, index):
        view = self.tab_widget.widget(index)
        if isinstance(view, QWebEngineView):
            self.url_bar.setText(view.url().toString())
            self.url_bar.setCursorPosition(0)
            self.update_icon(view.icon())

    def _on_view_url_changed(self, view, url):
        if view is self._current_view():
            self.url_bar.setText(url.toString())
            self.url_bar.setCursorPosition(0)

    def _update_tab_icon(self, view, icon: QIcon):
        index = self.tab_widget.indexOf(view)
        if index != -1:
            self.tab_widget.setTabIcon(index, icon)
        if view is self._current_view():
            self.update_icon(icon)

    def _update_tab_title(self, view, title: str):
        index = self.tab_widget.indexOf(view)
        if index != -1:
            self.tab_widget.setTabText(index, title or "New Tab")

    def _handle_feature_permission(self, page, origin: QUrl, feature):
        description = self._feature_description(feature)
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Permission Request")
        dialog.setText(f"{origin.host() or origin.toString()} wants to use {description}.")
        dialog.setInformativeText("Allow this request for this session? It will be asked again next time.")
        dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dialog.setDefaultButton(QMessageBox.StandardButton.No)
        dialog.setIcon(QMessageBox.Icon.Question)
        result = dialog.exec()
        policy = QWebEnginePage.PermissionPolicy
        if result == QMessageBox.StandardButton.Yes:
            page.setFeaturePermission(origin, feature, policy.PermissionGrantedByUser)
            QTimer.singleShot(
                200,
                lambda: page.setFeaturePermission(
                    origin, feature, policy.PermissionDeniedByUser
                ),
            )
        else:
            page.setFeaturePermission(origin, feature, policy.PermissionDeniedByUser)

    def _feature_description(self, feature):
        names = {
            QWebEnginePage.Feature.MediaAudioCapture: "microphone",
            QWebEnginePage.Feature.MediaVideoCapture: "camera",
            QWebEnginePage.Feature.MediaAudioVideoCapture: "camera and microphone",
            QWebEnginePage.Feature.Geolocation: "location",
            QWebEnginePage.Feature.DesktopVideoCapture: "screen sharing",
            QWebEnginePage.Feature.Notifications: "notifications",
            QWebEnginePage.Feature.MouseLock: "mouse locking",
        }
        fallback = getattr(feature, "value", feature)
        return names.get(feature, f"feature #{fallback}")

    def _close_tab(self, index):
        view = self.tab_widget.widget(index)
        self.tab_widget.removeTab(index)
        if view:
            view.deleteLater()
        if self.tab_widget.count() == 0:
            self._add_new_tab()

    def _load_saved_toolbar_area(self):
        raw_area = self.settings.value("navBarArea")
        if raw_area is not None:
            try:
                return Qt.ToolBarArea(int(raw_area))
            except (TypeError, ValueError):
                pass
        return Qt.ToolBarArea.TopToolBarArea

    def toolBarAreaChanged(self, toolbar: QToolBar, area: Qt.ToolBarArea):
        super().toolBarAreaChanged(toolbar, area)
        if toolbar is self.navigation_bar:
            self._saved_nav_area = area

    def closeEvent(self, event):
        if hasattr(self, "_saved_nav_area"):
            self.settings.setValue("navBarArea", int(self._saved_nav_area.value))
        self.settings.sync()
        super().closeEvent(event)


app = QApplication(sys.argv)
window = Browser()
window.resize(800, 400)
window.setWindowTitle("Solar")
window.show()
sys.exit(app.exec())
