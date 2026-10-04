import os

from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING, MongoClient

load_dotenv()

client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
db = client[os.getenv("MONGODB_DB", "finguide")]

users = db["users"]
profiles = db["profiles"]
settings = db["settings"]
conversations = db["conversations"]
otps = db["otps"]  # one-time codes for email verification / password reset


def init_indexes() -> None:
    users.create_index([("username", ASCENDING)], unique=True)
    users.create_index([("email", ASCENDING)], unique=True)
    profiles.create_index([("user_id", ASCENDING)], unique=True)
    settings.create_index([("user_id", ASCENDING)], unique=True)
    conversations.create_index([("user_id", ASCENDING), ("updated_at", DESCENDING)])
    otps.create_index([("email", ASCENDING), ("purpose", ASCENDING)], unique=True)
    otps.create_index("expires_at", expireAfterSeconds=0)  # expired codes are removed automatically