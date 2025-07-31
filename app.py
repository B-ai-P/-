from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import secrets
import string
import math
import datetime
import threading
# 시간대 변환을 위해 zoneinfo를 import합니다. (Python 3.9+ 기본 내장)
from zoneinfo import ZoneInfo

app = Flask(__name__)
# 세션 관리를 위한 시크릿 키 (보안상 필수)
app.secret_key = os.urandom(24)

# ADMIN_KEY 환경 변수 (허깅페이스 시크릿에서 설정)
ADMIN_PASSWORD = os.environ.get("ADMIN_KEY")

# --- 데이터베이스 대신 사용할 메모리 내 저장소 ---
passwords_store = []
# 여러 사용자가 동시에 암호를 생성할 때 충돌을 방지하기 위한 잠금 장치
lock = threading.Lock()
# ---------------------------------------------

# 한국 시간대(KST)를 정의합니다.
KST = ZoneInfo("Asia/Seoul")

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
    
    with lock:
        new_id = len(passwords_store) + 1
        # 시간대 정보가 포함된 UTC 시간으로 저장합니다.
        created_at_utc = datetime.datetime.now(datetime.timezone.utc)
        
        passwords_store.append({
            "id": new_id,
            "password": new_password,
            "created_at": created_at_utc
        })
        count = len(passwords_store)

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
    """관리자 대시보드. 검색 및 시간대 변환 기능 포함."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # 페이지네이션 및 검색 파라미터 가져오기
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    search_by = request.args.get('search_by', '')
    query = request.args.get('q', '').strip()

    if page_size > 200:
        page_size = 200
        
    with lock:
        # 검색어에 따라 데이터 필터링
        filtered_passwords = []
        if query and search_by:
            for item in passwords_store:
                if search_by == 'id':
                    if str(item['id']) == query:
                        filtered_passwords.append(item)
                elif search_by == 'password':
                    if query.lower() in item['password'].lower():
                        filtered_passwords.append(item)
                elif search_by == 'created_at':
                    # UTC 시간을 KST로 변환 후 문자열로 만듦
                    created_kst_str = item['created_at'].astimezone(KST).strftime('%Y-%m-%d %H:%M:%S')
                    # 검색어가 생성일시 문자열에 포함되는지 확인
                    if query in created_kst_str:
                        filtered_passwords.append(item)
        else:
            # 검색어가 없으면 전체 목록을 사용
            filtered_passwords = list(passwords_store)

        # 최신순으로 보여주기 위해 리스트를 복사하고 뒤집습니다.
        sorted_passwords = list(reversed(filtered_passwords))
        
        total_items = len(sorted_passwords)
        total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_passwords = sorted_passwords[start_index:end_index]

        # 표시용 데이터 가공: UTC 시간을 KST로 변환
        display_passwords = []
        for item in paginated_passwords:
            new_item = item.copy()
            # UTC 시간을 KST로 변환하여 'created_at_kst' 키에 저장
            new_item['created_at_kst'] = item['created_at'].astimezone(KST)
            display_passwords.append(new_item)

    return render_template(
        'admin.html',
        passwords=display_passwords, # KST 시간이 포함된 데이터 전달
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        total_items=total_items,
        # 검색 유지를 위해 파라미터 전달
        search_by=search_by,
        q=query
    )

@app.route('/logout')
def logout():
    """관리자 로그아웃."""
    session.pop('logged_in', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Hugging Face Spaces는 기본적으로 7860 포트를 사용합니다.
    app.run(host="0.0.0.0", port=7860)
