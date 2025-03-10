from fastapi import FastAPI, HTTPException
import mysql.connector
from mysql.connector import Error
from pydantic import BaseModel
import os
import traceback
import logging
from urllib.parse import urlparse

app = FastAPI()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URL from Railway environment variables
DB_URL = os.getenv("DATABASE_URL")  # Railway provides this automatically

def get_db_connection():
    try:
        if not DB_URL:
            raise Exception("DATABASE_URL environment variable is missing!")

        # Parse the DATABASE_URL format from Railway
        url = urlparse(DB_URL)
        connection = mysql.connector.connect(
            host=url.hostname,
            user=url.username,
            password=url.password,
            database=url.path[1:],  # Remove leading "/"
            port=url.port
        )
        return connection
    except Error as err:
        logger.error(f"Database Connection Error: {err}")
        return None

# Pydantic model for request body
class SMSRequest(BaseModel):
    sender_number: str
    message: str

@app.post("/process_sms/")
def process_sms(request: SMSRequest):
    sender_number = request.sender_number
    message = request.message

    try:
        db = get_db_connection()
        if db is None:
            raise HTTPException(status_code=500, detail="Database connection failed")

        cursor = db.cursor()

        logger.info(f"Received sender_number: {sender_number}")

        # Check if the sender's mobile number exists in the database
        cursor.execute("SELECT location FROM users WHERE mobile_number = %s", (sender_number,))
        result = cursor.fetchone()

        if result is None:
            raise HTTPException(status_code=400, detail="Sender number not found in database")

        location = result[0]
        logger.info(f"User found in location: {location}")

        # Fetch all other mobile numbers in the same location
        cursor.execute("SELECT mobile_number FROM users WHERE location = %s AND mobile_number != %s", (location, sender_number))
        recipients = cursor.fetchall()

        if not recipients:
            raise HTTPException(status_code=400, detail="No other users found in this location")

        recipient_numbers = [row[0] for row in recipients]
        logger.info(f"Message will be sent to: {recipient_numbers}")

        # Close database connection
        cursor.close()
        db.close()

        return {"message": "SMS processed successfully", "recipients": recipient_numbers}

    except mysql.connector.Error as err:
        logger.error(f"Database error: {err}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Database error occurred")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
