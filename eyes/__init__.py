import os , functools

from flask import (
    Flask, url_for, render_template, redirect, g , redirect , render_template , request , session , url_for
)

from werkzeug.security import check_password_hash , generate_password_hash
from eyes.db import get_db

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

    @login_required
    @app.route("/cart" , methods=["GET"])
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

    ### AUTH START
    @app.route('/register', methods=("GET","POST"))
    def register():
        if request.method == "POST":
            username = request.form["username"]
            password = request.form["password"]
            db = get_db()
            error = None

            if not username:
                error = "No username"
            elif not password:
                error = "No password"

            if error is None:
                try:
                    db.execute(
                            "INSERT INTO user (username, password) VALUES (?, ?)",
                            (username, generate_password_hash(password)),)
                    db.commit()
                except db.IntegrityError:
                    error = f"User {username} is already registered."
            else:
                return render_template("partial/register.html")
        return render_template('partial/login.html')

    @app.route("/logout")
    def logout():
        session.clear()
        return render_template("partial/login.html")


    @app.route("/login" , methods=["GET","POST"])
    def login():
        if request.method == "POST":
            username = request.form["username"]
            password = request.form["password"]
            db = get_db()
            error = None
            user = db.execute(
                        'SELECT * FROM USER WHERE USERNAME = ?',(username,)
                    ).fetchone()
            if user is None:
                error = "incorrect username"
            elif not check_password_hash(user['password'], password):
                error = 'Incorrect password.'

            if error is None:
                session.clear()
                session['user_id'] = user['id']
                return redirect(url_for('hello_world'))
        return render_template('partial/login.html')

    @app.before_request
    def load_logged_in_user():
        user_id = session.get('user_id')
        if user_id is None:
            g.user = None
        else:
            g.user = get_db().execute(
                'SELECT * FROM user WHERE id = ?', (user_id,)
            ).fetchone()
    #
    # def login_required(view):
    #     @functools.wraps(view)
    #     def wrapped_view(**kwargs):
    #         if g.user is None:
    #             return redirect(url_for('hello_world'))
    #         return view(**kwargs)
    #     return wrapped_view

    ###AUTH END

    from . import auth
    app.register_blueprint(auth.bp)

    from . import db
    db.init_app(app)

    return app
