import os
from flask import Flask, render_template, redirect, url_for, flash, request ,jsonify
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange, ValidationError , URL ,Optional
from nutrition_calculator.nutrition_utils import get_nutrition, calculate_recipe_nutrition

# --- App setup ---
app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# --- Models ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    recipes = db.relationship("Recipe", backref="user", lazy=True)
    ratings = db.relationship("Rating", backref="user", lazy=True)
    comments = db.relationship("Comment", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False) 
    image_url = db.Column(db.String(300))        # New: for recipe image
    ingredients = db.Column(db.Text, nullable=False)
        # Main macronutrients
    calories = db.Column(db.Float)
    proteins = db.Column(db.Float)
    fats = db.Column(db.Float)
    carbs = db.Column(db.Float)
    fibers = db.Column(db.Float)

    instructions = db.Column(db.Text, nullable=False)
    youtube_url = db.Column(db.String(300))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    ratings = db.relationship("Rating", backref="recipe", lazy=True)
    comments = db.relationship("Comment", backref="recipe", lazy=True)


class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, nullable=False)  # 1-5
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipe.id"), nullable=False)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipe.id"), nullable=False)

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipe.id"), nullable=False)

    user = db.relationship("User", backref="favorites")
    recipe = db.relationship("Recipe", backref="favorited_by")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- Forms ---
class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=150)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=128)])
    password2 = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Register")

    def validate_username(self, username):
        if User.query.filter_by(username=username.data).first():
            raise ValidationError("Username already taken. Choose another.")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class RecipeForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    ingredients = TextAreaField("Ingredients", validators=[DataRequired()])
    instructions = TextAreaField("Instructions", validators=[DataRequired()])
    calories = IntegerField("Calories (optional)")
    image_url = StringField("Image URL", validators=[Optional(), URL()])
    youtube_url = StringField("YouTube Link", validators=[Optional(), URL()])
    submit = SubmitField("Save")


class RatingForm(FlaskForm):
    score = IntegerField("Rate 1–5", validators=[DataRequired(), NumberRange(min=1, max=5)])
    submit = SubmitField("Submit Rating")


class CommentForm(FlaskForm):
    content = TextAreaField("Add a comment", validators=[DataRequired()])
    submit = SubmitField("Post Comment")


# --- Routes ---
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash("Logged in successfully.", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/recipes")
@login_required
def recipes():
    all_recipes = Recipe.query.all()
    return render_template("recipes.html", recipes=all_recipes)


@app.route("/recipe/<int:recipe_id>")
@login_required
def recipe_detail(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    rating_form = RatingForm()
    comment_form = CommentForm()
    is_favorite=any(f.user_id == current_user.id for f in recipe.favorited_by)
    return render_template(
        "recipe_detail.html",
        recipe=recipe,
        rating_form=rating_form,
        comment_form=comment_form,
        is_favorite=is_favorite
    )


@app.route("/recipe/new", methods=["GET", "POST"])
@login_required
def add_recipe():
    form = RecipeForm()
    if form.validate_on_submit():
        ingredients_list = [i.strip() for i in form.ingredients.data.split(',')]
        nutrition_totals = calculate_recipe_nutrition(ingredients_list)
        recipe = Recipe(
            title=form.title.data,
            ingredients=form.ingredients.data,
            instructions=form.instructions.data,
            image_url=form.image_url.data,
            youtube_url=form.youtube_url.data,
            user_id=current_user.id,
            calories=nutrition_totals.get("calories", 0),
            proteins=nutrition_totals.get("proteins", 0),
            fats=nutrition_totals.get("fats", 0),
            carbs=nutrition_totals.get("carbs", 0),
            fibers=nutrition_totals.get("fibers", 0)
        )
        db.session.add(recipe)
        db.session.commit()
        flash("Recipe added successfully with nutrition info!", "success")
        return redirect(url_for("recipes"))
    return render_template("add_recipe.html", form=form)

@app.route('/calculate_nutrition', methods=['POST'])
def calculate_nutrition():
    data = request.get_json()
    ingredients = [i.strip() for i in data.get('ingredients', '').split(',') if i.strip()]
    result = calculate_recipe_nutrition(ingredients)
    return jsonify(result)

@app.route("/recipe/<int:recipe_id>/edit", methods=["GET", "POST"])
@login_required
def edit_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    if recipe.user_id != current_user.id:
        flash("You cannot edit this recipe!", "danger")
        return redirect(url_for("recipes"))
    form = RecipeForm(obj=recipe)
    if form.validate_on_submit():
        recipe.title = form.title.data
        recipe.ingredients = form.ingredients.data
        recipe.instructions = form.instructions.data
        recipe.image_url = form.image_url.data
        recipe.youtube_url = form.youtube_url.data
        ingredients_list = [i.strip() for i in form.ingredients.data.split(',')]
        nutrition_totals = calculate_recipe_nutrition(ingredients_list)
        recipe.calories = nutrition_totals.get("calories", 0)
        recipe.proteins = nutrition_totals.get("proteins", 0)
        recipe.fats = nutrition_totals.get("fats", 0)
        recipe.carbs = nutrition_totals.get("carbs", 0)
        recipe.fibers = nutrition_totals.get("fibers", 0)

        db.session.commit()
        flash("Recipe updated with new nutrition info!", "success")
        return redirect(url_for("recipe_detail", recipe_id=recipe.id))
    return render_template("add_recipe.html", form=form, edit=True)


@app.route("/recipe/<int:recipe_id>/delete", methods=["POST"])
@login_required
def delete_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    if recipe.user_id != current_user.id:
        flash("You cannot delete this recipe!", "danger")
        return redirect(url_for("recipes"))
    db.session.delete(recipe)
    db.session.commit()
    flash("Recipe deleted.", "info")
    return redirect(url_for("recipes"))


@app.route("/recipe/<int:recipe_id>/rate", methods=["POST"])
@login_required
def rate_recipe(recipe_id):
    form = RatingForm()
    if form.validate_on_submit():
        existing = Rating.query.filter_by(user_id=current_user.id, recipe_id=recipe_id).first()
        if existing:
            existing.score = form.score.data
        else:
            new_rating = Rating(score=form.score.data, user_id=current_user.id, recipe_id=recipe_id)
            db.session.add(new_rating)
        db.session.commit()
        flash("Rating submitted!", "success")
    return redirect(url_for("recipe_detail", recipe_id=recipe_id))


@app.route("/recipe/<int:recipe_id>/comment", methods=["POST"])
@login_required
def comment_recipe(recipe_id):
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(content=form.content.data, user_id=current_user.id, recipe_id=recipe_id)
        db.session.add(comment)
        db.session.commit()
        flash("Comment added!", "success")
    return redirect(url_for("recipe_detail", recipe_id=recipe_id))

@app.route("/recipe/<int:recipe_id>/favorite", methods=["POST"])
@login_required
def favorite_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    existing = Favorite.query.filter_by(user_id=current_user.id, recipe_id=recipe_id).first()
    if existing:
        db.session.delete(existing)  # unfavorite
        flash("Removed from favorites.", "info")
    else:
        fav = Favorite(user_id=current_user.id, recipe_id=recipe_id)
        db.session.add(fav)
        flash("Added to favorites!", "success")
    db.session.commit()
    return redirect(url_for("recipe_detail", recipe_id=recipe_id))

@app.route("/nutrition_lookup", methods=["GET", "POST"])
def nutrition_lookup():
    totals = None
    matched = None
    if request.method == "POST":
        ingredients_list = [i.strip() for i in request.form['ingredients'].split(',')]
        totals = calculate_recipe_nutrition(ingredients_list)
        matched = ingredients_list
    return render_template("nutrition_lookup.html", totals=totals, matched=matched)

@app.route("/favorites")
@login_required
def favorites():
    favs = Favorite.query.filter_by(user_id=current_user.id).all()
    return render_template("favorites.html", favorites=favs)


@app.route("/my_recipes")
@login_required
def my_recipes():
    user_recipes = Recipe.query.filter_by(user_id=current_user.id).all()
    return render_template("my_recipes.html", recipes=user_recipes)


if __name__ == "__main__":
    os.makedirs(os.path.join(os.path.dirname(__file__), "instance"), exist_ok=True)
    with app.app_context():
        db.create_all()
    app.run(debug=True)
