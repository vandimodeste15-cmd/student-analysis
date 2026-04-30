# 🚀 Deployment Guide — Student Performance Analyzer

---

## 1 · Local Development

```bash
# Clone / unzip the project
cd student_analyzer

# Create virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — set a strong SECRET_KEY

# Run locally
python app.py
# → Open http://localhost:5000
```

The first user to register automatically becomes the **admin**.

---

## 2 · Deploy on Render (recommended — free tier)

### Step-by-step

1. Push your project to a **GitHub repository**.
2. Go to [https://render.com](https://render.com) → **New → Web Service**.
3. Connect your GitHub account and select the repository.
4. Fill in the Render form:

| Field | Value |
|-------|-------|
| **Environment** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn "app:create_app('production')" --workers 2 --bind 0.0.0.0:$PORT --timeout 120` |

5. Add **Environment Variables** (Render → Environment tab):

| Key | Value |
|-----|-------|
| `FLASK_ENV` | `production` |
| `SECRET_KEY` | *(generate a long random string)* |

6. **(Optional) Add PostgreSQL:**
   - Render → **New → PostgreSQL** → free tier.
   - In your web service, add env var:
     `DATABASE_URL` → paste the **Internal Database URL** from Render.
   - The app will auto-use it instead of SQLite.

7. Click **Deploy** — Render installs dependencies and starts gunicorn.

> **Auto-deploy:** Render redeploys on every `git push` by default.

---

## 3 · Deploy on Railway

1. Install Railway CLI: `npm i -g @railway/cli`
2. `railway login`
3. Inside the project folder:

```bash
railway init          # creates a new project
railway up            # deploys
```

4. In the Railway dashboard → **Variables**, add:
   - `FLASK_ENV=production`
   - `SECRET_KEY=<long-random-string>`
   - (Optional) Provision a **PostgreSQL** plugin → `DATABASE_URL` is injected automatically.

---

## 4 · Deploy on Heroku

```bash
heroku login
heroku create my-student-analyzer
heroku config:set FLASK_ENV=production SECRET_KEY="your-secret"
git push heroku main

# (Optional) Add Postgres
heroku addons:create heroku-postgresql:mini
# DATABASE_URL is set automatically
```

---

## 5 · Project Structure

```
student_analyzer/
├── app.py                  ← Application factory
├── config.py               ← Dev / Prod / Test configs
├── extensions.py           ← db, login_manager, migrate
├── models.py               ← User + StudentEntry ORM models
├── requirements.txt
├── Procfile                ← gunicorn start command
├── render.yaml             ← One-click Render deploy
├── .env.example
│
├── routes/
│   ├── __init__.py
│   ├── main.py             ← Home, form, live predict API
│   ├── auth.py             ← Login, register, logout
│   ├── dashboard.py        ← ML dashboard, CSV export
│   └── admin.py            ← Admin panel, user mgmt
│
├── analysis/
│   ├── __init__.py
│   └── ml_engine.py        ← All ML: SLR, MLR, PCA, KNN, K-Means
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── collect.html
│   ├── auth/
│   │   ├── login.html
│   │   └── register.html
│   ├── dashboard/
│   │   ├── overview.html
│   │   └── my_data.html
│   └── admin/
│       └── panel.html
│
└── static/
    ├── css/custom.css
    └── js/main.js
```

---

## 6 · Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | **Yes** in prod | `dev-secret-key` | Flask session signing key |
| `FLASK_ENV` | No | `development` | `development` or `production` |
| `DATABASE_URL` | No | SQLite file | Full PostgreSQL connection string |
| `PORT` | No | `5000` | Injected by Render / Railway |

---

## 7 · First-Time Setup Checklist

- [ ] `SECRET_KEY` set to a long random value in production
- [ ] Database URL configured (or SQLite file path writable)
- [ ] First user registered (becomes admin automatically)
- [ ] At least **5 data entries** submitted to unlock ML dashboard
- [ ] (Optional) Seed script run for demo data

---

## 8 · Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, Flask 3, SQLAlchemy, Flask-Login |
| ML | scikit-learn, pandas, numpy, matplotlib, seaborn |
| Frontend | Bootstrap 5.3, Bootstrap Icons, Vanilla JS |
| Database | SQLite (dev) / PostgreSQL (prod) |
| WSGI | gunicorn |
| Hosting | Render / Railway / Heroku |
