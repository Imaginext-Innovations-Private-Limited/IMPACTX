
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    DateTime, Boolean, ForeignKey, inspect
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./msme.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


# USER ACCOUNT
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)


# DOCUMENTS
class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    filename = Column(String)
    document_type = Column(String)
    extracted_text = Column(String)
    uploaded_at = Column(DateTime, default=datetime.now)


# TRANSACTIONS
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    date = Column(String)
    description = Column(String)
    income = Column(Float, default=0)
    expense = Column(Float, default=0)


# FINANCIAL SUMMARY
class FinancialSummary(Base):
    __tablename__ = "financial_summary"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    revenue = Column(Float, default=0)
    expenses = Column(Float, default=0)
    profit = Column(Float, default=0)


# GST TASKS
class GSTTask(Base):
    __tablename__ = "gst_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    return_name = Column(String)
    due_date = Column(String)
    status = Column(String, default="Pending")


# BUSINESS PROFILE
class BusinessProfile(Base):
    __tablename__ = "business_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    business_name = Column(String)
    business_type = Column(String)
    annual_turnover = Column(Float)
    loan_requirement = Column(Float)
    business_age = Column(Integer)
    employees = Column(Integer)

    applicant_age = Column(Integer, nullable=True)
    is_new_business = Column(Boolean, nullable=True)
    education = Column(String, nullable=True)
    mudra_tarun_repaid = Column(Boolean, nullable=True)
    udyam_registered = Column(Boolean, nullable=True)


# CREATE TABLES
Base.metadata.create_all(bind=engine)


# MIGRATE EXISTING DATABASE
with engine.begin() as conn:

    table_columns = {
        "documents": {"user_id": "INTEGER"},
        "transactions": {"user_id": "INTEGER"},
        "financial_summary": {"user_id": "INTEGER"},
        "gst_tasks": {"user_id": "INTEGER"},
        "business_profiles": {
            "user_id": "INTEGER",
            "applicant_age": "INTEGER",
            "is_new_business": "BOOLEAN",
            "education": "VARCHAR",
            "mudra_tarun_repaid": "BOOLEAN",
            "udyam_registered": "BOOLEAN"
        }
    }

    for table_name, new_columns in table_columns.items():

        existing_columns = {
            column["name"]
            for column in inspect(conn).get_columns(table_name)
        }

        for column_name, column_type in new_columns.items():

            if column_name not in existing_columns:
                conn.exec_driver_sql(
                    f"ALTER TABLE {table_name} ADD COLUMN "
                    f"{column_name} {column_type}"
                )
