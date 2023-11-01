from flask import redirect, render_template, request, url_for, Response, send_file, session
from app import app, func, serial_usb
from functools import wraps
import jwt
from datetime import datetime, timedelta
from control_stm32 import control
from serial.serialutil import SerialException
from recognize_face import Name, probabilities


# region login required (not use)
def login_required(f):
    @wraps(f)
    def check(*args, **kwargs):
        if not session.get("id"):
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return check


# endregion


# region decorator for verifying the JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'token' in session:
            token = session['token']
        if not token:
            return redirect(url_for('login'))
        try:
            # decoding the payload to fetch the stored details
            data = jwt.decode(token, str(app.secret_key), algorithms="HS256")

            if not session.get('id'):
                func.create_token_on_db(data['id'], token, str(datetime.fromtimestamp(data['exp'])))

            session['id'] = data['id']

        except Exception as e:
            if str(e) == "Signature has expired":
                session.pop('id', None)
                session.pop('token', None)
                func.var.txt_error_login = "Signature has expired. Sign in to continue!"
                return redirect(url_for('login'))
            return {
                       "message": "Something went wrong",
                       "error": ' [500] ' + str(e)
                   }, 500
        return f(*args, **kwargs)

    return decorated


# endregion


# region check user is logged in and avoid user log in by other account
def check_user(f):
    @wraps(f)
    def check(*args, **kwargs):
        if 'id' in session:
            if func.check_admin(_userid=session['id']):
                return redirect(url_for('main_page'))
            else:
                return redirect(url_for('guest_page'))
        return f(*args, **kwargs)

    return check


# endregion


# region home page
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        return redirect(url_for('login'))
    return render_template('gui_homepage.html')


# endregion


# region login
@app.route('/v1/login', methods=['GET', 'POST'])
@check_user
def login():
    if request.method == 'POST':
        _userid = request.form['id']
        _password = request.form['pw']

        # validate the received values
        user_id = func.validate_user(_userid=_userid, _password=_password)

        # validate success
        if user_id:
            # create token
            token = jwt.encode({
                'id': user_id,
                'exp': datetime.utcnow() + timedelta(minutes=60)}, str(app.secret_key), "HS256")

            # save token in session
            session['token'] = token

            if func.check_admin(_userid=user_id):
                return redirect(url_for('main_page'))
            else:
                return redirect(url_for('guest_page'))

    # validate fail
    return render_template('gui_login.html', error=func.var.txt_error_login)


# endregion


# region logout
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    if 'id' in session and 'token' in session:
        session.pop('id', None)
        session.pop('token', None)
        if func.var.name_btn == 'DISCONNECT' and func.var.txt_info_main == 'Kết nối thành công':
            func.video.disconnect_cam()
            func.var.name_btn = 'CONNECT'
        func.var.txt_info_main = "Click CONNECT"
        func.var.txt_error_port = None
        serial_usb.close_port()
        return redirect(url_for('home'))


# endregion


# region sign up
@app.route('/v1/signup', methods=['GET', 'POST'])
def signup1():
    return render_template('gui_signup.html', error=None)


@app.route('/v1/signup-info', methods=['GET', 'POST'])
def signup2():
    if request.method == 'POST':
        _userid = request.form['id']
        _password = request.form['pw']
        _repassword = request.form['rpw']
        _email = request.form['email']
        _opt_level = request.form['opt_lv']

        if _opt_level == 'Admin':
            _opt_level = 'true'
        else:
            _opt_level = 'false'
        # validate the received values
        valid = func.validate_info_signup(_userid=_userid, _password=_password, _repassword=_repassword,
                                          _email=_email, _opt_level=_opt_level)
        if valid:
            return redirect(url_for('signup3'))
        else:
            return render_template('gui_signup.html', error=func.var.txt_error_signup)
    return render_template('gui_signup.html', error=None)


@app.route('/v1/signup-status=success', methods=['GET', 'POST'])
def signup3():
    if request.method == 'POST' and 'continue' in request.form:
        return redirect(url_for('login'))
    return render_template('end_signup.html')


# endregion


# region change and forget password
@app.route('/v1/change-password', methods=['GET', 'POST'])
@token_required
def change_pass():
    func.var.txt_error_newpw = None
    if request.method == 'POST':
        if 'back' in request.form:
            if func.check_admin(session['id']):
                return redirect(url_for('main_page'))
            else:
                return redirect(url_for('guest_page'))
        elif 'change' in request.form:
            _userid = session['id']
            _oldpw = request.form['opw']
            _newpw = request.form['npw']
            _renewpw = request.form['rnpw']

            # validate the received values
            valid = func.validate_change_password(_userid=_userid, _oldpassword=_oldpw, _newpassword=_newpw,
                                                  _renewpassword=_renewpw)
            if valid:
                if 'id' in session and 'token' in session:
                    session.pop('id', None)
                    session.pop('token', None)
                    if func.var.name_btn == 'DISCONNECT' and func.var.txt_info_main == 'Kết nối thành công':
                        func.video.disconnect_cam()
                        func.var.name_btn = 'CONNECT'
                    func.var.txt_info_main = 'Click CONNECT'
                    func.var.txt_error_port = None
                return redirect(url_for('endchange_pass'))
    return render_template('gui_changepw.html', error=func.var.txt_error_newpw)


@app.route('/v1/forget-password', methods=['GET', 'POST'])
def forget_pass():
    func.var.txt_error_newpw = None
    if request.method == 'POST':
        if 'back' in request.form:
            return redirect(url_for('login'))
        elif 'change' in request.form:
            _userid = request.form['id']
            _email = request.form['email']

            # validate the received values
            valid = func.validate_forget_password(_userid=_userid, _email=_email)
            if valid:
                return redirect(url_for('endforget_pass'))
    return render_template('gui_forgetpw.html', error=func.var.txt_error_newpw)


@app.route('/v1/forget-status=success', methods=['GET', 'POST'])
def endforget_pass():
    if request.method == 'POST':
        if 'continue' in request.form:
            return redirect(url_for('login'))
        else:
            return redirect(url_for('forget_pass'))
    return render_template('end_forgetpw.html')


@app.route('/v1/change-status=success', methods=['GET', 'POST'])
def endchange_pass():
    if request.method == 'POST':
        if 'continue' in request.form:
            return redirect(url_for('login'))
        else:
            return redirect(url_for('change_pass'))
    return render_template('end_changepw.html')


# endregion


# region guest page
@app.route('/v1/guest-page')
@token_required
def guest_page():
    return render_template('gui_guest.html', nameid=session['id'])


# endregion


# region main page
@app.route('/v1/main-page', methods=['GET', 'POST'])
@token_required
def main_page():
    return render_template('gui_main.html', info=func.var.txt_info_main, namebtn=func.var.name_btn,
                           nameid=session['id'], errorport=func.var.txt_error_port, nguoinhandien=func.var.name_predict,
                           khanangnhandien=func.var.prob_predict)


# endregion


# region event connect button
@app.route('/v1/connection', methods=['GET', 'POST'])
@token_required
def cnt_camera():
    if request.method == 'POST':
        if func.var.name_btn == 'CONNECT' and ('cnt1' or 'cnt2' in request.form):
            func.video.connect_cam()
            if func.video.vid.isOpened:
                func.var.name_btn = 'DISCONNECT'
                func.var.txt_info_main = 'Kết nối thành công'
            else:
                func.var.name_btn = 'CONNECT'
                func.var.txt_info_main = 'Something is wrong'
        elif func.var.name_btn == 'DISCONNECT' and ('cnt1' or 'cnt2' in request.form):
            func.video.disconnect_cam()
            func.var.name_btn = 'CONNECT'
            func.var.txt_info_main = 'Ngắt kết nối thành công'
        else:
            pass
    return redirect(url_for('main_page'))


@app.route('/v1/openport', methods=['GET', 'POST'])
@token_required
def openport():
    if request.method == 'POST':
        try:
            serial_usb.open_port()
            if serial_usb.usb.isOpen():
                control.control_thread.start()
                func.var.txt_error_port = 'Thành công'
        except SerialException:
            func.var.txt_error_port = 'Kiểm tra lại dây dẫn hoặc đã mở port!'
    return redirect(url_for('main_page'))


@app.route('/v1/refresh', methods=['GET', 'POST'])
@token_required
def refresh():
    if request.method == "POST":
        func.var.name_predict = Name.final_name[0]
        func.var.prob_predict = probabilities.result
        return redirect(url_for('main_page'))
# endregion


# region show video on home page
@app.route('/v1/video_feed')
@token_required
def video_feed():
    if func.var.name_btn == 'DISCONNECT' and func.var.txt_info_main == 'Kết nối thành công':
        return Response(func.video.gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return send_file('static/styles/cap3.jpg', mimetype='image/gif')

# endregion


if __name__ == '__main__':
    app.run()
