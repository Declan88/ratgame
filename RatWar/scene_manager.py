import json, os
from panda3d.core import (
    DirectionalLight,
    AmbientLight,
    Vec3,
    Vec4,
    Material,
    CullFaceAttrib,
    Texture,
    TextureStage,
)
from direct.interval.IntervalGlobal import Sequence, LerpPosInterval


# Define Class
class SceneManager:
    def __init__(self, app):
        self.app = app
        self.map_dir = ""
        self.map = self.skybox = None
        self.props = []
        self.dlight_np = None

    # Get path
    def _get_path(self, fn):
        return os.path.join(self.map_dir, fn).replace("\\", "/")

    # Add models from json to scene
    def _setup_model(self, data, mat=None, is_skybox=False):
        model = self.app.loader.loadModel(self._get_path(data["model"]))
        model.reparentTo(self.app.render)

        # Apply transforms based on json
        scale = data.get("scale", 1)
        model.setScale(*scale) if isinstance(scale, (list, tuple)) else model.setScale(
            float(scale)
        )

        if "pos" in data:
            model.setPosHprScale(
                *data["pos"], *data.get("hpr", (0, 0, 0)), *model.getScale()
            )
        # Make models with "collide" in json match the setting
        if data.get("collide"):
            model.setCollideMask(1)

        # Skybox definition (Fixing textures and lighting)
        if is_skybox:
            if "texture" in data:
                tex = self.app.loader.loadTexture(self._get_path(data["texture"]))
                if tex:
                    tex.setWrapU(Texture.WM_clamp)
                    tex.setWrapV(Texture.WM_clamp)
                    stages = model.findAllTextureStages()
                    stage = stages[0] if stages else TextureStage.getDefault()
                    stage.setMode(TextureStage.MReplace)
                    model.setTexture(stage, tex, 1)

            model.clearMaterial()
            model.setLightOff(1)
            model.setDepthWrite(False)
            model.setBin("background", 0)
        elif mat:
            model.setMaterial(mat, 1)

        # Fix face culling
        model.setAttrib(CullFaceAttrib.make(CullFaceAttrib.MCullClockwise), 1)
        return model

    # Map loading from json
    def load_map(self, map_dir="Maps/Test", json_file="testmap.json"):
        self.map_dir = map_dir
        with open(os.path.join(map_dir, json_file), "r") as f:
            data = json.load(f)

        mat = Material()
        mat.setAmbient((1, 1, 1, 1))
        mat.setDiffuse((1, 1, 1, 1))

        if "skybox" in data:
            self.skybox = self._setup_model(data["skybox"], is_skybox=True)

        self.map = self._setup_model(data["map"], mat)
        self.props = [self._setup_model(p, mat) for p in data.get("props", [])]

        # TEST FOR MOVING PROPS!!!!
        if self.props:
            Sequence(
                LerpPosInterval(
                    self.props[0], 2.0, Vec3(0, 15, 13), startPos=Vec3(0, 15, 7)
                ),
                LerpPosInterval(
                    self.props[0], 2.0, Vec3(0, 15, 7), startPos=Vec3(0, 15, 13)
                ),
            ).loop()

        # Call scene lighting
        self.setup_lighting(
            data.get("directional_light", {}), data.get("ambient_light", {})
        )

    # Setup scene lighting
    def setup_lighting(self, light_data, ambient_data={}):
        self.app.render.clearShader()

        dlight = DirectionalLight("dlight")
        d_color = light_data.get("color", [0.9, 0.9, 0.85, 1.0])
        d_intensity = light_data.get("intensity", 1.0)

        dlight.setColor(
            Vec4(
                d_color[0] * d_intensity,
                d_color[1] * d_intensity,
                d_color[2] * d_intensity,
                d_color[3],
            )
        )

        # High resolution depth map
        dlight.setShadowCaster(True, 4096, 4096)

        # Set bias tuning to prevent self-shadowing acne across flat faces
        if hasattr(dlight, "setShadowBias"):
            dlight.setShadowBias(0.0002)

        # Fit frustum bounds to cover the scene extent
        film_size = light_data.get("film_size", 80)
        dlight.getLens().setFilmSize(film_size, film_size)

        # Deep z-bounds ensure no scene geometry is clipped by the near plane
        dlight.getLens().setNearFar(10, 600)

        self.dlight_np = self.app.render.attachNewNode(dlight)

        # Pull light position far back along the direction vector to prevent frustum clipping
        target = Vec3(*light_data.get("target", [0, 15, 0]))
        self.dlight_np.setPos(target + Vec3(150, -150, 250))
        self.dlight_np.lookAt(target)

        self.app.render.setLight(self.dlight_np)

        # Ambient Light
        alight = AmbientLight("alight")
        a_color = ambient_data.get("color", [0.3, 0.3, 0.35, 1.0])
        a_intensity = ambient_data.get("intensity", 1.0)

        alight.setColor(
            Vec4(
                a_color[0] * a_intensity,
                a_color[1] * a_intensity,
                a_color[2] * a_intensity,
                a_color[3],
            )
        )
        self.app.render.setLight(self.app.render.attachNewNode(alight))

        # Auto Shader pipeline
        self.app.render.setShaderAuto()
