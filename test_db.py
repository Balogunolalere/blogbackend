from pymongo import MongoClient
import os

mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
mongo_db_name = os.getenv("MONGODB_DB", "newsdb")
mongo_collection_name = os.getenv("MONGODB_COLLECTION", "articles")

client = MongoClient(mongo_uri)
db = client[mongo_db_name]
collection = db[mongo_collection_name]

test_doc = {"test": "mongodb connection", "status": "success"}

result = collection.insert_one(test_doc)
print("Inserted document ID:", result.inserted_id)