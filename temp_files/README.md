# 🏗️ Watchtower — Advantec Consulting Engineers

A tool distribution portal where you can upload Excel tools, share Streamlit app links, and let your team browse and download resources.

## Quick Start (Local — PyCharm)

### 1. Open in PyCharm
- Open PyCharm → **File → Open** → select this `watchtower` folder
- PyCharm will detect it as a Python project

### 2. Create virtual environment
In PyCharm's terminal (bottom panel):
```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the app
```bash
python app.py
```

### 5. Open in browser
Go to **http://localhost:5000** — that's it! Start uploading your tools.

---

## Deploy to Render.com (Free — Shareable Link)

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "Initial Watchtower release"
```
Create a new repo on GitHub, then:
```bash
git remote add origin https://github.com/YOUR_USERNAME/watchtower.git
git branch -M main
git push -u origin main
```

### 2. Deploy on Render
1. Go to [render.com](https://render.com) and sign up (free)
2. Click **New → Web Service**
3. Connect your GitHub repo
4. Render will auto-detect the `render.yaml` config
5. Click **Create Web Service**
6. Wait ~2 minutes for build
7. Your app is live at `https://watchtower-XXXX.onrender.com`

Share that URL with your team!

### Note on free tier
Render's free tier spins down after 15 min of inactivity, so the first load after idle takes ~30 seconds. The paid tier ($7/mo) keeps it always on.

---

## Project Structure
```
watchtower/
├── app.py              # Flask backend (routes, API, file handling)
├── models.py           # Database models (Tool, Screenshot)
├── requirements.txt    # Python dependencies
├── render.yaml         # Render.com deployment config
├── templates/
│   └── index.html      # Frontend (HTML + CSS + JS, all-in-one)
└── uploads/
    ├── files/          # Uploaded tool files (.xlsm, .xlsx, etc.)
    └── screenshots/    # Uploaded screenshot images
```

## Features
- **Upload Excel tools** with file attachments, descriptions, versioning
- **Share Streamlit app links** as resources alongside downloadable files
- **Screenshot uploads** to preview tools before downloading
- **Search & filter** by department (Engineering, Administration, Finance)
- **Sort** by newest, most downloaded, most viewed, or alphabetical
- **View & download tracking** — see how many people use each tool
- **Edit & delete** resources anytime
- **Tags & changelogs** for version tracking

## Customization
- **Departments**: Edit the `DEPARTMENTS` list in `templates/index.html` and the `<select>` in the upload form
- **Branding**: Change company name in the header section of `templates/index.html`
- **File types**: Edit `ALLOWED_FILE_EXT` in `app.py` to allow more file formats
