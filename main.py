from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import serial.tools.list_ports
import serial
import re
from pydantic import BaseModel

# Định nghĩa model dữ liệu cho body request
class GSMRequest(BaseModel):
    port: str

# Tạo ứng dụng FastAPI
app = FastAPI()

@app.get("/")
def read_root():
    """
    Endpoint để kiểm tra API.
    """
    return {"message": "GSM API is running!"}


@app.get("/ports")
def list_ports():
    """
    Endpoint để liệt kê tất cả các cổng COM (trừ COM1).
    """
    try:
        ports = serial.tools.list_ports.comports()
        port_list = [{"port": port.device, "description": port.description} for port in ports if port.device != "COM1"]
        return {"ports": port_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể liệt kê cổng: {str(e)}")



@app.post("/get-info")
def get_gsm_info(request: GSMRequest):
    """
    Endpoint để lấy thông tin từ GSM Modem qua cổng COM.
    """
    port = request.port  # Truy xuất cổng từ body
    try:
        # Mở kết nối serial với cổng được chọn
        ser = serial.Serial(port, baudrate=115200, timeout=5)

        # Kiểm tra kết nối bằng lệnh AT
        ser.write(b'AT\r')
        response = ser.read(100).decode('utf-8', errors='ignore')
        if 'OK' not in response:
            ser.close()
            raise HTTPException(status_code=400, detail="Thiết bị không phản hồi.")

        # Thực hiện lệnh USSD (*101#)
        ser.write(b'ATD*101#;\r')  # Gửi lệnh USSD
        ussd_response = ser.read(300).decode('utf-8', errors='ignore').strip()

        # Phân tích phản hồi USSD
        phone_number, balance = extract_phone_and_balance(ussd_response)

        ser.close()

        # Trả về kết quả
        return {
            "port": port,
            "phone_number": phone_number,
            "balance": balance,
            "raw_response": ussd_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể lấy thông tin từ cổng {port}: {str(e)}")
    """
    Endpoint để lấy thông tin từ GSM Modem qua cổng COM.
    """
    try:
        # Mở kết nối serial với cổng được chọn
        ser = serial.Serial(port, baudrate=115200, timeout=5)

        # Kiểm tra kết nối bằng lệnh AT
        ser.write(b'AT\r')
        response = ser.read(100).decode('utf-8', errors='ignore')
        if 'OK' not in response:
            ser.close()
            raise HTTPException(status_code=400, detail="Thiết bị không phản hồi.")

        # Thực hiện lệnh USSD (*101#)
        ser.write(b'ATD*101#;\r')  # Gửi lệnh USSD
        ussd_response = ser.read(300).decode('utf-8', errors='ignore').strip()

        # Phân tích phản hồi USSD
        phone_number, balance = extract_phone_and_balance(ussd_response)

        ser.close()

        # Trả về kết quả
        return {
            "port": port,
            "phone_number": phone_number,
            "balance": balance,
            "raw_response": ussd_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể lấy thông tin từ cổng {port}: {str(e)}")


def extract_phone_and_balance(response: str):
    """
    Hàm bóc tách số điện thoại và số dư từ phản hồi USSD.
    """
    phone_number = re.search(r'\b\d{10,11}\b', response)  # Tìm số điện thoại (10-11 chữ số)
    balance = re.search(r'TKC:?\s?([\w\d]+)', response)  # Tìm thông tin TKC (số dư)

    phone_number = phone_number.group(0) if phone_number else "Không xác định"
    balance = balance.group(1) if balance else "Không xác định"

    return phone_number, balance
