@echo off
echo === Kisan Mitra setup ===
python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env (
  copy .env.example .env >nul
  echo.
  echo .env created. Opening it - paste your Groq key after GROQ_API_KEY= and SAVE.
  notepad .env
)
echo.
echo Setup done. Now double-click run.bat
pause
