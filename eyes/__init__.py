import os , functools

from flask import (
    Flask,send_from_directory ,  flash,url_for, render_template, redirect, g , redirect , render_template , request , session , url_for
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

    @app.route("/add_to_cart", methods=["POST"])
    def add_to_cart():
        product = request.form.get("product")
        if "cart" not in session:
            session["cart"] = []
        session["cart"].append({
            "name": product,
            "price": 10
        })

        session.modified = True

        # cart_items = session["cart"]
        # total = sum(item["price"] for item in cart_items)

        return "",204

        # return render_template(
        #     "partial/cart.html",
        #     cart_items=cart_items,
        #     total=total
        # )

    @app.route("/cart-total", methods=["GET"])
    @login_required
    def cart_total():
        cart = session.get("cart", [])
        total = sum(item["price"] for item in cart)
        return f"<strong>Total: Rs {total}</strong>"


    @app.route("/remove-from-cart", methods=["POST"])
    def remove_from_cart():
        item_id = request.form.get("item_id")

        # Example if cart is stored in session
        cart = session.get("cart", [])

        for i, item in enumerate(cart):
             if item["name"] == item_id:
                 cart.pop(i)   # remove only the first matching item
                 break

        session["cart"] = cart
        total = sum(item["price"] for item in cart)
        return ("",204)
        # return render_template(
        #     "partial/cart.html",
        #     cart_items=cart,
        #     total=total
        # )
        # return redirect("/cart")

    @login_required
    @app.route("/cart" , methods=["GET"])
    def cart():
        cart_items = session["cart"]
        total = sum(item["price"] for item in cart_items)
        return render_template(
            "partial/cart.html",
            cart_items=cart_items,
            total=total
        )

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
                db = get_db()
                user_id = g.user['id']
                cur = db.execute("SELECT filename FROM purchased_images WHERE user_id = ?", (user_id,))
                purchased_images = cur.fetchall()
                return render_template("partial/account.html" , purchased_images=purchased_images)
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
        return render_template('index.html')

    @app.route("/logout")
    def logout():
        session.clear()
        return render_template("partial/login.html")

    @app.route("/change-password", methods=["POST"])
    @login_required
    def change_password():
        old_pass = request.form.get("old_password")
        new_pass = request.form.get("new_password")
        db = get_db()
        user_id = g.user['id']

        # Fetch current hashed password from SQLite
        cur = db.execute("SELECT password FROM user WHERE id = ?", (user_id,))
        row = cur.fetchone()
        if not row or not row["password"]:
            return "<p style='color:red'>No current password set.</p>"

        stored_password = row["password"]

        # Verify old password
        if not check_password_hash(stored_password, old_pass):
            return "<p style='color:red'>Current password is incorrect.</p>"

        # Hash new password and update in DB
        new_hashed = generate_password_hash(new_pass)
        db.execute("UPDATE user SET password = ? WHERE id = ?", (new_hashed, user_id))
        db.commit()
        return "<p style='color:green'>Password changed successfully!</p>"
        

    @app.route("/download/<filename>")
    @login_required
    def download_image(filename):
        uploads = os.path.join(app.root_path, "static/images")
        return send_from_directory(uploads, filename, as_attachment=True)

    @app.route("/checkout", methods=["POST"])
    @login_required
    def checkout():
        cart_items = session.get("cart", [])
        if not cart_items:
            return redirect(url_for("index"))

        db = get_db()
        user_id = g.user['id']

        # Move cart items to purchased_images table
        for item in cart_items:
            filename = item["name"]
            # Check if this user already purchased this file
            cur = db.execute(
                "SELECT 1 FROM purchased_images WHERE user_id = ? AND filename = ?",
                (user_id, filename)
            )
            if not cur.fetchone():  # Only insert if not already purchased
                db.execute(
                    "INSERT INTO purchased_images (user_id, filename) VALUES (?, ?)",
                    (user_id, filename)
                )
        db.commit()

        # Clear cart
        session["cart"] = []
        return "" ,204

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

    ###AUTH END

    from . import auth
    app.register_blueprint(auth.bp)

    from . import db
    db.init_app(app)

    return app
