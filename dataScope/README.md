# DataScope: Dataset Insight & Preparation Tool

DataScope is a standalone GUI tool designed for analysts and data cleaning teams to review, understand, and prepare datasets before transformation. It includes modular responsibilities for logging, error handling, visual summaries, and input validation.

## 📦 Folder Structure

```
DataScope/
├── assets/         # Static assets like logos or templates
├── build/          # .exe or distribution builds
├── chart/          # Output charts/graphs
├── dist/           # Output from PyInstaller
├── logs/           # Log files
├── output/         # Cleaned/processed data
├── reports/        # Text/HTML reports
├── src/            # Core Python source code
│   └── gui_test_theme.py
├── tests/          # Optional: unit or integration tests
├── README.md
└── requirements.txt
```

## 💡 Key Features

- ✅ Intro Splash Screen (9-second auto-close or click-to-skip)

- ✅ Themed GUI with Navy Blue background and improved visibility for logo & text

- Modular script integration by role (Logging, Data Handling, Visualization)

- Dynamic data loading with live status indicators

- Console and GUI-linked output messaging

- Export strategy planned for PDF, HTML, and chart outputs

- Compatible for .exe compilation (via PyInstaller - TBA)


## 🧩 Roles & Modules

| Role                     | Functionality                            |  Team
|--------------------------|------------------------------------------|-------------------------------
| Logging/Error Handler    | Captures errors and runtime logs         | Kerryann Briggs & Keishan Moore
| Data Handling Developer  | Manages file input and format validation | Hadley Edwards & Glenroy Massiah
| Visual Analyst           | Produces visual summaries of data        | O'Brian Griffith
| UI/UX Developer          | Improves interface layout and flow       | Sean Cooke
| Documentation Lead       | Creates user-facing documentation        | Alesha Yarde & Marilyn Gittens

## 🚀 Setup

### 1. Create a virtual environment (optional but recommended)

```bash
python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the GUI

```bash
python src/gui_test_theme.py
```

### 4. Build as `.exe` (TBA)


## 🛠 Team Collaboration Protocol
All modules must be integrated into gui_test_theme.py as test blocks.

Each function/module should print to both the console and GUI output area.

Sections in code are clearly marked (e.g. # GUI Interface, # Intro Splash, etc.).

After testing, notify the project lead for final merging.


## 📬 0 Notes for Observers
You are not required to contribute code.

You are encouraged to review repo structure, test GUI, and comment via GitHub Issues.

Day-0 is for alignment and feedback; feature contributions begin from Day-1