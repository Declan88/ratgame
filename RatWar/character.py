from panda3d.core import (
    Vec3,
    CollisionNode,
    CollisionCapsule,
    CollisionHandlerPusher,
    CollisionTraverser,
    ButtonHandle,
)


class Character:
    def __init__(self, app):
        self.app = app
        self.heading = self.pitch = 0.0
        self.speed, self.sens = 15.0, 15.0
        self.velocity_z, self.gravity, self.jump_force = 0.0, -32.0, 12.0

        # Create base player node for movement/rotation (Upright)
        self.node = app.render.attachNewNode("player")
        self.node.setZ(15.0)

        # Reparent camera to player node for pitch control
        app.camera.reparentTo(self.node)
        app.camera.setPos(0, 0, 0)

        # FOV Configuration
        self._fov = 90.0
        self.fov = 90.0

        # Setup Collision Capsule attached to player root
        app.cTrav, app.pusher = CollisionTraverser(), CollisionHandlerPusher()
        col = self.node.attachNewNode(CollisionNode("playerCapsule"))
        col.node().addSolid(CollisionCapsule(0, 0, -4.5, 0, 0, -1.2, 1.2))
        col.node().setFromCollideMask(1)
        col.node().setIntoCollideMask(0)

        app.pusher.addCollider(col, self.node)
        app.cTrav.addCollider(col, app.pusher)
        app.taskMgr.add(self.update, "char_update")

    @property
    def fov(self):
        return self._fov

    @fov.setter
    def fov(self, val):
        self._fov = val
        if self.app.camLens:
            self.app.camLens.setFov(val)

    def update(self, task):
        dt, mw = globalClock.getDt(), self.app.mouseWatcherNode

        # Mouse Look
        if mw.hasMouse() and self.app.win.getProperties().getCursorHidden():
            self.heading -= mw.getMouseX() * self.sens
            self.pitch = max(-89.0, min(89.0, self.pitch + mw.getMouseY() * self.sens))

            # Rotate player node horizontally, camera vertically
            self.node.setH(self.heading)
            self.app.camera.setP(self.pitch)
            self.app.win.movePointer(
                0, self.app.win.getXSize() // 2, self.app.win.getYSize() // 2
            )

        # Movement Inputs (Relative to upright player node)
        btn = mw.is_button_down
        x = btn(ButtonHandle("d")) - btn(ButtonHandle("a"))
        y = btn(ButtonHandle("w")) - btn(ButtonHandle("s"))

        self.node.setPos(self.node, Vec3(x, y, 0) * self.speed * dt)

        # Jump & Gravity Logic
        if self.app.pusher.has_contact() and self.velocity_z <= 0:
            self.velocity_z = self.jump_force if btn(ButtonHandle("space")) else 0.0
        else:
            self.velocity_z += self.gravity * dt

        self.node.setZ(
            self.app.render, self.node.getZ(self.app.render) + self.velocity_z * dt
        )
        return task.cont
