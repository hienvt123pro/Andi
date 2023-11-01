import time
from recognize_face import Name, NumberOfPeople
from control_stm32 import stx, etx, sync, cmd_open_door, cmd_close_door, cmd_on_led, cmd_off_led, cmdResponse
import threading
from app import serial_usb, func
import collections

OPEN_DOOR = bytes(stx + cmd_open_door + sync + etx)
CLOSE_DOOR = bytes(stx + cmd_close_door + sync + etx)
ON_LED = bytes(stx + cmd_on_led + sync + etx)
OFF_LED = bytes(stx + cmd_off_led + sync + etx)


def control_handler():
    while True:
        if serial_usb.usb.isOpen() and func.var.name_btn == 'DISCONNECT':
            # event read port handler
            if serial_usb.usb.inWaiting():
                res = serial_usb.usb.readline(7)
                if res[1:5] == b'OLED' or res[1:5] == b'CLED':
                    cmdResponse.led_cmd = res[1:5]
                    print("led: {}".format(cmdResponse.led_cmd))
                elif res[1:5] == b'OPEN' or res[1:5] == b'CLOS':
                    cmdResponse.motor_cmd = res[1:5]
                    print("motor: {}".format(cmdResponse.motor_cmd))

            # if 0 person
            if NumberOfPeople.get_num == 0:
                if cmdResponse.led_cmd != b'CLED':
                    serial_usb.usb.write(OFF_LED)
                time.sleep(6)
                if NumberOfPeople.get_num == 0:
                    if cmdResponse.motor_cmd != b'CLOS':
                        serial_usb.usb.write(CLOSE_DOOR)

            # if 1 person
            elif NumberOfPeople.get_num == 1:
                if Name.final_name[0] == 'unknown':
                    if cmdResponse.led_cmd != b'OLED':
                        serial_usb.usb.write(ON_LED)
                    time.sleep(3)
                    if Name.final_name[0] == 'unknown' and NumberOfPeople.get_num != 0:
                        if cmdResponse.motor_cmd != b'CLOS':
                            serial_usb.usb.write(CLOSE_DOOR)
                elif Name.final_name[0] != 'unknown' and Name.final_name[0] != 0:
                    if cmdResponse.led_cmd != b'CLED':
                        serial_usb.usb.write(OFF_LED)
                    time.sleep(3)
                    if Name.final_name[0] != 'unknown' and Name.final_name[0] != 0 and NumberOfPeople.get_num != 0:
                        if cmdResponse.motor_cmd != b'OPEN':
                            serial_usb.usb.write(OPEN_DOOR)

            # if > 1 person
            elif 1 < NumberOfPeople.get_num < 21:
                opening = False
                for i in range(0, NumberOfPeople.get_num):
                    if Name.final_name[i] != 'unknown':
                        time.sleep(3)
                        if Name.final_name[i] != 'unknown':
                            if cmdResponse.motor_cmd != b'OPEN':
                                serial_usb.usb.write(OPEN_DOOR)
                                opening = True
                            break

                # all unknown
                if not opening:
                    count = collections.Counter(Name.final_name)
                    if count.most_common()[1][1] == NumberOfPeople.get_num:
                        if cmdResponse.motor_cmd != b'CLOS':
                            serial_usb.usb.write(CLOSE_DOOR)


control_thread = threading.Thread(target=control_handler)
