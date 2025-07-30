from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import secrets
import string
import math
import datetime
import threading # 여러 요청을 안전하게 처리하기 위해 추가

app = Flask(__name__)
# 세션 관리를 위한 시크릿 키 (보안상 필수)
app.secret_key = os.urandom(24)

# ADMIN_KEY 환경 변수 (허깅페이스 시크릿에서 설정)
ADMIN_PASSWORD = os.environ.get("ADMIN_KEY")

# --- 데이터베이스 대신 사용할 메모리 내 저장소 ---
# 생성된 암호를 저장할 리스트
passwords_store = []
# 여러 사용자가 동시에 암호를 생성할 때 충돌을 방지하기 위한 잠금 장치
lock = threading.Lock()
# ---------------------------------------------

def generate_password(length=24):
    """안전한 랜덤 암호를 생성합니다."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    return password

@app.route('/')
def index():
    """메인 페이지를 렌더링합니다."""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def create_and_show_password():
    """암호를 생성하고 메모리에 저장한 뒤, 사용자에게 보여줍니다."""
    new_password = generate_password()
    
    # lock을 사용하여 안전하게 리스트에 데이터를 추가합니다.
    with lock:
        new_id = len(passwords_store) + 1
        created_at_utc = datetime.datetime.now(datetime.timezone.utc)
        
        passwords_store.append({
            "id": new_id,
            "password": new_password,
            "created_at": created_at_utc
        })
        count = len(passwords_store)

    # 생성된 암호와 순번을 index.html에 전달
    return render_template('index.html', generated_password=new_password, password_count=count)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """관리자 로그인 페이지 처리."""
    if request.method == 'POST':
        password = request.form['password']
        if ADMIN_PASSWORD and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash('비밀번호가 틀렸습니다.', 'error')
            if not ADMIN_PASSWORD:
                flash('ADMIN_KEY 시크릿이 설정되지 않았습니다!', 'error')
    return render_template('login.html')

@app.route('/admin')
def admin():
    """관리자 대시보드. 로그인 상태가 아니면 로그인 페이지로 리디렉션합니다."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # 페이지네이션 파라미터 가져오기
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    
    # 페이지 크기 최대 200으로 제한
    if page_size > 200:
        page_size = 200
        
    with lock:
        # 최신순으로 보여주기 위해 리스트를 복사하고 뒤집습니다.
        sorted_passwords = list(reversed(passwords_store))
        
        total_items = len(sorted_passwords)
        total_pages = math.ceil(total_items / page_size)

        # 현재 페이지에 해당하는 데이터만 잘라냅니다.
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_passwords = sorted_passwords[start_index:end_index]

    return render_template(
        'admin.html',
        passwords=paginated_passwords,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        total_items=total_items
    )

@app.route('/logout')
def logout():
    """관리자 로그아웃."""
    session.pop('logged_in', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Hugging Face Spaces는 기본적으로 7860 포트를 사용합니다.
    app.run(host="0.0.0.0", port=7860)