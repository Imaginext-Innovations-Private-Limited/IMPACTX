
import os

from pymongo import MongoClient, ASCENDING, DESCENDING
from dotenv import load_dotenv

load_dotenv()


# -----------------------------------------
# MONGODB CONFIGURATION
# -----------------------------------------

MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb://localhost:27017"
)

DATABASE_NAME = os.getenv(
    "DATABASE_NAME",
    "aquawatch"
)


# -----------------------------------------
# DATABASE CONNECTION
# -----------------------------------------

client = MongoClient(
    MONGODB_URI,
    serverSelectionTimeoutMS=5000
)

db = client[DATABASE_NAME]


# -----------------------------------------
# CHECK DATABASE CONNECTION
# -----------------------------------------

def check_database():

    try:
        client.admin.command("ping")

        print("MongoDB connected successfully!")

        return True

    except Exception as error:

        print("MongoDB connection error:", error)

        return False


# -----------------------------------------
# CREATE COLLECTIONS AND INDEXES
# -----------------------------------------

def create_collections():

    try:

        collections = [
            "users",
            "reports",
            "detections",
            "complaints",
            "lakes",
            "water_readings"
        ]

        existing = db.list_collection_names()

        for collection in collections:

            if collection not in existing:

                db.create_collection(collection)

                print(f"Created collection: {collection}")

            else:

                print(f"Collection already exists: {collection}")


        # ---------------------------------
        # USER INDEXES
        # ---------------------------------

        db.users.create_index(
            [("email", ASCENDING)],
            unique=True
        )


        # ---------------------------------
        # REPORT INDEXES
        # ---------------------------------

        db.reports.create_index(
            [("created_at", DESCENDING)]
        )

        db.reports.create_index(
            [("status", ASCENDING)]
        )

        db.reports.create_index(
            [("user_id", ASCENDING)]
        )


        # ---------------------------------
        # COMPLAINT INDEXES
        # ---------------------------------

        db.complaints.create_index(
            [("complaint_id", ASCENDING)],
            unique=True
        )


        # ---------------------------------
        # WATER QUALITY INDEXES
        # ---------------------------------

        db.water_readings.create_index(
            [("source", ASCENDING)]
        )

        db.water_readings.create_index(
            [("data_type", ASCENDING)]
        )


        print("AquaWatch database collections and indexes ready!")

        return True

    except Exception as error:

        print("Collection creation error:", error)

        return False


# -----------------------------------------
# CLOSE DATABASE CONNECTION
# -----------------------------------------

def close_database():

    client.close()

    print("MongoDB connection closed.")
