from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from dotenv import load_dotenv
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from models import Review_Trustpilot, Review_Tripadvisor, Google_Business_Data
from urllib.parse import urlparse, unquote
from datetime import datetime, timezone
import re
import logging
from pymongo import DESCENDING, ASCENDING, ReturnDocument, InsertOne, UpdateOne
import json
from pymongo import ReturnDocument
from bson import json_util
import mysql.connector
from mysql.connector import Error
from auth import get_db_connection
import motor.motor_asyncio
from pymongo import errors
import asyncio
from pymongo.errors import ConnectionFailure, OperationFailure
from motor.motor_asyncio import AsyncIOMotorDatabase

load_dotenv()

logger = logging.getLogger(__name__)
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME_REPORTS = "Reports"
def audit_request(request: BaseModel) -> str:
    """Request an audit from the database, and return the id of the audit"""
    audit_client = MongoClient(MONGODB_URI)
    try:
        audit_collection = audit_client["Audits"]["Audits_Insights"]
        request_dict = request.model_dump()
        current_time = datetime.now()
        document = {"date": current_time, "request": request_dict, "status": "pending"}
        result = audit_collection.insert_one(document)
        return str(result.inserted_id)
    except Exception as e:
        raise Exception(f"Failed to create audit request: {str(e)}")
    finally:
        audit_client.close()
 
def update_audit(id: str, status: str, outscraper_id: Optional[str] = None ):
    """Update the audit status in the database"""
    client = MongoClient(os.getenv("MONGODB_URI"))
    try:
        if outscraper_id:
            audit_collection = client["Audits"]["Audits_Insights"]
            audit_collection.update_one(
                {"_id": ObjectId(id)},
                {"$set": {"status": status, "outscraper_id": outscraper_id}}
            )
        else:
            audit_collection = client["Audits"]["Audits_Insights"]
            audit_collection.update_one(
                {"_id": ObjectId(id)},
                {"$set": {"status": status}}
            )
    except Exception as e:
        raise Exception(f"Failed to update audit status: {str(e)}")
    finally:
        client.close()
 
def upload_truspilot_reviews(reviews_data: List[dict], job_id: str) -> List[str]:
    """Upload the gathered and processed review data (list of dicts) to the database,
       avoiding duplicates based on 'review' text. Associates with MySQL job_id.
       Assumes reviews_data comes from DataProcessor and is largely conformant."""
    client = MongoClient(os.getenv("MONGODB_URI"))
    inserted_ids_str = []
    reviews_to_insert = []
    skipped_count = 0
    logger.info(f"[Trustpilot DB Upload - Job {job_id}] Starting upload process.")
    try:
        reviews_collection = client["Reviews"]["reviews_trustpilot_gold"]

        # 1. Get review texts to check for duplicates
        review_texts_to_check = [rd.get("review") for rd in reviews_data if isinstance(rd.get("review"), str) and rd.get("review").strip()]
        existing_texts = set()

        # 2. Check existing texts in DB
        if review_texts_to_check:
            try:
                existing_reviews_cursor = reviews_collection.find(
                    {"review": {"$in": review_texts_to_check}},
                    {"review": 1, "_id": 0}
                )
                existing_texts = {doc["review"] for doc in existing_reviews_cursor}
                logger.info(f"[Trustpilot DB Check - Job {job_id}] Found {len(existing_texts)} existing reviews out of {len(review_texts_to_check)} candidates.")
            except Exception as find_e:
                logger.error(f"[Trustpilot DB Check - Job {job_id}] Error checking existing reviews: {find_e}. Proceeding without duplicate check.")
                existing_texts = set()

        # 3. Prepare list of new reviews
        for review_dict in reviews_data:
            # review_dict is expected to come from DataProcessor and contain:
            # 'audit_id', 'brand_name', 'source', 'country', 'date' (datetime),
            # 'rating' (int), 'review', 'sentiment', 'emotion', 'topic', 'created_at' (datetime)

            review_text = review_dict.get("review")
            if isinstance(review_text, str) and review_text.strip() and review_text not in existing_texts:
                # The DataProcessor should have already set 'audit_id' to job_id
                # and 'created_at'. The 'date' field should also be a datetime object.
                # No further modifications to review_dict are needed here if DataProcessor is correct.
                reviews_to_insert.append(review_dict)
            elif isinstance(review_text, str) and review_text.strip():
                skipped_count += 1

        # 4. Insert new reviews
        if not reviews_to_insert:
            logger.warning(f"[Trustpilot DB Upload - Job {job_id}] No new reviews to insert. Skipped {skipped_count} duplicates.")
        else:
            result = reviews_collection.insert_many(reviews_to_insert)
            inserted_ids_str = [str(oid) for oid in result.inserted_ids]
            logger.info(f"[Trustpilot DB Upload - Job {job_id}] Inserted {len(inserted_ids_str)} new reviews. Skipped {skipped_count} duplicates.")

    except Exception as e:
        # Log the error, but let the caller handle the main job status update
        logger.error(f"[Trustpilot DB Upload - Job {job_id}] Failed to upload reviews: {e}", exc_info=True)
        # Return empty list to indicate failure to the caller
        return []
    finally:
        client.close()
        logger.info(f"[Trustpilot DB Upload - Job {job_id}] MongoDB connection closed.")

    return inserted_ids_str
 
def upload_tripadvisor_reviews(reviews: List[Review_Tripadvisor], audit_id: str)->List[str]:
    """Upload the gathered reviews to the database, alongside the audit id"""
    client = MongoClient(os.getenv("MONGODB_URI"))
    print("Got here")
    try:
        reviews_collection = client["Reviews"]["Reviews_Tripadvisor"]
        reviews_to_insert = [
            {**review.model_dump(), "audit_id": audit_id}
            for review in reviews
        ]
        result = reviews_collection.insert_many(reviews_to_insert)
        print(result.inserted_ids)
        return result.inserted_ids
    except Exception as e:
        update_audit(audit_id, "error")
        raise Exception(f"Failed to upload reviews: {str(e)}")
    finally:
        client.close()
 
def upload_google_reviews(reviews: List[Google_Business_Data], audit_id: str)->List[str]:
    """Upload the gathered reviews to the database, alongside the audit id"""
    client = MongoClient(os.getenv("MONGODB_URI"))
    try:
        reviews_collection = client["Reviews"]["reviews_google_gold"]
        reviews_to_insert = [
            {**review.model_dump(), "audit_id": audit_id}
            for review in reviews
        ]
        result = reviews_collection.insert_many(reviews_to_insert)
        print(result.inserted_ids)
        return result.inserted_ids
    except Exception as e:
        update_audit(audit_id, "error")
        raise Exception(f"Failed to upload reviews: {str(e)}")
    finally:
        client.close()
 
def grab_reviews_from_db(audit_id: str)->List:
    """Grab the reviews from the database, given an audit id"""
    client = MongoClient(os.getenv("MONGODB_URI"))
    try:
        db = client["Reviews"]
        all_reviews = []
        for collection_name in db.list_collection_names():
            collection = db[collection_name]
            reviews = collection.find({"audit_id": audit_id})
 
            converted_reviews = []
            #add also the collection name to the review
            for review in reviews:
                if '_id' in review:
                    review['_id'] = str(review['_id'])
                review['collection'] = collection_name
                converted_reviews.append(review)
           
            all_reviews.extend(converted_reviews)
        return all_reviews
    except Exception as e:
        raise Exception(f"Failed to grab reviews: {str(e)}")
    finally:
        client.close()
 
def get_job_status_from_db(id: str)->str:
    """Get the status of a job, given an audit id"""
    client = MongoClient(os.getenv("MONGODB_URI"))
    try:
        audit_collection = client["Audits"]["Audits_Insights"]
        audit = audit_collection.find_one({"_id": ObjectId(id)})
        return audit["status"]
    except Exception as e:
        raise Exception(f"Failed to get job status: {str(e)}")
    finally:
        client.close()
 
def exists_audit_id_from_db(_id: str, id_type: List[str] = ["outscraper_id", "audit_id"])->bool:
    """Grab the audit from the database, given an outscraper id or audit id"""
    client = MongoClient(os.getenv("MONGODB_URI"))
    audit = None # Initialize audit to None
    try:
        audit_collection = client["Audits"]["Audits_Insights"]
        query = {}
        if "outscraper_id" in id_type and "audit_id" in id_type:
             # If both are possible, check ObjectId first
             try:
                 query = {"_id": ObjectId(_id)}
                 audit = audit_collection.find_one(query)
             except Exception: # Handle invalid ObjectId format
                 audit = None
             if not audit: # If not found by ObjectId, try outscraper_id
                 query = {"outscraper_id": _id}
                 audit = audit_collection.find_one(query)
        elif "audit_id" in id_type:
            try:
                query = {"_id": ObjectId(_id)}
                audit = audit_collection.find_one(query)
            except Exception:
                audit = None # Invalid ObjectId format
        elif "outscraper_id" in id_type:
            query = {"outscraper_id": _id}
            audit = audit_collection.find_one(query)
        else:
            print("Warning: Invalid id_type specified in exists_audit_id_from_db")
            # raise Exception("Invalid id type") # Or just return False
            return False
        return audit is not None
    except Exception as e:
        print(f"Error checking audit existence: {str(e)}")
        # Consider whether to raise or return False on general error
        return False # Safer option
    finally:
        client.close()

def audit_id_from_db(_id: str, id_type: List[str] = ["outscraper_id", "audit_id"]):
    """Grab the audit document from the database, given an outscraper id or audit id"""
    client = MongoClient(os.getenv("MONGODB_URI"))
    audit = None
    try:
        audit_collection = client["Audits"]["Audits_Insights"]
        query = {}
        # Similar logic as exists_audit_id_from_db to find the document
        if "outscraper_id" in id_type and "audit_id" in id_type:
             try:
                 query = {"_id": ObjectId(_id)}
                 audit = audit_collection.find_one(query)
             except Exception:
                 audit = None
             if not audit:
                 query = {"outscraper_id": _id}
                 audit = audit_collection.find_one(query)
        elif "audit_id" in id_type:
            try:
                query = {"_id": ObjectId(_id)}
                audit = audit_collection.find_one(query)
            except Exception:
                audit = None
        elif "outscraper_id" in id_type:
            query = {"outscraper_id": _id}
            audit = audit_collection.find_one(query)
        else:
            print("Warning: Invalid id_type specified in audit_id_from_db")
            return None

        # Convert _id to string if document found
        if audit and '_id' in audit:
             audit['_id'] = str(audit['_id'])

        return audit
    except Exception as e:
        print(f"Error grabbing audit document: {str(e)}")
        return None # Return None on error
    finally:
        client.close()

 
 
def extract_company_name_tripadvisor(query):
    if query.startswith("http"):  
        parsed_url = urlparse(query)
        path_parts = parsed_url.path.strip("/").split("/")
 
        if "Reviews" in path_parts[-1]:  
            last_part = path_parts[-1].split("-")
           
            filtered_parts = [part for part in last_part if not re.match(r"^[g|d]\d+$", part)]
           
            #Tomar solo la parte del nombre del negocio (eliminar "Reviews" y la ciudad)
            name_index = filtered_parts.index("Reviews") + 1 if "Reviews" in filtered_parts else 1
            name = "_".join(filtered_parts[name_index:-1])
           
            name = unquote(name)
        else:
            name = "Desconocido"
    else:
        name = query
 
    name = re.sub(r"[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]", "", name).strip().replace(" ", "_")
    return name

async def query_single_collection_async(db, coll_name, query_filter, projection, collection_map):
    """Helper function to query one collection asynchronously."""
    try:
        collection = db[coll_name]
        logger.debug(f"Executing async query on '{coll_name}': Filter={query_filter}")
        cursor = collection.find(query_filter, projection)
        reviews_from_coll = await cursor.to_list(length=None) # Asynchronously fetch all

        # Post-process (similar logic as before)
        processed_reviews = []
        for review in reviews_from_coll:
            if 'date' in review and isinstance(review['date'], datetime):
                review['date'] = review['date'].isoformat() + 'Z'
            # Fallback logic...
            if coll_name == collection_map.get("druni") and 'sentiment' not in review and 'rating' in review:
                 # ... (sentiment logic using review.get('rating'))
                 pass # Placeholder for brevity
            processed_reviews.append(review)

        logger.info(f"Found {len(processed_reviews)} reviews in '{coll_name}'.")
        return processed_reviews
    except Exception as e:
        logger.error(f"Error querying or processing collection '{coll_name}' async: {e}", exc_info=True)
        return [] # Return empty list on error for this collection


async def query_reviews_for_report_async(start_date: Optional[str], end_date: Optional[str], sources: List[str], countries: List[str], brand_name: str) -> List[dict]:
    """Async version: Query MongoDB for reviews based on filters for report generation."""
    client = None
    all_reviews = []
    logger.info(f"query_reviews_for_report_async called with:")
    logger.info(f"  start_date: {start_date} (type: {type(start_date)})")
    logger.info(f"  end_date: {end_date} (type: {type(end_date)})")
    logger.info(f"  sources: {sources}")
    logger.info(f"  countries: {countries}")
    logger.info(f"  brand_name: {brand_name}")

    # --- 1. Validate and Parse Dates ---
    start_dt: Optional[datetime] = None
    end_dt: Optional[datetime] = None

    try:
        if start_date: # Only parse if start_date is not None and not an empty string
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:   # Only parse if end_date is not None and not an empty string
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except ValueError:
        logger.error(f"Invalid date format provided. start_date='{start_date}', end_date='{end_date}'")
        return [] # Or handle error as appropriate

    # --- 2. Connect to MongoDB (using motor) ---
    try:
        mongo_uri = os.getenv("MONGODB_URI")
        client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000)
        await client.admin.command('ismaster') # Check connection async
        db = client["Reviews"]
        logger.info("Successfully connected to MongoDB (async).")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB async at {mongo_uri}: {e}")
        return []

    # --- 3. Determine Collections (Same as before) ---
    collection_map = { # Same map
        "trustpilot": "reviews_trustpilot_gold",
        "tripadvisor": "reviews_tripadvisor_gold",
        "google": "reviews_google_gold",
        "druni": "reviews_druni_gold",
        "amazon": "reviews_amazon_gold"
    }
    collections_to_query = [collection_map[s.lower()] for s in sources if s.lower() in collection_map]
    # ... (logger and empty check)

    # --- 4. Build Base Query and Projection ---
    query_filter_base: Dict[str, Any] = {
        "brand_name": { "$regex": f"^{re.escape(brand_name)}$", "$options": "i" }
    }

    # Conditionally add date filter
    if start_dt and end_dt:
        query_filter_base["date"] = {"$gte": start_dt, "$lte": end_dt}
    elif start_dt: # Only start_date is provided
        query_filter_base["date"] = {"$gte": start_dt}
    elif end_dt:   # Only end_date is provided
        query_filter_base["date"] = {"$lte": end_dt}
    # If neither start_dt nor end_dt is present (e.g., "All Time"), no date filter is added.

    if countries:
        uppercase_countries = [c.upper() for c in countries]
        query_filter_base["country"] = {"$in": uppercase_countries}
    
    projection = {"_id": 0, "audit_id": 0}


    # --- 5. Create and Run Query Tasks Concurrently ---
    tasks = []
    for coll_name in collections_to_query:
        # Pass necessary args to the helper
        tasks.append(query_single_collection_async(db, coll_name, query_filter_base.copy(), projection, collection_map))

    # Gather results from all tasks
    results_list = await asyncio.gather(*tasks) # Runs queries concurrently

    # --- 6. Combine Results ---
    for results in results_list:
        all_reviews.extend(results) # results is the list returned by the helper

    # --- 7. Cleanup and Return ---
    if client:
        client.close() # Motor client close is synchronous
        logger.info("MongoDB connection closed.")

    logger.info(f"Total reviews fetched for report: {len(all_reviews)}")
    return all_reviews

# helper/utilsdb.py
# ... other imports (MongoClient, os, logger, datetime, update_audit) ...
from pymongo.errors import BulkWriteError
from typing import List, Dict, Any
import pandas as pd # Import pandas for date conversion check

# ... other functions ...

def upload_cleaned_google_reviews(reviews_data: List[Dict], audit_id: str) -> List[str]:
    """Upload the gathered and processed Google review data (list of dicts) to the database."""
    client = MongoClient(os.getenv("MONGODB_URI"))
    logger.info(f"[Google DB Upload - Job {audit_id}] Connecting to MongoDB...")
    try:
        reviews_collection = client["Reviews"]["reviews_google_gold"] # Save to gold collection
        reviews_to_insert = []
        now_mongo = datetime.now(timezone.utc).replace(tzinfo=None) # Use timezone-aware UTC, then make naive for Mongo

        for review_dict in reviews_data:
            # Convert date if necessary (assuming 'date' column exists and is datetime or ISO string)
            if 'date' in review_dict:
                 if isinstance(review_dict['date'], str):
                     try:
                         if review_dict['date'].endswith('Z'):
                             review_dict['date'] = review_dict['date'].replace('Z', '+00:00')
                         review_dict['date'] = datetime.fromisoformat(review_dict['date']).replace(tzinfo=None) # Store naive
                     except (ValueError, TypeError):
                         print(f"Advertencia [Google]: No se pudo convertir la fecha {review_dict.get('date')} a datetime.")
                         review_dict['date'] = None # Set to None if conversion fails
                 elif isinstance(review_dict['date'], datetime):
                     review_dict['date'] = review_dict['date'].replace(tzinfo=None) # Ensure naive
                 # else: keep as is if already None or other type

            review_dict["audit_id"] = audit_id
            review_dict["created_at"] = now_mongo # Align with user schema 'created_at'
            review_dict.pop("processed_at", None) # Remove old 'processed_at' if it exists
            review_dict["source"] = review_dict.get("source", "Google") # Ensure source is Google


            reviews_to_insert.append(review_dict)

        if not reviews_to_insert:
            logger.warning(f"[Google DB Upload - Job {audit_id}] No processed Google reviews to insert into MongoDB.")
            return []

        logger.info(f"[Google DB Upload - Job {audit_id}] Attempting to insert {len(reviews_to_insert)} reviews...")
        result = reviews_collection.insert_many(reviews_to_insert)
        inserted_ids_str = [str(oid) for oid in result.inserted_ids]
        logger.info(f"[Google DB Upload - Job {audit_id}] Inserted {len(inserted_ids_str)} processed Google reviews into MongoDB.")
        return inserted_ids_str
    except Exception as e:
        logger.error(f"[Google DB Upload - Job {audit_id}] Failed to upload reviews: {e}", exc_info=True)
        try:
            # update_audit is deprecated, use update_job_status_mysql if job status needs update here
            # For now, primary job status update is handled in the scraper function.
            pass
        except Exception as audit_e:
             logger.error(f"Failed to update audit status after DB error: {audit_e}")
        return [] 
    finally:
        if client:
            client.close()
            logger.info(f"[Google DB Upload - Job {audit_id}] MongoDB connection closed.")

def upload_google_place_data(place_data: Dict, job_id: str, actual_brand_name: Optional[str] = None) -> Optional[str]:
    """Uploads a single Google Place data dictionary to MongoDB collection 'reviews_google_places_gold'."""
    client = MongoClient(os.getenv("MONGODB_URI"))
    logger.info(f"[Google Place DB Upload - Job {job_id}] Attempting to save place data for '{place_data.get('name', 'Unknown Place')}' with brand '{actual_brand_name}'.")
    try:
        db = client["Reviews"] 
        collection = db["reviews_google_places_gold"]

        place_data_to_save = place_data.copy() 
        place_data_to_save["audit_id"] = job_id # This is the job_id from the scraping task
        if actual_brand_name: # Add the brand_name if provided
            place_data_to_save["brand_name"] = actual_brand_name
        else:
            # Fallback if actual_brand_name is not provided for some reason, though it should be
            place_data_to_save["brand_name"] = place_data.get("query") # Or another field from place_data as fallback
            logger.warning(f"[Google Place DB Upload - Job {job_id}] actual_brand_name not provided, using query '{place_data.get('query')}' as fallback brand_name for place '{place_data.get('name')}'.")

        place_data_to_save["created_at"] = datetime.now(timezone.utc).replace(tzinfo=None)

        if not place_data_to_save.get('google_id') and not place_data_to_save.get('place_id'):
            logger.warning(f"[Google Place DB Upload - Job {job_id}] Place data for '{place_data.get('name')}' missing google_id and place_id. Skipping save.")
            return None
        
        # Using simple insert for now:
        result = collection.insert_one(place_data_to_save)
        inserted_id_str = str(result.inserted_id)

        if inserted_id_str:
            logger.info(f"[Google Place DB Upload - Job {job_id}] Successfully saved place data for '{place_data.get('name')}' with DB ID: {inserted_id_str}.")
            return inserted_id_str
        else:
            logger.error(f"[Google Place DB Upload - Job {job_id}] Failed to save place data for '{place_data.get('name')}'.")
            return None
            
    except Exception as e:
        logger.error(f"[Google Place DB Upload - Job {job_id}] Failed to upload place data for '{place_data.get('name')}': {e}", exc_info=True)
        return None
    finally:
        if client:
            client.close()

def save_report_to_mongodb(brand_name: str, report_type: str, html_content: str, filters: dict, user_id: int, archetype_identifier: Optional[str] = None, archetype_full_details: Optional[dict] = None) -> bool:
    """Saves the generated HTML report content and its metadata (including archetype info) to MongoDB."""
    if not MONGODB_URI:
        logger.error("MongoDB URI not found, cannot save report to DB.")
        return False

    client = None
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000) # Added timeout
        # The ismaster command is cheap and does not require auth.
        client.admin.command('ismaster')
        logger.info("Successfully connected to MongoDB for saving report.")
        
        # Use brand_name for the database name
        db_name = brand_name.lower().replace(' ', '_') # Parameterize DB name
        db = client[db_name] # Select DB based on brand_name

        # Parameterize collection name
        collection_name = f"informes_{brand_name.lower().replace(' ', '_')}"
        collection = db[collection_name]

        # Create the document to insert
        report_document = {
            "brand_name": brand_name,
            "report_type": report_type,
            "html_content": html_content,
            "filters": filters,
            "user_id": user_id,
            "generated_at": datetime.now(timezone.utc),
            "archetype_identifier": archetype_identifier if archetype_identifier else "General", # Store the ID/name passed, or 'General'
            "archetype_details": archetype_full_details # Store the full details dict, or None
        }

        # Insert the document
        insert_result = collection.insert_one(report_document)
        
        if insert_result.inserted_id:
            logger.info(f"Report type '{report_type}' for brand '{brand_name}' successfully saved to MongoDB collection '{collection_name}' with ID: {insert_result.inserted_id}")
            return True
        else:
            logger.error(f"Failed to insert report for brand '{brand_name}' into MongoDB collection '{collection_name}'. No ID returned.")
            return False

    except errors.ServerSelectionTimeoutError as timeout_err:
        logger.error(f"MongoDB connection timed out: {timeout_err}")
        return False
    except errors.ConnectionFailure as conn_err:
        logger.error(f"Failed to connect to MongoDB: {conn_err}")
        return False
    except Exception as e:
        logger.error(f"An error occurred while saving report to MongoDB: {e}", exc_info=True)
        return False
    finally:
        if client:
            client.close()
            logger.info("MongoDB client closed.")

def get_mongo_client():
    """Creates and returns a MongoDB client, handling potential errors."""
    try:
        uri = os.getenv("MONGODB_URI")
        if not uri:
            logger.error("MONGODB_URI environment variable not set.")
            return None
        # Added serverSelectionTimeoutMS for quicker failure detection
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # The ismaster command is cheap and does not require auth.
        client.admin.command('ismaster')
        logger.info("Successfully connected to MongoDB.")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}", exc_info=True)
        return None

def fetch_generated_reports_for_brand(brand_name: str) -> List[Dict]:
    """Fetches all generated reports for a specific brand from MongoDB."""
    client = get_mongo_client()
    if not client:
        logger.error("Cannot fetch generated reports: MongoDB connection failed.")
        return []

    reports_list = []
    try:
        # Parameterize DB and Collection name based on brand
        sanitized_db_name = brand_name.lower().replace(' ', '_')
        db = client[sanitized_db_name] # Use the sanitized name
        # Collection name is 'informes_{brand_name}'
        collection_name = f"informes_{brand_name.lower().replace(' ', '_')}"
        collection = db[collection_name] # Select collection

        # Fetch reports sorted by creation date descending
        # Exclude bulky HTML content from the list view
        reports_cursor = collection.find({}, {'html_content': 0}).sort("generated_at", DESCENDING)

        for report in reports_cursor:
            report["_id"] = str(report["_id"]) # Convert ObjectId to string
            # Convert datetime to ISO string for JSON compatibility
            if 'generated_at' in report and isinstance(report['generated_at'], datetime):
                 report['generated_at'] = report['generated_at'].isoformat()
            # Convert filters dates if they exist and are datetime
            if 'filters' in report and isinstance(report['filters'], dict):
                if 'start_date' in report['filters'] and isinstance(report['filters'].get('start_date'), datetime):
                    report['filters']['start_date'] = report['filters']['start_date'].isoformat()
                if 'end_date' in report['filters'] and isinstance(report['filters'].get('end_date'), datetime):
                    report['filters']['end_date'] = report['filters']['end_date'].isoformat()

            reports_list.append(report)

        logger.info(f"Fetched {len(reports_list)} reports for brand '{brand_name}' from DB '{sanitized_db_name}', collection '{collection_name}'.")

    except Exception as e:
        logger.error(f"Error fetching reports for brand '{brand_name}' from MongoDB: {e}", exc_info=True)
        return [] # Return empty list on error
    finally:
        if client:
            client.close()
            logger.info("MongoDB connection closed after fetching reports.")

    return reports_list

def fetch_single_generated_report(report_id: str, expected_brand_name: str) -> Optional[Dict]:
    """Fetches a single generated report by its ID, ensuring brand match."""
    client = get_mongo_client()
    if not client:
        logger.error("Cannot fetch single report: MongoDB connection failed.")
        return None

    report_data = None
    try:
        # Validate ObjectId string
        try:
            object_id = ObjectId(report_id)
        except Exception as e:
            logger.error(f"Invalid report ID format: {report_id}")
            return None

        # Parameterize DB and Collection name
        sanitized_db_name = expected_brand_name.lower().replace(' ', '_')
        db = client[sanitized_db_name] # Use the sanitized name
        collection_name = f"informes_{expected_brand_name.lower().replace(' ', '_')}"
        collection = db[collection_name] # Select collection

        report_data = collection.find_one({"_id": object_id})

        if report_data:
            # Explicitly check brand_name within the document for extra security
            if report_data.get("brand_name") != expected_brand_name:
                logger.warning(f"Access denied: Report {report_id} brand '{report_data.get('brand_name')}' does not match expected brand '{expected_brand_name}'.")
                return None # Or raise HTTPException(status_code=403)

            report_data["_id"] = str(report_data["_id"]) # Convert ObjectId
            # Convert datetime to ISO string
            if 'generated_at' in report_data and isinstance(report_data['generated_at'], datetime):
                 report_data['generated_at'] = report_data['generated_at'].isoformat()
            # Convert filters dates if they exist and are datetime
            if 'filters' in report_data and isinstance(report_data['filters'], dict):
                if 'start_date' in report_data['filters'] and isinstance(report_data['filters'].get('start_date'), datetime):
                    report_data['filters']['start_date'] = report_data['filters']['start_date'].isoformat()
                if 'end_date' in report_data['filters'] and isinstance(report_data['filters'].get('end_date'), datetime):
                    report_data['filters']['end_date'] = report_data['filters']['end_date'].isoformat()

            logger.info(f"Successfully fetched report {report_id} for brand '{expected_brand_name}'.")
        else:
            logger.warning(f"Report with ID {report_id} not found in DB '{sanitized_db_name}', collection '{collection_name}'.")

    except Exception as e:
        logger.error(f"Error fetching report ID {report_id} for brand '{expected_brand_name}' from MongoDB: {e}", exc_info=True)
        return None # Return None on error
    finally:
        if client:
            client.close()
            logger.info("MongoDB connection closed after fetching single report.")

    return report_data

def delete_generated_report(report_id: str, expected_brand_name: str) -> bool:
    """Deletes a single generated report by its ID, ensuring brand match."""
    client = get_mongo_client()
    if not client:
        logger.error("Cannot delete report: MongoDB connection failed.")
        return False

    try:
        # Validate ObjectId string
        try:
            object_id = ObjectId(report_id)
        except Exception:
            logger.error(f"Invalid report ID format for deletion: {report_id}")
            return False

        # Parameterize DB and Collection name
        sanitized_db_name = expected_brand_name.lower().replace(' ', '_')
        db = client[sanitized_db_name]
        collection_name = f"informes_{expected_brand_name.lower().replace(' ', '_')}"
        collection = db[collection_name]

        # Find the report first to check brand_name
        report_to_delete = collection.find_one({"_id": object_id}, {"brand_name": 1})

        if not report_to_delete:
            logger.warning(f"Report with ID {report_id} not found for deletion in DB '{sanitized_db_name}', collection '{collection_name}'.")
            return False

        # Verify brand ownership before deleting
        if report_to_delete.get("brand_name") != expected_brand_name:
            logger.warning(f"Deletion denied: Report {report_id} brand '{report_to_delete.get('brand_name')}' does not match expected brand '{expected_brand_name}'.")
            return False

        # Proceed with deletion
        delete_result = collection.delete_one({"_id": object_id})

        if delete_result.deleted_count == 1:
            logger.info(f"Successfully deleted report {report_id} for brand '{expected_brand_name}'.")
            return True
        else:
            # This case should ideally not be reached if find_one was successful,
            # but it's a safeguard.
            logger.warning(f"Report {report_id} found but not deleted for brand '{expected_brand_name}'. Delete count: {delete_result.deleted_count}")
            return False

    except Exception as e:
        logger.error(f"Error deleting report ID {report_id} for brand '{expected_brand_name}' from MongoDB: {e}", exc_info=True)
        return False
    finally:
        if client:
            client.close()
            logger.info("MongoDB connection closed after attempting report deletion.")

def update_job_status_mysql(
    job_id: str,
    status_code: str, # e.g., 'running', 'failed', 'completed'
    status_message: Optional[str] = None, # Optional detailed message or error
    user_id_for_log: Optional[int] = None
):
    """Updates the status and optional message of a job in the MySQL jobs table."""
    conn = None
    cursor = None
    logger = logging.getLogger(__name__) # Initialize logger
    log_adapter = logging.LoggerAdapter(logger, {'user_id': user_id_for_log or 'N/A'})
    

    # Ensure status_code isn't too long for its column (e.g., VARCHAR(50))
    status_code_db = status_code[:50] if status_code else 'unknown'
    status_message_db = status_message if status_message and status_message.strip() else None

    # Prepare message for DB (NULL if None or empty)
    message_db = status_message_db if status_message_db and status_message_db.strip() else None
    log_adapter.info(f"Job [{job_id}] Status: '{status_code_db}', Message: {message_db[:100] if message_db else ''}...")

    try:
        conn = get_db_connection()
        log_adapter.info(f"Job [{job_id}] DB connection successful.") # Changed from logger.info to log_adapter.info
        if not conn:
            log_adapter.error(f"Job [{job_id}] - Failed DB connection to update status='{status_code_db}'.")
            return False
        cursor = conn.cursor()
        log_adapter.info(f"Job [{job_id}] DB cursor created.")
        # Update both status and status_message columns
        sql = """
            UPDATE jobs
            SET
                status = %s,
                status_message = %s,
                updated_at = %s
            WHERE id = %s
        """
        values = (status_code_db, message_db, datetime.utcnow(), job_id)
        cursor.execute(sql, values)
        log_adapter.info(f"Job [{job_id}] SQL executed.")
        conn.commit()
        log_adapter.info(f"Job [{job_id}] status updated to '{status_code_db}' in DB.")
        if message_db: # Changed from 'message' to 'message_db'
             log_adapter.info(f"Job [{job_id}] Status: '{status_code_db}', Message: {message_db[:100]}...") # Changed from 'message' to 'message_db'
        return True
    except Error as e:
        log_adapter.error(f"Job [{job_id}] - Error updating job status='{status_code_db}' in DB: {e}", exc_info=True)
        return False
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
        return True

async def save_discovered_product_in_db(db: AsyncIOMotorDatabase, product: Dict[str, Any], brand_name: str, user_id: int) -> str:
    """
    Saves a discovered product's data to the 'reviews_products_gold' collection.
    Uses upsert to avoid creating duplicates based on the identifier and brand_name.
    """
    collection = db["Reviews"]["reviews_products_gold"]
    
    identifier = product.get("identifier")
    if not identifier:
        raise ValueError("Product data must contain an 'identifier' field.")

    product_data_to_save = product.copy()
    product_data_to_save.pop("_id", None)

    if 'final_price' in product_data_to_save and product_data_to_save['final_price'] is not None:
        product_data_to_save['final_price'] = str(product_data_to_save['final_price'])

    product_data_to_save['brand_name'] = brand_name
    product_data_to_save['user_id'] = user_id
    product_data_to_save['last_updated'] = datetime.now(timezone.utc)
    
    filter_query = {
        "identifier": identifier,
        "brand_name": brand_name
    }
    
    update_result = await collection.update_one(
        filter_query,
        {"$set": product_data_to_save},
        upsert=True
    )
    
    if update_result.upserted_id:
        return str(update_result.upserted_id)
    
    doc = await collection.find_one(filter_query, {"_id": 1})
    if doc:
        return str(doc["_id"])

    raise Exception("Could not save or find the product after upsert operation.")


async def fetch_discovered_products(db: AsyncIOMotorDatabase, brand_name: str) -> List[Dict]:
    """
    Fetches all saved/discovered products for a given brand from the 'reviews_products_gold' collection.
    """
    collection = db["Reviews"]["reviews_products_gold"]
    
    products_cursor = collection.find({"brand_name": brand_name})
    
    products = await products_cursor.to_list(length=None)
    
    # Convert ObjectId to string for JSON serialization
    for product in products:
        product["_id"] = str(product["_id"])
        
    return products


async def delete_discovered_product_from_db(db: AsyncIOMotorDatabase, identifier: str, brand_name: str) -> int:
    """Deletes a product from the discovered_products collection."""
    result = await db["Reviews.reviews_products_gold"].delete_one({"identifier": identifier, "brand_name": brand_name})
    return result.deleted_count

async def fetch_discovered_product_by_title(db: AsyncIOMotorDatabase, title: str, brand_name: str) -> Optional[Dict[str, Any]]:
    """Fetches a single discovered product by its title for a given brand."""
    try:
        product = await db["Reviews.reviews_products_gold"].find_one({"title": title, "brand_name": brand_name})
        if product:
            # Convert ObjectId to string to prevent serialization issues later
            product["_id"] = str(product["_id"])
        return product
    except Exception as e:
        logger.error(f"Error fetching discovered product by title '{title}' for brand '{brand_name}': {e}", exc_info=True)
        return None

async def fetch_discovered_product_by_identifier(db: AsyncIOMotorDatabase, identifier: str, brand_name: str) -> Optional[Dict[str, Any]]:
    """Fetches a single discovered product by its unique identifier for a specific brand."""
    collection = db["discovered_products"]
    product = await collection.find_one({"identifier": identifier, "brand_name": brand_name})
    if product and "_id" in product:
        product["_id"] = str(product["_id"])
    return product