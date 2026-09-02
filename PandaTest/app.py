from direct.showbase.ShowBase import ShowBase
app=ShowBase()

app.set_background_color(0,0,0,1)
app.cam.setPos(0, -5, 0)
model = app.loader.load_model("models/cylinder")
model.reparent_to(app.render)

app.run()