import os
from urllib.parse import urlparse
import mysql.connector
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import traceback
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URL from Render's environment variable
DB_URL = os.getenv("DATABASE_URL", "mysql://root:IjZkUIijlMWQqcGxxFSPABRvksXEvSHl@trolley.proxy.rlwy.net:28128/railway")
db_url = urlparse(DB_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific frontend URL if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    try:
        if not DB_URL:
            raise Exception("DATABASE_URL environment variable is missing!")

        url = urlparse(DB_URL)
        connection = mysql.connector.connect(
            host=url.hostname,
            user=url.username,
            password=url.password,
            database=url.path[1:],  # Remove leading "/"
            port=url.port
        )
        return connection
    except mysql.connector.Error as err:
        logger.error(f"Database Connection Error: {err}")
        return None

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

        cursor.execute("SELECT location FROM usersrecord WHERE mobile_number = %s", (sender_number,))
        result = cursor.fetchone()

        if result is None:
            raise HTTPException(status_code=400, detail="Sender number not found in database")

        location = result[0]

        cursor.execute("SELECT mobile_number FROM usersrecord WHERE location = %s AND mobile_number != %s", (location, sender_number))
        recipients = cursor.fetchall()

        recipient_numbers = [row[0] for row in recipients]

        cursor.close()
        db.close()

        return {"message": "SMS processed successfully", "recipients": recipient_numbers}

    except mysql.connector.Error as err:
        logger.error(f"Database error: {err}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Database error occurred")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)  # Change port if needed
