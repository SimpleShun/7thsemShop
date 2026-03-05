import os
from flask import (
    Flask, url_for, render_template, redirect
)


from flask_htmx import HTMX

from eyes.auth import login_required


def create_app(test_config=None):
    app = Flask(__name__,instance_relative_config=True)
    app.config.from_mapping(
            SECRET_KEY='dev',
            DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )
    if test_config is None:
        app.config.from_pyfile('config.py',silent=True)
    else:
        app.config.from_pyfile(test_config)

    os.makedirs(app.instance_path, exist_ok=True)


    images = os.listdir(os.path.join(app.static_folder,"images"))
    htmx = HTMX(app)

    @app.route("/")
    def hello_world():
        return render_template('index.html')

    @app.route("/cart" , methods=["GET"])
    @login_required
    def cart():
        return render_template("partial/cart.html")


    @app.route("/preview/<img>" , methods=["GET"])
    def preview(img):
        if htmx:
            return render_template("partial/preview.html", image=img)
        return redirect(url_for("hello_world"))

    @app.route("/shop" , methods=["GET"])
    def shop():
        if htmx:
            return render_template("partial/shop.html", images=images)
        return redirect(url_for("hello_world"))

    @app.route("/navButton" , methods = ["GET"])
    def navButton():
        if htmx:
            id = htmx.trigger
            if ( id == "register" ):
                return render_template("partial/register.html")
            elif ( id == "login" ):
                return render_template("partial/login.html")
            elif ( id == "account" ):
                return render_template("partial/account.html")
            return f"<h1>{id}</h1>"
        else:
            return redirect(url_for("hello_world"))

    from . import auth
    app.register_blueprint(auth.bp)

    from . import db
    db.init_app(app)

    return app
