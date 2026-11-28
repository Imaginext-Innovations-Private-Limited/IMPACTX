import hashlib
import hmac
import os
import re
import json
import shutil
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pdfplumber
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import (
    SessionLocal,
    Document,
    Transaction,
    GSTTask,
    BusinessProfile,
    FinancialSummary,
    User,
)

app = FastAPI(title="MSME Mitra - Your AI Assistant")

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
UPLOAD_DIR = BASE_DIR / "uploads"

load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SESSION_SECRET = os.getenv("SESSION_SECRET")

if not SESSION_SECRET:
    raise RuntimeError("SESSION_SECRET is missing from backend/.env")

gemini_client = (
    genai.Client(api_key=GEMINI_API_KEY)
    if GEMINI_API_KEY else None
)

serializer = URLSafeTimedSerializer(
    SESSION_SECRET,
    salt="msme-mitra-session"
)

SESSION_MAX_AGE = 60 * 60 * 24

UPLOAD_DIR.mkdir(exist_ok=True)


# ---------------- AUTHENTICATION HELPERS ----------------

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    hashed = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1
    )
    return salt.hex() + "$" + hashed.hex()


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, hash_hex = stored_hash.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)

        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=2**14,
            r=8,
            p=1
        )

        return hmac.compare_digest(actual, expected)

    except (ValueError, TypeError):
        return False


def get_session_user_id(token):
    if not token:
        return None

    try:
        data = serializer.loads(token, max_age=SESSION_MAX_AGE)
        return int(data["user_id"])
    except (BadSignature, SignatureExpired, TypeError, KeyError, ValueError):
        return None


@app.middleware("http")
async def use_shared_user(request: Request, call_next):
    db = SessionLocal()

    try:
        shared_user = db.query(User).order_by(User.id.asc()).first()

        if not shared_user:
            return JSONResponse(
                status_code=500,
                content={"detail": "No user account found in database."}
            )

        request.state.user_id = shared_user.id

    finally:
        db.close()

    return await call_next(request)


# ---------------- AUTHENTICATION MODELS & ROUTES ----------------

class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/api/register")
def register(data: RegisterRequest):
    name = data.full_name.strip()
    email = data.email.strip().lower()

    if not name or "@" not in email or "." not in email:
        raise HTTPException(400, "Please enter valid registration details.")

    if len(data.password) < 8:
        raise HTTPException(
            400,
            "Password must contain at least 8 characters."
        )

    db = SessionLocal()

    try:
        existing = db.query(User).filter(User.email == email).first()

        if existing:
            raise HTTPException(400, "Email already registered.")

        user = User(
            full_name=name,
            email=email,
            password_hash=hash_password(data.password)
        )

        db.add(user)
        db.commit()

        return {
            "message": "Registration successful. Please log in."
        }

    finally:
        db.close()


@app.post("/api/login")
def login(data: LoginRequest, response: Response):
    db = SessionLocal()

    try:
        email = data.email.strip().lower()
        user = db.query(User).filter(User.email == email).first()

        if not user or not verify_password(
            data.password,
            user.password_hash
        ):
            raise HTTPException(401, "Invalid email or password.")

        token = serializer.dumps({"user_id": user.id})

        response.set_cookie(
            key="msme_session",
            value=token,
            httponly=True,
            secure=False,  # Localhost uses HTTP. Set True when deployed with HTTPS.
            samesite="lax",
            max_age=SESSION_MAX_AGE,
            path="/"
        )

        return {
            "message": "Login successful",
            "full_name": user.full_name
        }

    finally:
        db.close()


@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(
        key="msme_session",
        path="/",
        httponly=True,
        secure=False,
        samesite="lax"
    )

    return {"message": "Logged out successfully"}


@app.get("/api/me")
def get_current_user(request: Request):
    user_id = get_session_user_id(
        request.cookies.get("msme_session")
    )

    if not user_id:
        raise HTTPException(401, "Please log in first.")

    db = SessionLocal()

    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(401, "User account not found.")

        return {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email
        }

    finally:
        db.close()


# ---------------- HEALTH ----------------

@app.get("/api/health")
def health():
    return {"status": "connected"}


# ---------------- DOCUMENT UPLOAD ----------------

@app.post("/api/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    document_type: str = Form(...)
):
    allowed = {".pdf", ".csv", ".xlsx", ".xls"}
    extension = Path(file.filename).suffix.lower()

    if extension not in allowed:
        raise HTTPException(400, "Unsupported file format")

    filename = f"{uuid.uuid4().hex}_{Path(file.filename).name}"
    destination = UPLOAD_DIR / filename

    try:
        with destination.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        extracted_text = ""

        if extension == ".pdf":
            with pdfplumber.open(destination) as pdf:
                extracted_text = "\n".join(
                    page.extract_text() or "" for page in pdf.pages
                )

        elif extension == ".csv":
            df = pd.read_csv(destination)
            extracted_text = df.head(100).to_string(index=False)

        elif extension in [".xlsx", ".xls"]:
            df = pd.read_excel(destination)
            extracted_text = df.head(100).to_string(index=False)

        db = SessionLocal()

        try:
            record = Document(
                user_id=request.state.user_id,
                filename=Path(file.filename).name,
                document_type=document_type,
                extracted_text=extracted_text[:100000]
            )

            db.add(record)
            db.commit()
        finally:
            db.close()

        return {
            "message": "Document uploaded and processed successfully!",
            "filename": file.filename,
            "document_type": document_type,
            "extracted_text": extracted_text[:3000]
        }

    except HTTPException:
        if destination.exists():
            destination.unlink()
        raise

    except Exception as e:
        if destination.exists():
            destination.unlink()
        raise HTTPException(500, f"Document processing failed: {str(e)}")

    finally:
        await file.close()


@app.get("/api/documents")
def get_documents(request: Request):
    db = SessionLocal()
    user_id = request.state.user_id

    try:
        documents = (
            db.query(Document)
            .filter(Document.user_id == user_id)
            .order_by(Document.id.desc())
            .all()
        )

        return [
            {
                "id": d.id,
                "filename": d.filename,
                "type": d.document_type
            }
            for d in documents
        ]
    finally:
        db.close()

# ---------------- DASHBOARD ----------------

@app.get("/api/dashboard")
def get_dashboard(request: Request):
    db = SessionLocal()
    user_id = request.state.user_id

    try:
        transactions = (
            db.query(Transaction)
            .filter(Transaction.user_id == user_id)
            .all()
        )

        revenue = sum(t.income or 0 for t in transactions)
        expenses = sum(t.expense or 0 for t in transactions)
        profit = revenue - expenses

        gst_pending = (
            db.query(GSTTask)
            .filter(
                GSTTask.user_id == user_id,
                GSTTask.status == "Pending"
            )
            .count()
        )

        return {
            "revenue": revenue,
            "expenses": expenses,
            "profit": profit,
            "gst_pending": gst_pending
        }
    finally:
        db.close()

# ---------------- CASH FLOW FORECAST ----------------

@app.get("/api/forecast")
def cash_flow_forecast(request: Request):
    db = SessionLocal()
    user_id = request.state.user_id

    try:
        transactions = (
            db.query(Transaction)
            .filter(Transaction.user_id == user_id)
            .all()
        )
    finally:
        db.close()

    if not transactions:
        return {
            "message": "Upload a bank statement to generate a forecast.",
            "forecast": []
        }

    monthly_data = {}

    for transaction in transactions:
        try:
            month = datetime.strptime(
                transaction.date, "%Y-%m-%d"
            ).strftime("%Y-%m")
        except (ValueError, TypeError):
            continue

        if month not in monthly_data:
            monthly_data[month] = {"income": 0, "expenses": 0}

        monthly_data[month]["income"] += transaction.income or 0
        monthly_data[month]["expenses"] += transaction.expense or 0

    if not monthly_data:
        return {"message": "No valid transaction dates found.", "forecast": []}

    months = sorted(monthly_data.keys())[-3:]

    average_income = sum(
        monthly_data[m]["income"] for m in months
    ) / len(months)

    average_expenses = sum(
        monthly_data[m]["expenses"] for m in months
    ) / len(months)

    forecast = []

    for i in range(1, 4):
        future_month = (
            datetime.strptime(months[-1], "%Y-%m")
            + timedelta(days=32 * i)
        ).strftime("%b %Y")

        forecast.append({
            "month": future_month,
            "income": round(average_income, 2),
            "expenses": round(average_expenses, 2),
            "net_cash_flow": round(average_income - average_expenses, 2)
        })

    return {
        "forecast": forecast,
        "average_income": round(average_income, 2),
        "average_expenses": round(average_expenses, 2)
    }

# ---------------- BANK STATEMENT PROCESSING ----------------

@app.post("/api/process-bank-statement")
def process_bank_statement(request: Request):
    db = SessionLocal()
    user_id = request.state.user_id

    try:
        document = (
            db.query(Document)
            .filter(
                Document.user_id == user_id,
                Document.document_type == "bank"
            )
            .order_by(Document.id.desc())
            .first()
        )

        if not document:
            raise HTTPException(404, "Upload a bank statement first")

        file_path = next(
            (
                p for p in UPLOAD_DIR.iterdir()
                if p.name.endswith(document.filename)
            ),
            None
        )

        if not file_path:
            raise HTTPException(404, "Uploaded file not found")

        if file_path.suffix.lower() != ".csv":
            raise HTTPException(400, "For now, use a CSV bank statement")

        df = pd.read_csv(file_path)
        required = {"Date", "Description", "Amount", "Type"}

        if not required.issubset(df.columns):
            raise HTTPException(
                400,
                "CSV must contain Date, Description, Amount and Type columns"
            )

        # Replace only this user's previously imported transactions.
        db.query(Transaction).filter(
            Transaction.user_id == user_id
        ).delete(synchronize_session=False)

        for _, row in df.iterrows():
            amount = abs(float(row["Amount"]))
            transaction_type = str(row["Type"]).strip().lower()

            if transaction_type in ["credit", "income"]:
                income, expense = amount, 0
            elif transaction_type in ["debit", "expense"]:
                income, expense = 0, amount
            else:
                continue

            db.add(Transaction(
                user_id=user_id,
                date=str(row["Date"]),
                description=str(row["Description"]),
                income=income,
                expense=expense
            ))

        db.commit()

        transactions = (
            db.query(Transaction)
            .filter(Transaction.user_id == user_id)
            .all()
        )
        revenue = sum(t.income or 0 for t in transactions)
        expenses = sum(t.expense or 0 for t in transactions)

        return {
            "message": "Bank statement analyzed successfully",
            "revenue": revenue,
            "expenses": expenses,
            "profit": revenue - expenses
        }
    finally:
        db.close()

# ---------------- AI CHAT ----------------

class ChatRequest(BaseModel):
    message: str


def get_chat_business_context(http_request):
    """Short summary of the user's business so chat answers are personal."""
    db = SessionLocal()
    user_id = http_request.state.user_id
    try:
        profile = (
            db.query(BusinessProfile)
            .filter(BusinessProfile.user_id == user_id)
            .first()
        )
        if not profile:
            return ""
        snapshot = build_financial_snapshot(db, user_id)
        info = {
            "business_name": profile.business_name,
            "business_type": profile.business_type,
            "annual_turnover": profile.annual_turnover,
            "loan_requirement": profile.loan_requirement,
            "business_age_years": profile.business_age,
            "employees": profile.employees,
            "financial_snapshot": snapshot,
        }
        return (
            "\n\nThe user's business details (use them to personalise "
            "answers, but do not repeat them unless relevant): "
            + json.dumps(info, default=str)
        )
    except Exception:
        return ""
    finally:
        db.close()


@app.post("/api/chat")
def chat(request: ChatRequest, http_request: Request):
    if not gemini_client:
        raise HTTPException(500, "Gemini API key is not configured.")

    business_context = get_chat_business_context(http_request)

    for attempt in range(3):
        try:
            response = gemini_client.models.generate_content(
                model="gemini-3.6-flash",
                contents=request.message,
                config={
                    "system_instruction": (
                        "You are MSME Mitra, an AI business assistant for Indian small businesses. "
                        "Help with finance, cash flow, GST, government schemes and business growth. "
                        "Use simple English and give complete, practical answers. "
                        "For general questions, provide 4 to 6 useful points. "
                        "Never guarantee loan approval or invent government scheme rules. "
                        "Do not stop sentences midway."
                        + business_context
                    ),
                    "temperature": 0.4,
                    "max_output_tokens": 1200
                }
            )

            return {"reply": response.text}

        except Exception as e:
            error_message = str(e)

            if "503" in error_message and attempt < 2:
                time.sleep(2 ** attempt)
                continue

            if "503" in error_message:
                raise HTTPException(
                    503,
                    "Gemini is temporarily busy. Please try again shortly."
                )

            raise HTTPException(500, f"AI assistant error: {error_message}")


# ---------------- FRONTEND HOME ----------------

@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


# ---------------- GST TRACKER ----------------

class GSTTaskCreate(BaseModel):
    return_name: str
    due_date: str


@app.get("/api/gst-tasks")
def get_gst_tasks(request: Request):
    db = SessionLocal()
    user_id = request.state.user_id

    try:
        tasks = (
            db.query(GSTTask)
            .filter(GSTTask.user_id == user_id)
            .order_by(GSTTask.id)
            .all()
        )

        return [
            {
                "id": task.id,
                "return_name": task.return_name,
                "due_date": task.due_date,
                "status": task.status
            }
            for task in tasks
        ]
    finally:
        db.close()

@app.post("/api/gst-tasks")
def add_gst_task(task: GSTTaskCreate, request: Request):
    db = SessionLocal()
    user_id = request.state.user_id

    try:
        new_task = GSTTask(
            user_id=user_id,
            return_name=task.return_name,
            due_date=task.due_date,
            status="Pending"
        )

        db.add(new_task)
        db.commit()
        db.refresh(new_task)

        return {
            "message": "GST task added successfully",
            "id": new_task.id
        }
    finally:
        db.close()

@app.put("/api/gst-tasks/{task_id}/file")
def mark_gst_filed(task_id: int, request: Request):
    db = SessionLocal()
    user_id = request.state.user_id

    try:
        task = (
            db.query(GSTTask)
            .filter(
                GSTTask.id == task_id,
                GSTTask.user_id == user_id
            )
            .first()
        )

        if not task:
            raise HTTPException(404, "GST task not found")

        task.status = "Filed"
        db.commit()

        return {"message": "GST return marked as filed"}
    finally:
        db.close()

# ---------------- BUSINESS PROFILE ----------------

class BusinessProfileCreate(BaseModel):
    business_name: str
    business_type: str
    annual_turnover: float
    loan_requirement: float
    business_age: int
    employees: int
    applicant_age: int | None = None
    is_new_business: bool | None = None
    education: str | None = None
    mudra_tarun_repaid: bool | None = None
    udyam_registered: bool | None = None


@app.post("/api/business-profile")
def save_business_profile(data: BusinessProfileCreate, request: Request):
    db = SessionLocal()
    user_id = request.state.user_id

    try:
        profile = (
            db.query(BusinessProfile)
            .filter(BusinessProfile.user_id == user_id)
            .first()
        )

        if profile:
            for key, value in data.dict().items():
                setattr(profile, key, value)
        else:
            profile = BusinessProfile(
                user_id=user_id,
                **data.dict()
            )
            db.add(profile)

        db.commit()
        db.refresh(profile)

        return {"message": "Business profile saved successfully!"}
    finally:
        db.close()

@app.get("/api/business-profile")
def get_business_profile(request: Request):
    db = SessionLocal()
    user_id = request.state.user_id

    try:
        profile = (
            db.query(BusinessProfile)
            .filter(BusinessProfile.user_id == user_id)
            .first()
        )

        if not profile:
            return {"message": "No business profile found"}

        return {
            "business_name": profile.business_name,
            "business_type": profile.business_type,
            "annual_turnover": profile.annual_turnover,
            "loan_requirement": profile.loan_requirement,
            "business_age": profile.business_age,
            "employees": profile.employees
        }
    finally:
        db.close()

# ---------------- LOAN RECOMMENDATIONS ----------------

@app.get("/api/loan-recommendations")
def get_loan_recommendations(request: Request):
    db = SessionLocal()
    user_id = request.state.user_id

    try:
        profile = (
            db.query(BusinessProfile)
            .filter(BusinessProfile.user_id == user_id)
            .first()
        )

        if not profile:
            return {
                "recommendations": [],
                "message": "Please save your business profile first."
            }

        amount = profile.loan_requirement or 0
        recommendations = []

        if 0 < amount <= 50000:
            recommendations.append({
                "scheme": "PM MUDRA - Shishu",
                "category": "Loan up to ₹50,000",
                "reason": "Your loan requirement falls under the Shishu category.",
                "status": "Potential match"
            })
        elif 50000 < amount <= 500000:
            recommendations.append({
                "scheme": "PM MUDRA - Kishor",
                "category": "Loan above ₹50,000 to ₹5 lakh",
                "reason": "Your loan requirement falls under the Kishor category.",
                "status": "Potential match"
            })
        elif 500000 < amount <= 1000000:
            recommendations.append({
                "scheme": "PM MUDRA - Tarun",
                "category": "Loan above ₹5 lakh to ₹10 lakh",
                "reason": "Your loan requirement falls under the Tarun category.",
                "status": "Potential match"
            })
        elif 1000000 < amount <= 2000000:
            if profile.mudra_tarun_repaid is True:
                recommendations.append({
                    "scheme": "PM MUDRA - Tarun Plus",
                    "category": "Loan above ₹10 lakh to ₹20 lakh",
                    "reason": "You reported successfully repaying a previous Tarun loan.",
                    "status": "Potential match"
                })
            else:
                recommendations.append({
                    "scheme": "PM MUDRA - Tarun Plus",
                    "category": "Loan above ₹10 lakh to ₹20 lakh",
                    "reason": "A previous Tarun loan must be successfully repaid.",
                    "status": "Not currently matched"
                })

        if profile.is_new_business is None or profile.applicant_age is None:
            recommendations.append({
                "scheme": "PMEGP",
                "category": "New Enterprise Support",
                "reason": "Applicant age and new-business status are required.",
                "status": "More information required"
            })
        elif profile.applicant_age <= 18:
            recommendations.append({
                "scheme": "PMEGP",
                "category": "New Enterprise Support",
                "reason": "The applicant must be above 18 years of age.",
                "status": "Not eligible"
            })
        elif profile.is_new_business is False:
            recommendations.append({
                "scheme": "PMEGP",
                "category": "New Enterprise Support",
                "reason": "The new-enterprise provision is intended for new businesses.",
                "status": "Not eligible"
            })
        else:
            business_type = (profile.business_type or "").lower()
            threshold = 1000000 if "manufact" in business_type else 500000

            if amount > threshold and profile.education is None:
                status = "More information required"
                reason = "Education qualification needs verification."
            elif amount > threshold and profile.education == "Below 8th":
                status = "Not eligible"
                reason = (
                    "At least 8th-standard education is required above "
                    "the applicable project-cost threshold."
                )
            else:
                status = "Potential match"
                reason = (
                    "Your age and new-business status meet the basic checks. "
                    "Other PMEGP conditions need verification."
                )

            recommendations.append({
                "scheme": "PMEGP",
                "category": "New Enterprise Support",
                "reason": reason,
                "status": status
            })

        if amount > 0:
            recommendations.append({
                "scheme": "CGTMSE",
                "category": "Credit Guarantee Support",
                "reason": (
                    "You can explore a business loan with credit guarantee "
                    "support through a participating lender."
                ),
                "status": "Explore eligibility"
            })

        suitable = [
            item for item in recommendations
            if item["status"] == "Potential match"
        ]

        if suitable:
            best_option = suitable[0]
            suggestion = {
                "scheme": best_option["scheme"],
                "reason": best_option["reason"],
                "message": (
                    "This is the strongest preliminary match based on "
                    "your business profile."
                )
            }
        elif amount > 0:
            suggestion = {
                "scheme": "CGTMSE",
                "reason": (
                    "Explore credit guarantee support through a "
                    "participating lender."
                ),
                "message": (
                    "No clear scheme match was identified. Discuss "
                    "CGTMSE-backed finance with your lender."
                )
            }
        else:
            suggestion = {
                "scheme": "No recommendation yet",
                "reason": "Please enter your loan requirement.",
                "message": (
                    "Save your business profile to receive a "
                    "suitable suggestion."
                )
            }

        return {
            "business_name": profile.business_name,
            "loan_requirement": amount,
            "recommendations": recommendations,
            "best_option": suggestion,
            "note": (
                "These are preliminary suggestions, not loan approvals. "
                "Final eligibility depends on scheme rules and lender "
                "verification. The loan amount is only an estimate for "
                "the PMEGP education check."
            )
        }
    finally:
        db.close()

# ---------------- AI LOAN ADVISOR ----------------

ASSUMED_INTEREST_RATE = 12.0   # % per year, illustrative only
ASSUMED_TENURE_MONTHS = 60     # 5 years, illustrative only


def calculate_emi(principal, annual_rate=ASSUMED_INTEREST_RATE,
                  months=ASSUMED_TENURE_MONTHS):
    if principal <= 0:
        return 0.0
    r = annual_rate / 12 / 100
    return principal * r * (1 + r) ** months / ((1 + r) ** months - 1)


def build_financial_snapshot(db, user_id):
    """Summarise the user's uploaded transactions and GST status."""
    transactions = (
        db.query(Transaction).filter(Transaction.user_id == user_id).all()
    )
    monthly = {}
    for t in transactions:
        try:
            month = datetime.strptime(t.date, "%Y-%m-%d").strftime("%Y-%m")
        except (ValueError, TypeError):
            continue
        m = monthly.setdefault(month, {"income": 0, "expenses": 0})
        m["income"] += t.income or 0
        m["expenses"] += t.expense or 0

    gst_pending = (
        db.query(GSTTask)
        .filter(GSTTask.user_id == user_id, GSTTask.status == "Pending")
        .count()
    )

    if not monthly:
        return {"has_data": False, "gst_pending": gst_pending}

    months = sorted(monthly)[-3:]
    avg_income = sum(monthly[m]["income"] for m in months) / len(months)
    avg_expenses = sum(monthly[m]["expenses"] for m in months) / len(months)
    return {
        "has_data": True,
        "months_of_data": len(monthly),
        "avg_monthly_income": round(avg_income, 2),
        "avg_monthly_expenses": round(avg_expenses, 2),
        "avg_monthly_net_cash_flow": round(avg_income - avg_expenses, 2),
        "gst_pending": gst_pending,
    }


def build_affordability(amount, snapshot):
    emi = round(calculate_emi(amount), 2)
    result = {
        "assumed_interest_rate_percent": ASSUMED_INTEREST_RATE,
        "assumed_tenure_months": ASSUMED_TENURE_MONTHS,
        "estimated_monthly_emi": emi,
        "rating": "Unknown",
        "emi_to_net_cash_flow_percent": None,
    }
    if not snapshot.get("has_data"):
        return result

    net = snapshot["avg_monthly_net_cash_flow"]
    if net <= 0:
        result["rating"] = "High risk"
        return result

    ratio = emi / net * 100
    result["emi_to_net_cash_flow_percent"] = round(ratio, 1)
    if ratio <= 30:
        result["rating"] = "Comfortable"
    elif ratio <= 50:
        result["rating"] = "Manageable"
    else:
        result["rating"] = "Stretched"
    return result


def rule_based_advice(rec_data, affordability, snapshot):
    """Fallback used when Gemini is unavailable."""
    best = rec_data.get("best_option", {})
    return {
        "summary": (
            f"Based on your profile, {best.get('scheme', 'a government scheme')} "
            "looks like the strongest preliminary match."
        ),
        "why_this_scheme": best.get("reason", ""),
        "affordability_comment": (
            f"At an assumed {ASSUMED_INTEREST_RATE}% rate over "
            f"{ASSUMED_TENURE_MONTHS // 12} years, the EMI would be about "
            f"Rs {affordability['estimated_monthly_emi']:,.0f} per month "
            f"({affordability['rating']})."
        ),
        "documents_checklist": [
            "Aadhaar and PAN",
            "Business address proof",
            "Last 6-12 months bank statements",
            "Udyam registration (if available)",
            "GST returns (if registered)",
        ],
        "next_steps": [
            "Visit a bank or NBFC that offers the scheme",
            "Carry the documents above",
            "Ask the lender to confirm final eligibility",
        ],
        "risks": [
            "These are preliminary suggestions, not approvals.",
        ],
    }


@app.post("/api/loan-advice")
def get_ai_loan_advice(request: Request):
    # 1. Rule-based eligibility (reuses the existing recommendation logic)
    rec_data = get_loan_recommendations(request)
    if not rec_data.get("recommendations"):
        return {
            "message": rec_data.get(
                "message", "Please save your business profile first."
            ),
            "advice": None,
        }

    # 2. Financial context from uploaded bank statements + GST tracker
    db = SessionLocal()
    user_id = request.state.user_id
    try:
        profile = (
            db.query(BusinessProfile)
            .filter(BusinessProfile.user_id == user_id)
            .first()
        )
        snapshot = build_financial_snapshot(db, user_id)
        profile_info = {
            "business_name": profile.business_name,
            "business_type": profile.business_type,
            "annual_turnover": profile.annual_turnover,
            "loan_requirement": profile.loan_requirement,
            "business_age_years": profile.business_age,
            "employees": profile.employees,
            "udyam_registered": profile.udyam_registered,
        }
    finally:
        db.close()

    affordability = build_affordability(
        profile_info["loan_requirement"] or 0, snapshot
    )

    context = {
        "business_profile": profile_info,
        "financial_snapshot": snapshot,
        "affordability": affordability,
        "scheme_matches": rec_data["recommendations"],
        "best_option": rec_data["best_option"],
    }

    base = {
        "business_name": rec_data.get("business_name"),
        "loan_requirement": rec_data.get("loan_requirement"),
        "financial_snapshot": snapshot,
        "affordability": affordability,
        "best_option": rec_data["best_option"],
        "recommendations": rec_data["recommendations"],
        "disclaimer": rec_data.get("note"),
    }

    # 3. Gemini turns the verified data into personalised advice
    if not gemini_client:
        base["advice"] = rule_based_advice(rec_data, affordability, snapshot)
        base["ai_generated"] = False
        return base

    prompt = (
        "You are MSME Mitra, a loan advisor for Indian small businesses.\n"
        "Use ONLY the JSON data below. The scheme eligibility statuses were "
        "computed by our rule engine: do not change them, do not invent "
        "scheme rules, interest rates or subsidies, and never guarantee "
        "approval. The EMI uses an assumed rate and is only illustrative.\n"
        "If the business has weak or negative cash flow, say so honestly "
        "and suggest ways to improve before applying.\n\n"
        "Return ONLY a JSON object with these keys:\n"
        '"summary" (2-3 simple sentences), '
        '"why_this_scheme" (string), '
        '"affordability_comment" (string, mention EMI vs cash flow), '
        '"documents_checklist" (list of strings), '
        '"next_steps" (list of 3-5 strings), '
        '"risks" (list of strings).\n\n'
        "DATA:\n" + json.dumps(context, default=str)
    )

    advice = None
    for attempt in range(3):
        try:
            response = gemini_client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config={
                    "temperature": 0.3,
                    "max_output_tokens": 1200,
                    "response_mime_type": "application/json",
                },
            )
            text = (response.text or "").strip()
            text = re.sub(r"^```(?:json)?|```$", "", text).strip()
            advice = json.loads(text)
            break
        except json.JSONDecodeError:
            break
        except Exception as e:
            if "503" in str(e) and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            break

    if advice is None:
        base["advice"] = rule_based_advice(rec_data, affordability, snapshot)
        base["ai_generated"] = False
    else:
        base["advice"] = advice
        base["ai_generated"] = True
    return base


# ---------------- SERVE FRONTEND FILES ----------------
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")