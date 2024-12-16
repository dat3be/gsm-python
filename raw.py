import tkinter as tk
from tkinter import ttk, messagebox
import serial.tools.list_ports
import threading
import re
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "GSM API is running!"}

class GSMManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Quét và Quản lý thiết bị GSM")
        self.root.geometry("900x500")

        # Status label
        self.status_label = tk.Label(self.root, text="", fg="blue")
        self.status_label.pack()

        # Cấu hình cột cho bảng Treeview
        self.columns = ("Check", "Cổng", "Mô tả", "Số điện thoại", "Số dư", "Nội dung")
        self.tree = ttk.Treeview(self.root, columns=self.columns, show="headings", height=15)

        self.tree.heading("Check", text="Check", command=lambda: self.sort_column("Check", False))
        self.tree.heading("Cổng", text="Cổng", command=lambda: self.sort_column("Cổng", False))
        self.tree.heading("Mô tả", text="Mô tả", command=lambda: self.sort_column("Mô tả", False))
        self.tree.heading("Số điện thoại", text="Số điện thoại", command=lambda: self.sort_column("Số điện thoại", False))
        self.tree.heading("Số dư", text="Số dư", command=lambda: self.sort_column("Số dư", False))
        self.tree.heading("Nội dung", text="Nội dung", command=lambda: self.sort_column("Nội dung", False))

        # Định nghĩa kích thước cột
        self.tree.column("Check", width=50, anchor="center")
        self.tree.column("Cổng", width=100, anchor="center")
        self.tree.column("Mô tả", width=200, anchor="center")
        self.tree.column("Số điện thoại", width=150, anchor="center")
        self.tree.column("Số dư", width=100, anchor="center")
        self.tree.column("Nội dung", width=250, anchor="center")
        self.tree.pack(fill="both", expand=True)

        # Bắt sự kiện click
        self.tree.bind("<Button-1>", self.on_checkbox_click)

        # Tạo các nút
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10)

        self.scan_button = ttk.Button(button_frame, text="Quét cổng", command=self.start_scan_ports)
        self.scan_button.pack(side="left", padx=5)

        self.select_all_button = ttk.Button(button_frame, text="Chọn tất cả", command=self.select_all)
        self.select_all_button.pack(side="left", padx=5)

        self.details_button = ttk.Button(button_frame, text="Xem thông tin", command=self.start_get_port_details)
        self.details_button.pack(side="left", padx=5)

        self.exit_button = ttk.Button(button_frame, text="Thoát", command=self.root.quit)
        self.exit_button.pack(side="left", padx=5)

    def set_status(self, text):
        """Set the status label text."""
        self.status_label.config(text=text)
        self.root.update_idletasks()

    def start_scan_ports(self):
        """Run the scan ports process in a separate thread."""
        threading.Thread(target=self.scan_ports).start()

    def scan_ports(self):
        """Scan and display available ports."""
        self.set_status("Processing...")
        ports = serial.tools.list_ports.comports()
        self.tree.delete(*self.tree.get_children())  # Clear the current list

        for port in ports:
            # Bỏ qua cổng COM1
            if port.device == "COM1":
                continue
            self.tree.insert(
                "",
                "end",
                values=("☐", port.device, port.description, "", "", "")
            )

        self.set_status("Done.")

    def on_checkbox_click(self, event):
        """Handle checkbox click."""
        region = self.tree.identify_region(event.x, event.y)
        if region == "heading":
            return

        row_id = self.tree.identify_row(event.y)
        if row_id:
            current_value = self.tree.set(row_id, "Check")
            new_value = "☑" if current_value == "☐" else "☐"
            self.tree.set(row_id, "Check", new_value)

    def select_all(self):
        """Select all rows in the treeview."""
        for item in self.tree.get_children():
            self.tree.set(item, "Check", "☑")

    def start_get_port_details(self):
        """Run the get port details process in a separate thread."""
        threading.Thread(target=self.get_port_details).start()

    def extract_phone_and_balance(self, response):
        """Extract phone number and balance from USSD response."""
        phone_number = re.search(r'\b\d{10,11}\b', response)  # Tìm số điện thoại (10-11 chữ số)
        balance = re.search(r'TKC:?\s?([\w\d]+)', response)  # Tìm thông tin TKC (số dư)

        phone_number = phone_number.group(0) if phone_number else "Không xác định"
        balance = balance.group(1) if balance else "Không xác định"

        return phone_number, balance

    def get_port_details(self):
        """Fetch details from the selected port."""
        selected_item = None
        for item in self.tree.get_children():
            if self.tree.set(item, "Check") == "☑":  # Check if the checkbox is selected
                selected_item = item
                break

        if not selected_item:
            messagebox.showwarning("Chưa chọn cổng", "Vui lòng chọn một cổng trước!")
            return

        selected_port = self.tree.item(selected_item, "values")[1]
        self.set_status("Processing...")

        try:
            ser = serial.Serial(selected_port, baudrate=115200, timeout=5)

            # Kiểm tra kết nối bằng lệnh AT
            ser.write(b'AT\r')
            response = ser.read(100).decode('utf-8', errors='ignore')
            if 'OK' not in response:
                messagebox.showerror("Không phản hồi", "Không nhận được phản hồi từ thiết bị GSM.")
                ser.close()
                self.set_status("Done.")
                return

            # Thực hiện lệnh USSD (*101#)
            ser.write(b'ATD*101#;\r')  # Gửi lệnh USSD
            ussd_response = ser.read(300).decode('utf-8', errors='ignore').strip()

            # Phân tích phản hồi USSD
            phone_number, balance = self.extract_phone_and_balance(ussd_response)
            self.tree.set(selected_item, "Nội dung", ussd_response)
            self.tree.set(selected_item, "Số điện thoại", phone_number)
            self.tree.set(selected_item, "Số dư", balance)

            ser.close()
            self.set_status("Done.")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lấy thông tin từ cổng {selected_port}.\n{str(e)}")
            self.set_status("Done.")

    def sort_column(self, col, reverse):
        """Sort the treeview column."""
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        data.sort(reverse=reverse)

        for index, (val, k) in enumerate(data):
            self.tree.move(k, "", index)

        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))


if __name__ == "__main__":
    root = tk.Tk()
    app = GSMManagerApp(root)
    root.mainloop()
