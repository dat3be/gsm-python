from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # Import CORS middleware
import serial.tools.list_ports
import serial
import re
from pydantic import BaseModel

# Define the request model for GSM port
class GSMRequest(BaseModel):
    port: str

# Create the FastAPI app
app = FastAPI()

# Allow CORS for all domains (you can restrict it to specific domains as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all domains to make requests (replace '*' with specific domains if needed)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
def read_root():
    """
    Endpoint to check if the API is running.
    """
    return {"message": "GSM API is running!"}

@app.get("/ports")
def list_ports():
    """
    Endpoint to list all available COM ports (except COM1).
    """
    try:
        ports = serial.tools.list_ports.comports()
        port_list = [{"port": port.device, "description": port.description} for port in ports if port.device != "COM1"]
        return {"ports": port_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot list ports: {str(e)}")

@app.post("/get-info")
def get_gsm_info(request: GSMRequest):
    """
    Endpoint to fetch information from GSM Modem via COM port.
    """
    port = request.port  # Retrieve the port from the request body
    try:
        # Open the serial connection with the selected port
        ser = serial.Serial(port, baudrate=115200, timeout=5)

        # Verify connection using AT command
        ser.write(b'AT\r')
        response = ser.read(100).decode('utf-8', errors='ignore')
        if 'OK' not in response:
            ser.close()
            raise HTTPException(status_code=400, detail="Device not responding.")

        # Send USSD command (*101#)
        ser.write(b'ATD*101#;\r')  # Send USSD command
        ussd_response = ser.read(300).decode('utf-8', errors='ignore').strip()

        # Extract phone number and balance from the USSD response
        phone_number, balance = extract_phone_and_balance(ussd_response)

        ser.close()

        # Return the results
        return {
            "port": port,
            "phone_number": phone_number,
            "balance": balance,
            "raw_response": ussd_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot fetch information from port {port}: {str(e)}")

def extract_phone_and_balance(response: str):
    """
    Function to extract phone number and balance from the USSD response.
    """
    phone_number = re.search(r'\b\d{10,11}\b', response)  # Match phone number (10-11 digits)
    balance = re.search(r'TKC:?\s?([\w\d]+)', response)  # Match balance (TKC info)

    phone_number = phone_number.group(0) if phone_number else "Unknown"
    balance = balance.group(1) if balance else "Unknown"

    return phone_number, balance
