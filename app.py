import os
from flask import Flask, render_template, redirect, url_for,make_response, flash, request ,jsonify
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from flask_wtf import CSRFProtect
from flask import send_from_directory
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange, ValidationError , URL ,Optional
from werkzeug.utils import secure_filename
from uuid import uuid4
from urllib.parse import urlencode
import shutil

 
# ...existing code... (removed FileField import since we use image URL instead)
# --- App setup ---
app = Flask(__name__)
app.config.from_object(Config)

# Serve images folder (project-level) at /images/
@app.route('/images/<path:filename>')
def project_image(filename):
    return send_from_directory(os.path.join(basedir, 'images'), filename)

# Upload configuration: store uploaded images under static/uploads
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)
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
    # allow decimal calories input (we store floats rounded to 2 decimals)
    calories = StringField("Calories (optional)")
    # Allow either an uploaded image or an image URL
    image_file = FileField("Upload image", validators=[FileAllowed(['jpg','png','jpeg'], 'Images only!')])
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
    # provide small forms for rating and commenting so they can be used inline
    rating_form = RatingForm()
    comment_form = CommentForm()
    return render_template("recipes.html", recipes=all_recipes, rating_form=rating_form, comment_form=comment_form)


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




 
os.environ['WKHTMLTOPDF_PATH'] = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
@app.route('/recipe/<int:recipe_id>/export')
@login_required
def export_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    html = render_template('recipe_print.html', recipe=recipe)

    # --- Try WeasyPrint ---
    try:
        from weasyprint import HTML
        pdf = HTML(string=html).write_pdf()
    except Exception as e:
        app.logger.warning(f"WeasyPrint failed: {e}")
        pdf = None

    # --- Try pdfkit if WeasyPrint fails ---
    if pdf is None:
        try:
            import pdfkit
            wk_path = os.getenv('WKHTMLTOPDF_PATH') or shutil.which('wkhtmltopdf')
            config = pdfkit.configuration(wkhtmltopdf=wk_path) if wk_path else None
            pdf = pdfkit.from_string(html, False, configuration=config)
        except Exception as e:
            app.logger.warning(f"pdfkit failed: {e}")
            pdf = None

    # --- Return PDF if generated ---
    if pdf:
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=recipe_{recipe.id}.pdf'
        return response

    # --- Fallback ---
    flash("PDF export not available. Use Print → Save as PDF.", "warning")
    return render_template("recipe_print.html", recipe=recipe)




@app.route("/recipe/new", methods=["GET", "POST"])
@login_required
def add_recipe():
    form = RecipeForm()
    if form.validate_on_submit():
        ingredients_list = [i.strip() for i in form.ingredients.data.split(',')]
        # import nutrition utils lazily to avoid heavy startup imports (pandas)
        from nutrition_calculator.nutrition_utils import calculate_recipe_nutrition
        nutrition_totals = calculate_recipe_nutrition(ingredients_list)
        # decide image path: prefer uploaded file, fall back to provided URL
        image_path = None
        if form.image_file.data:
            f = form.image_file.data
            # generate secure unique filename
            filename = secure_filename(f.filename)
            unique = f"{uuid4().hex}_{filename}"
            dest = os.path.join(app.config['UPLOAD_FOLDER'], unique)
            f.save(dest)
            # save relative URL for templates
            image_path = url_for('static', filename=f'uploads/{unique}')
        elif form.image_url.data:
            image_path = form.image_url.data

        # If user manually entered calories, prefer that (parse to float)
        manual_cal = None
        if form.calories.data and str(form.calories.data).strip():
            try:
                manual_cal = float(str(form.calories.data).strip())
            except Exception:
                manual_cal = None

        recipe = Recipe(
            title=form.title.data,
            ingredients=form.ingredients.data,
            instructions=form.instructions.data,
            image_url=image_path,
            youtube_url=form.youtube_url.data,
            user_id=current_user.id,
            calories=round(manual_cal, 2) if manual_cal is not None else round(nutrition_totals.get("calories", 0), 2),
            proteins=round(nutrition_totals.get("proteins", 0), 2),
            fats=round(nutrition_totals.get("fats", 0), 2),
            carbs=round(nutrition_totals.get("carbs", 0), 2),
            fibers=round(nutrition_totals.get("fibers", 0), 2)
        )
        db.session.add(recipe)
        db.session.commit()
        flash("Recipe added successfully with nutrition info!", "success")
        return redirect(url_for("recipes"))
    return render_template("add_recipe.html", form=form)

@app.route('/calculate_nutrition', methods=['POST'])
def calculate_nutrition():
    try:
        data = request.get_json()
        ingredients = [i.strip() for i in data.get('ingredients', '').split(',') if i.strip()]
        from nutrition_calculator.nutrition_utils import calculate_recipe_nutrition
        result = calculate_recipe_nutrition(ingredients)
        return jsonify(result)
    except Exception as e:
        # Return the error message for debugging (temporary)
        import traceback
        tb = traceback.format_exc()
        app.logger.error('calculate_nutrition error:\n' + tb)
        return jsonify({'error': str(e), 'trace': tb}), 500

@app.route("/recipe/<int:recipe_id>/edit", methods=["GET", "POST"])
@login_required
def edit_recipe(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None or recipe.user_id != current_user.id:
        flash("You cannot edit this recipe!", "danger")
        return redirect(url_for("recipes"))
    form = RecipeForm(obj=recipe)
    if form.validate_on_submit():
        recipe.title = form.title.data
        recipe.ingredients = form.ingredients.data
        recipe.instructions = form.instructions.data
        # handle uploaded file or URL
        if form.image_file.data:
            f = form.image_file.data
            filename = secure_filename(f.filename)
            unique = f"{uuid4().hex}_{filename}"
            dest = os.path.join(app.config['UPLOAD_FOLDER'], unique)
            f.save(dest)
            recipe.image_url = url_for('static', filename=f'uploads/{unique}')
        elif form.image_url.data:
            recipe.image_url = form.image_url.data
        recipe.youtube_url = form.youtube_url.data
        ingredients_list = [i.strip() for i in form.ingredients.data.split(',')]
        nutrition_totals = calculate_recipe_nutrition(ingredients_list)
        # If user provided a manual calories override, use it
        if form.calories.data and str(form.calories.data).strip():
            try:
                recipe.calories = round(float(str(form.calories.data).strip()), 2)
            except Exception:
                recipe.calories = round(nutrition_totals.get("calories", 0), 2)
        else:
            recipe.calories = round(nutrition_totals.get("calories", 0), 2)
            recipe.proteins = round(nutrition_totals.get("proteins", 0), 2)
            recipe.fats = round(nutrition_totals.get("fats", 0), 2)
            recipe.carbs = round(nutrition_totals.get("carbs", 0), 2)
            recipe.fibers = round(nutrition_totals.get("fibers", 0), 2)
        db.session.commit()
        flash("Recipe updated with new nutrition info!", "success")
        return redirect(url_for("recipe_detail", recipe_id=recipe.id))
    else :
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
        from nutrition_calculator.nutrition_utils import calculate_recipe_nutrition
        totals = calculate_recipe_nutrition(ingredients_list)
        matched = ingredients_list
    return render_template("nutrition_lookup.html", totals=totals, matched=matched)


@app.route('/__debug_calc')
def debug_calc():
    # debug-only endpoint: call nutrition util directly with querystring
    q = request.args.get('ingredients', '')
    try:
        from nutrition_calculator.nutrition_utils import calculate_recipe_nutrition
        ing = [i.strip() for i in q.split(',') if i.strip()]
        res = calculate_recipe_nutrition(ing)
        return jsonify(res)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        app.logger.error('debug_calc error:\n' + tb)
        return jsonify({'error': str(e), 'trace': tb}), 500


def normalize_text(s):
    return (s or '').strip().lower()


@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    ingredients = request.args.get('ingredients', '').strip()

    local_results = []
    external_results = []

    if q:
        # search by recipe title or ingredients in local DB
        q_like = f"%{q}%"
        local_results = Recipe.query.filter(
            (Recipe.title.ilike(q_like)) | (Recipe.ingredients.ilike(q_like))
        ).all()

    if ingredients:
        # search local DB for any recipe that contains all provided ingredients (comma-separated)
        needed = [i.strip().lower() for i in ingredients.split(',') if i.strip()]
        if needed:
            # naive approach: filter by ingredients text containing each ingredient
            query = Recipe.query
            for ing in needed:
                query = query.filter(Recipe.ingredients.ilike(f"%{ing}%"))
            local_ing_results = query.all()
            # merge unique
            for r in local_ing_results:
                if r not in local_results:
                    local_results.append(r)

    # external results removed — local-only search

    return render_template('search_results.html', q=q, ingredients=ingredients, local_results=local_results, external_results=external_results)

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
