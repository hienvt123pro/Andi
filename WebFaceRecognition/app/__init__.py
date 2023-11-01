from flask import Flask
from flask_cors import CORS
from flask_mail import Mail
import csv
import serial

secretkey = open("env.csv", "r")
read_secretkey = csv.reader(secretkey)
data = next(read_secretkey)
secretkey.close()

app = Flask(__name__)
app.secret_key = data
CORS(app)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'hien.nguyenminh.sistrain@gmail.com'
app.config['MAIL_PASSWORD'] = 'uffcoaqaivcpfcof'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)


class SerialUSB:
    def __init__(self):
        self.usb = serial.Serial('COM3', baudrate=115200, timeout=5)

    def __del__(self):
        self.usb.close()

    def open_port(self):
        self.usb.open()
        self.usb.flushOutput()
        self.usb.flushInput()

    def close_port(self):
        self.usb.close()


serial_usb = SerialUSB()
