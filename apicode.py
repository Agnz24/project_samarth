from fastapi import FastAPI, HTTPException
import mysql.connector
from pydantic import BaseModel
import traceback

app = FastAPI()

# Function to connect to MySQL database
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="kello2@M",  # Replace with your MySQL root password
        database="messaging_db"
    )

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
        cursor = db.cursor()

        # Debugging: Print received sender_number
        print(f"Received sender_number: {sender_number}")

        # Check if the sender's mobile number exists in the database
        cursor.execute("SELECT location FROM users WHERE mobile_number = %s", (sender_number,))
        result = cursor.fetchone()

        if result is None:
            raise HTTPException(status_code=400, detail="Sender number not found in database")

        location = result[0]
        print(f"User found in location: {location}")

        # Fetch all other mobile numbers in the same location
        cursor.execute("SELECT mobile_number FROM users WHERE location = %s AND mobile_number != %s", (location, sender_number))
        recipients = cursor.fetchall()

        if not recipients:
            raise HTTPException(status_code=400, detail="No other users found in this location")

        recipient_numbers = [row[0] for row in recipients]
        print(f"Message will be sent to: {recipient_numbers}")

        # Close database connection
        cursor.close()
        db.close()

        return {"message": "SMS processed successfully", "recipients": recipient_numbers}

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Database connection failed")
