import cv2
import psycopg2
import psycopg2.extras
from werkzeug.security import check_password_hash, generate_password_hash
from flask_mail import Message
from app import mail
import random
from recognize_face import facerecognize

# region DB-info
DB_HOST = "localhost"
DB_NAME = "login_data"
DB_USER = "postgres"
DB_PASS = "hienvt123"


# endregion


class MyOpenCV:
    def __init__(self):
        self.vid = None

    def __del__(self):
        if self.vid.isOpened():
            self.vid.release()
            cv2.destroyAllWindows()

    def connect_cam(self):
        self.vid = cv2.VideoCapture(0)

    def disconnect_cam(self):
        if self.vid.isOpened():
            self.vid.release()
            cv2.destroyAllWindows()

    def gen_frames(self):
        while True:
            if self.vid.isOpened():
                success, frame = self.vid.read()  # read the camera frame
                if not success:
                    break
                else:
                    frame = facerecognize.run_model(frame)
                    ret, buffer = cv2.imencode('.jpg', frame)
                    frame = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


class VariableHtml:
    def __init__(self):
        self.name_btn = 'CONNECT'
        self.txt_error_login = None
        self.txt_info_main = 'Click CONNECT'
        self.txt_error_signup = None
        self.admin = None
        self.txt_error_newpw = None
        self.txt_error_port = None
        self.name_predict = None
        self.prob_predict = None


# region var
var = VariableHtml()
video = MyOpenCV()
# endregion


def validate_user(_userid, _password):
    cnt = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)  # line connect 1
    if _userid and _password:
        # check user exists
        cursor = cnt.cursor(cursor_factory=psycopg2.extras.DictCursor)
        sql = "select * from public.validate_login where id=%s"
        sql_where = (_userid,)
        cursor.execute(sql, sql_where)
        row_value = cursor.fetchone()
        if row_value:
            userid = row_value[0]
            password = row_value[1]
            if check_password_hash(password, _password):
                cursor.close()
                cnt.close()
                var.txt_error_login = None
                return userid
            else:
                var.txt_error_login = '403: Incorrect password. Please try again!'
        else:
            var.txt_error_login = '401: Invalid CMND or CCCD. Try again!'
    else:
        var.txt_error_login = '401: Missing ID or Password. Try again!'
    return None


def check_admin(_userid):
    cnt = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = cnt.cursor(cursor_factory=psycopg2.extras.DictCursor)
    sql = "select * from public.validate_login where id=%s"
    sql_where = (_userid,)
    cursor.execute(sql, sql_where)
    row_value = cursor.fetchone()
    if row_value:
        return row_value[3]
    cursor.close()
    cnt.close()
    return None


def create_token_on_db(_userid, _token, _exp):
    cnt = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    cursor = cnt.cursor(cursor_factory=psycopg2.extras.DictCursor)
    sql = "UPDATE public.validate_login SET token=%s, expire_time=%s where id=%s"
    sql_where = (_token, _exp, _userid)
    cursor.execute(sql, sql_where)
    cnt.commit()
    cursor.close()
    cnt.close()


def validate_info_signup(_userid, _password, _repassword, _email, _opt_level):
    cnt = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)  # line connect 2
    if _userid and _password and _repassword and _email:
        if len(list(_userid)) == 12 and ('@gmail.com' in _email):
            if _password == _repassword:
                cursor = cnt.cursor(cursor_factory=psycopg2.extras.DictCursor)
                try:
                    sql = "INSERT INTO public.validate_login (id, pw, email, admin) VALUES (%s, %s, %s, %s)"
                    sql_where = (_userid, generate_password_hash(_password), _email, _opt_level)
                    cursor.execute(sql, sql_where)
                    cnt.commit()
                    cursor.close()
                    cnt.close()
                    return 'success'
                except cnt.IntegrityError:
                    var.txt_error_signup = "202: Your ID already exists. Please log in!"
                    return None
            else:
                var.txt_error_signup = '401: Incorrect re-type password. Try again!'
        else:
            var.txt_error_signup = '401: Invalid id or email. Try again!'
    else:
        var.txt_error_signup = '401: Missing some information. Try again!'
    return None


def validate_change_password(_userid, _oldpassword, _newpassword, _renewpassword):
    cnt = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    if _userid and _oldpassword and _newpassword and _renewpassword:
        cursor = cnt.cursor(cursor_factory=psycopg2.extras.DictCursor)
        sql = "select * from public.validate_login where id=%s"
        sql_where = (_userid,)
        cursor.execute(sql, sql_where)
        row_value = cursor.fetchone()
        if row_value:
            userid = row_value[0]
            password = row_value[1]
            if check_password_hash(password, _oldpassword):
                if _newpassword == _oldpassword:
                    var.txt_error_newpw = 'Duplicate old and new password!'
                    return None

                if _newpassword == _renewpassword:
                    sql = "UPDATE public.validate_login SET pw=%s where id=%s"
                    sql_where = (generate_password_hash(_newpassword), userid)
                    cursor.execute(sql, sql_where)
                    cnt.commit()
                    cursor.close()
                    cnt.close()
                    var.txt_error_newpw = None
                    return 'success'
                else:
                    var.txt_error_newpw = 'Incorrect re-type password. Try again!'
            else:
                var.txt_error_newpw = 'Incorrect old password. Try again!'
        else:
            var.txt_error_newpw = 'Error ID. Please sign in again!'
    else:
        var.txt_error_newpw = 'Missing some information. Try again!'
    return None


def validate_forget_password(_userid, _email):
    cnt = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
    if _userid and _email:
        cursor = cnt.cursor(cursor_factory=psycopg2.extras.DictCursor)
        sql = "select * from public.validate_login where id=%s"
        sql_where = (_userid,)
        cursor.execute(sql, sql_where)
        row_value = cursor.fetchone()
        if row_value:
            email = row_value[2]
            userid = row_value[0]
            if row_value:
                if email == _email:
                    a = random.randint(199111, 999456)
                    new_pass = generate_password_hash(str(a))
                    sql = "UPDATE public.validate_login SET pw=%s where id=%s"
                    sql_where = (new_pass, userid)
                    cursor.execute(sql, sql_where)
                    cnt.commit()
                    cursor.close()
                    cnt.close()
                    msg = Message('RESET MẬT KHẨU', sender='noreply@gmail.com', recipients=[email])
                    msg.body = "Chúng tôi đã hỗ trợ bạn reset mật khẩu. Đây là mật khẩu mới của bạn: " + str(
                        a) + '\n' + 'Trân trọng.'
                    mail.send(msg)
                    return 'success'
                else:
                    var.txt_error_newpw = '403: Incorrect email. Try again!'
        else:
            var.txt_error_newpw = '401: Invalid ID. Try again!'
    else:
        var.txt_error_newpw = '401: Missing some information!'
    return None
