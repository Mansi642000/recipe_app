# SyNutrify — Recipe App

Lightweight Flask recipe manager with nutrition calculation, image uploads, favorites, ratings, and PDF export support.

Features
 - Add, edit, and delete recipes (owners only)
 - Upload local images or use external image URLs
 - Nutrition calculation (local utility module)
 - Favorites, ratings, and comments
 - Local search by title and ingredients
 - Responsive UI using Bootstrap and a custom SyNutrify theme


Getting started (Windows)
1. Open a cmd.exe and navigate to the project folder:

	cd C:\\path\\to\\recipe_app

2. Create and activate a virtual environment:

	python -m venv venv
	venv\\Scripts\\activate

3. Install Python dependencies:

	python -m pip install --upgrade pip
	python -m pip install -r requirements.txt

4. Run the development server:

	python app.py

5. Open the app in your browser:

	http://127.0.0.1:5000/
	

Project layout
- `app.py` — application entrypoint and route definitions
- `config.py` — configuration (SECRET_KEY, DB URI)
- `templates/` — Jinja2 templates
- `static/` — CSS, JS, uploaded images
- `nutrition_calculator/` — nutrition helper module (pandas-backed)
- `instance/site.db` — SQLite DB (auto-created)
- `images/` — repo-level backgrounds (served at `/images/<file>`)


Important notes
- Database: The app creates `instance/site.db` automatically. Delete that file to reset the DB.
- Image uploads: Uploaded files are saved under `static/uploads/`. Templates use `recipe.image_url` (either static URL or external URL).
- Background images: The app serves the repository `images/` folder via a `/images/<file>` route. Confirm `images/bg1.jpg`, `bg2.jpg`, `lrbg.jpg`, and `allrbg.jpg` exist if you rely on hero backgrounds.
- Dataset : The dataset used for calculating nutitional values is from Indian Nutrient Databank https://www.anuvaad.org.in/indian-nutrient-databank/

Security
- CSRF protection is enabled via Flask-WTF. Forms include hidden CSRF tokens.
- Authentication is via Flask-Login. Only recipe owners may edit or delete recipes.


Troubleshooting
- ModuleNotFoundError: ensure your venv is active and `pip install -r requirements.txt` completed.
- Missing background images: open `http://127.0.0.1:5000/images/bg1.jpg` to confirm the server serves the files.
- PDF export fails: check the server log for WeasyPrint or wkhtmltopdf errors; fallback HTML will still be shown.


Development notes & next steps
- Nutrition utilities are lazy-imported inside routes to keep startup fast (pandas is heavy).
- Consider adding server-side image resizing, icons (Font Awesome), or unit tests (pytest) for the nutrition utilities.
