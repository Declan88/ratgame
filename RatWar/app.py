import ctypes
import os
import sys

# Pre-load steam_api64.dll globally before any modules import py_steam_net
if sys.platform == "win32":
    dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "steam_api64.dll")
    if os.path.exists(dll_path):
        ctypes.CDLL(dll_path, mode=ctypes.RTLD_GLOBAL)
        os.add_dll_directory(os.path.dirname(dll_path))

from direct.showbase.ShowBase import ShowBase
from direct.filter.CommonFilters import CommonFilters
from panda3d.core import WindowProperties, loadPrcFileData

from scene_manager import SceneManager
from character import Character
from Networking.network_manager import NetworkManager

# High-DPI scaling
loadPrcFileData("", "win-size 1280 720")
loadPrcFileData("", "dpiaware 1")


class MyApp(ShowBase):
    def __init__(self):
        print("Hello!")
        super().__init__()
        self.disableMouse()

        self.is_fullscreen = False

        # Set clipping plane
        self.camLens.setFar(100000)

        # Allow directional light intensity >1
        self.filters = CommonFilters(self.win, self.cam)
        self.filters.setHighDynamicRange()

        # Set initial mouse/window setup
        props = WindowProperties()
        props.setCursorHidden(True)
        props.setMouseMode(WindowProperties.M_confined)
        self.win.requestProperties(props)

        # Global Application Keybinds
        self.accept("escape", self.toggle_mouse)
        self.accept("f11", self.toggle_fullscreen)
        self.accept("alt-enter", self.toggle_fullscreen)

        # Initialize Subsystems
        self.scene_mgr = SceneManager(self)
        self.scene_mgr.load_map("Maps/Test", "testmap.json")

        self.player = Character(self)

        # Initialize Network Manager at startup
        self.net_mgr = NetworkManager(self)

    def toggle_mouse(self):
        props = WindowProperties()
        is_hidden = not self.win.getProperties().getCursorHidden()
        props.setCursorHidden(is_hidden)
        props.setMouseMode(
            WindowProperties.M_confined if is_hidden else WindowProperties.M_absolute
        )
        self.win.requestProperties(props)

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        props = WindowProperties()

        user32 = ctypes.windll.user32
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)

        if self.is_fullscreen:
            width, height = screen_w, screen_h
            props.setUndecorated(True)
            props.setSize(width, height)
            props.setOrigin(0, 0)
        else:
            width, height = 1280, 720
            props.setUndecorated(False)
            props.setSize(width, height)
            props.setOrigin((screen_w - width) // 2, (screen_h - height) // 2)

        self.win.requestProperties(props)

        if self.camLens and height > 0:
            self.camLens.setAspectRatio(width / height)


if __name__ == "__main__":
    app = MyApp()
    app.run()