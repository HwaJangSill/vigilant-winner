from flask import *
import os
import datetime
import sqlite3
import json
from random import choice
from string import ascii_letters, digits

# 임시 비밀번호 생성 함수 => (영어 대문자 + 소문자 + 숫자 중 무작위 20자리)
def temp_pw_generator():
    temp_pw = ""
    for i in range(20):
        temp_pw += choice(ascii_letters + digits)
    return temp_pw


# sql 키워드와 매칭되는 쿼리를 입력값으로 받는 함수
# 입력 받은 쿼리를 바탕으로 데이터베이스에 연결하여 실행을 담당
# 반환되는 자료형은 리스트
def exeQuery(**querys):
    selectValue = [] # 반환되는 값을 담는 리스트
    conn = sqlite3.connect('test.db')
    conn.row_factory = sqlite3.Row # 실행 결과를 딕셔너리 형태로 받기
    conn.execute("PRAGMA foreign_keys = ON;") # 외래 키 사용을 위해 명시적으로 지정
    Cursor = conn.cursor()
    for keyWord, query in querys.items():
        if keyWord == 'SELECT': # SELECT 키워드를 사용하는 경우에만 결과값을 저장하여 반환
            Cursor.execute(query)
            for row in Cursor.fetchall():
                selectValue.append(dict(row))
        Cursor.execute(query)
    conn.commit()
    conn.close()
    
    return selectValue

app = Flask(__name__)
app.debug = True


# 유저 테이블 생성 쿼리
createUserTable =  """
    CREATE TABLE IF NOT EXISTS TestUser (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track VARCHAR(32) NOT NULL,
    plan VARCHAR(10) NOT NULL,
    name VARCHAR(50) NOT NULL,
    affiliation VARCHAR(50) DEFAULT "-",
    email VARCHAR(255) UNIQUE NOT NULL,
    login_id VARCHAR(20) UNIQUE NOT NULL,
    login_pw VARCHAR(255) NOT NULL,
    file_name VARCHAR(50) DEFAULT NULL,
    date DATETIME NOT NULL
    );
"""

# 체크리스트 테이블 생성 쿼리
createCheckList = """
    CREATE TABLE IF NOT EXISTS CheckList (
    post_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    text VARCHAR(300) NOT NULL,
    date DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES TestUser(id) ON DELETE CASCADE
    );
"""

# 게시글 테이블 생성 쿼리
createBoard = """
    CREATE TABLE IF NOT EXISTS board (
    post_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    user_name VARCHAR(50) NOT NULL,
    plan VARCHAR(10) NOT NULL,
    title VARCHAR(300) NOT NULL,
    text VARCHAR(65535) NOT NULL,
    secret VARCHAR(20) DEFAULT NULL,
    file_name VARCHAR(100) DEFAULT NULL,
    date DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES TestUser(id) ON DELETE CASCADE
    );
"""

# 댓글 테이블 생성 쿼리
createComment = """
    CREATE TABLE IF NOT EXISTS comment (
    comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    user_id INTEGER UNIQUE NOT NULL,
    user_name VARCHAR(50) NOT NULL,
    plan VARCHAR(10) NOT NULL,
    text VARCHAR(500) NOT NULL,
    date DATETIME NOT NULL,
    FOREIGN KEY (post_id) REFERENCES board(post_id) ON DELETE CASCADE
    );
"""

#관리자 계정 생성
insertAdmin = f"""
    INSERT INTO TestUser (
    track,
    plan,
    name,
    affiliation,
    email,
    login_id,
    login_pw,
    date
    ) VALUES (
    '-',
    '-',
    '관리자',
    '-',
    'admin@manager.net',
    'admin',
    'admin',
    '{datetime.datetime.now().replace(microsecond=0)}');
"""

# 쿼리 실행
exeQuery(CREATE=createUserTable)
exeQuery(CREATE=createCheckList)
exeQuery(CREATE=createBoard)
exeQuery(CREATE=createComment)
# exeQuery(INSERT=insertAdmin)


##### 어플리케이션 로직 #####

# 메인 페이지 접근 처리
@app.route('/')
def index():
    cookie = request.cookies.get('user_id')
    if cookie:
        # 유저 데이터 가져오기
        selectUserInfo = f"SELECT * FROM TestUser WHERE id={cookie};"
        userData = exeQuery(SELECT=selectUserInfo)[0]
        print(userData)
        track = userData['track']
        name = userData['name']

        # 체크리스트 데이터 가져오기
        selectList = f"SELECT post_id, text FROM CheckList WHERE user_id={cookie};"
        checkLists = exeQuery(SELECT=selectList)
        print(checkLists)

        return render_template('index.html', loginState=True ,track=track, name=name, checkLists=checkLists)
    else:
        return render_template('index.html')



# 존재하지 않는 경로에 접근했을 때 404 에러 메시지 출력하기
@app.route('/<path:subpath>', methods=['GET'])
def pathRouting(subpath):
    if subpath not in ['login', 'join', 'checkList', 'exit']:
        notFound = """
        <h1>404 Not Found</h1>
        <h3>/{{ path }}에 대한 페이지를 찾을 수 없습니다.</h3>
        <a href="/">메인 페이지로 이동하기</a>
        """
        return render_template_string(notFound, path=subpath)



# 로그인 요청 처리
@app.route('/login/', methods=['GET', 'POST'])
def login():
    # 해당 경로에 POST 방식으로 요청을 보냈을 때 클라이언트에서 보낸 데이터를 
    # 기반으로 데이터베이스에 질의하여 일치하는 유저가 있는 경우 로그인 승인.
    if request.method == 'POST':
        loginData = request.form.to_dict() # 클라이언트에서 전송한 데이터를 딕셔너리 형태로 가져오기

        if loginData['type'] == 'find_id': # 아이디 찾기
            # 데이터베이스에 질의를 위한 SELECT문
            selectQuery = f"""
                SELECT * FROM TestUser WHERE 
                email='{loginData['email']}' 
                AND login_pw='{loginData['pw']}';
            """
            print(selectQuery)
            row = exeQuery(SELECT=selectQuery) # 유저 데이터
            print(row)
            if row == [] : # SELECT 구문 실행 이후 아무런 값도 받지 못한 경우
                message = """
                    <script>
                        alert('일치하는 데이터가 없습니다. 입력 값을 다시 한 번 확인해 주세요');
                        location.href='/login/';
                    </script>
                """
                return render_template_string(message)

            else: # 반환값이 있는 경우, 클라이언트에게 아이디 전달
                
                return render_template('login.html', ID=row[0]['login_id'])
            
        elif loginData['type'] == 'find_pw': # 패스워드 찾기
            # 데이터베이스에 질의를 위한 SELECT문
            selectQuery = f"""
                SELECT * FROM TestUser WHERE 
                name='{loginData['name']}'
                AND login_id='{loginData['id']}' 
                AND email='{loginData['email']}';
            """

            row = exeQuery(SELECT=selectQuery) # 유저 데이터

            if row == [] : # SELECT 구문 실행 이후 아무런 값도 받지 못한 경우
                message = """
                    <script>
                        alert('일치하는 데이터가 없습니다. 입력 값을 다시 한 번 확인해 주세요');
                        location.href='/login/';
                    </script>
                """
                return render_template_string(message)

            else: # 반환값이 있는 경우, 임시 패스워드를 생성하여 유저에게 전달
               temp_pw = temp_pw_generator()
               updateQuery = f"UPDATE TestUser SET login_pw='{temp_pw}' WHERE id={row[0]['id']};"
               exeQuery(UPDATE=updateQuery)
               
               return render_template('login.html', PW=temp_pw)
            
        elif loginData['type'] == 'login': # 로그인 하기
            # 데이터베이스에 질의를 위한 SELECT문
            selectQuery = f"""
                SELECT * FROM TestUser WHERE 
                login_id='{loginData['id']}' 
                AND login_pw='{loginData['pw']}';
            """

            row = exeQuery(SELECT=selectQuery) # 유저 데이터

            if row == [] : # SELECT 구문 실행 이후 아무런 값도 받지 못한 경우
                message = """
                    <script>
                        alert('이메일 또는 패스워드를 다시 한 번 확인해 주세요');
                        location.href='/login/';
                    </script>
                """
                return render_template_string(message)

            else: # 반환값이 있는 경우, 클라이언트에게 쿠키를 전달하여 로그인 유지
                res = make_response(redirect('/'))
                res.set_cookie(key='user_id', value=f'{row[0]['id']}')
                return res

    find = request.args.get('find')

    return render_template('login.html', find=find) # 단순히 GET 요청을 보내 /login/ 경로로 접근한 경우, 'login.html' 템플릿 반환



# 회원가입 요청 처리
@app.route('/join/', methods=['GET', 'POST'])
def join():
    # /join/ 경로로 POST 요청을 보낸 경우, 데이터베이스에 데이터 저장하기
    if request.method == "POST":
        req = request.form.to_dict() # 유저의 데이터
        print(req)

        # 유저 정보 삽입 쿼리
        insertQuery = f"""
            INSERT INTO TestUser (
            track,
            plan,
            name,
            Affiliation,
            email,
            login_id,
            login_pw,
            date
            ) VALUES (
            '{req['track']}',
            '{req['plan']}',
            '{req['name']}',
            '{req['Affiliation']}',
            '{req['email']}',
            '{req['id']}',
            '{req['pw']}',
            '{datetime.datetime.now().replace(microsecond=0)}');
        """
        result = exeQuery(INSERT=insertQuery, SELECT="SELECT * FROM TestUser")
        print(result)
        message = """
            <script>
                alert("가입이 완료되었습니다");
                location.href='/login/';
            </script>
        """
        return render_template_string(message) # 가입 완료 메시지와 함께 /login/ 페이지로 리다이렉트
    
    # 사용 중인 아이디인지 검사하기
    login_id = request.args.get('login_id')
    if login_id:
        selectQuery = f"SELECT id FROM TestUser WHERE login_id='{login_id}';"
        idCheck = exeQuery(SELECT=selectQuery)
        if idCheck == []:
            return jsonify(True)
        return jsonify(False)
    
    return render_template('join.html') # 단순히 GET 요청을 보내 해당 경로로 접근한 경우 'join.html' 전달



# 체크리스트 작성 처리
@app.route('/checkList/', methods=['GET', 'POST'])
def postCheckList():
    userid = request.cookies.get('user_id') # 로그인 시 얻을 수 있는 쿠키를 검사해 로그인 상태를 확인하기
    if not userid:
        message = """
            <script>
                alert('해당 기능은 로그인 후 이용하실 수 있습니다');
                location.href='/login/';
            </script>
        """
        return render_template_string(message)
    
    selectQuery = f"""
        SELECT post_id, text FROM CheckList WHERE
        user_id = {userid};
    """

    if request.method == 'POST':
        postData = request.form.to_dict()
        if 'text' in postData:
            if postData['text'] == '':
                return redirect('/checkList/')
        if 'delete' in postData:
            deleteQuery = f"""
                DELETE FROM CheckList
                WHERE post_id={postData['delete']};
            """

            exeQuery(DELETE=deleteQuery) # 체크리스트 삭제 쿼리 실행

            return redirect('/checkList/')
        insertQuery = f"""
        INSERT INTO CheckList (
        user_id,
        text,
        date
        ) VALUES (
        {userid},
        '{postData['text']}',
        '{datetime.datetime.now().replace(microsecond=0)}'
        );
        """

        # 체크리스트 삽입 후 데이터베이스에 저장된 체크리스트 가져오기
        checkLists = exeQuery(INSERT=insertQuery, SELECT=selectQuery) 
        return render_template('checkList.html', loginState=True, checkLists=checkLists)
    
    # 단순 GET 요청을 보낸 경우
    checkLists = exeQuery(SELECT=selectQuery) # 체크리스트 가져오는 쿼리 실행
    return render_template('checkList.html', loginState=True, checkLists=checkLists)



# 게시판 렌더링
@app.route('/board/', methods=['GET'])
def board():
    userid = request.cookies.get('user_id') # 로그인 시 얻을 수 있는 쿠키를 검사해 로그인 상태를 확인하기
    # 로그인 후 쿠키가 있는 경우 해당 페이지에 접근 허용
    if userid:
        return render_template("board.html", loginState=True)
    
    message = """
        <script>
            alert('해당 기능은 로그인 후 이용하실 수 있습니다');
            location.href='/login/';
        </script>
    """
    return render_template_string(message) # 쿠키가 존재하지 않는 경우 로그인 페이지로 리다이렉트



# 검색 요청 처리
@app.route('/search/', methods=['POST'])
def search():
    data = json.loads(request.data) # 클라이언트에서 요청 보낸 json 포맷 데이터를 가져와 파싱
    print(data)
    exeQuery = data['Query'] # 클라이언트에서 가져온 SELECT 문 실행 쿼리
    print(exeQuery)
    connect = sqlite3.connect("test.db")
    connect.row_factory = sqlite3.Row
    connect.execute("PRAGMA foreign_keys = ON;")
    Cursor = connect.cursor()
    Cursor.execute(exeQuery)
    rows = Cursor.fetchall()
    connect.commit()
    connect.close()

    # 쿼리 실행 이후 반환된 데이터를 딕셔너리로 변환하여 json 포맷으로 클라이언트에게 전달
    data = []
    for row in rows:
        data.append(dict(row))
    print(len(data))
    return jsonify(data)

# 게시글 렌더링
@app.route('/view/', methods=['GET'])
def view():
    userid = request.cookies.get('user_id') # 로그인 시 얻을 수 있는 쿠키를 검사해 로그인 상태를 확인하기
    postid = request.args.get('post_id')
    secret_num = request.args.get('password')
    download_path = request.args.get('fileDownload')

    if userid == None: # 로그인 검사하기
        message = """
        <script>
            alert('해당 기능은 로그인 후 이용하실 수 있습니다');
            location.href='/login/';
        </script>
        """
        return render_template_string(message)
    
    if postid: # 게시글 조회 요청을 보낸 경우
        postData = exeQuery(SELECT=f"SELECT * FROM board WHERE post_id='{postid}';")[0]
        print(postData)

        if download_path: # 파일 다운로드 요청 처리
            return send_file(f"{download_path}", as_attachment=True)
           

        if postData['secret'] == 'False': # 비밀글로 설정되지 않은 경우 게시글 렌더링
            return render_template('view.html', loginState=True, postData=postData)
        
        if postData['secret'] == secret_num: # 전달된 패스워드가 비밀글 패스워드와 일치하면 게시글 렌더링
            return render_template('view.html', loginState=True, postData=postData)

        message = f"""
            <script>
                alert("비밀번호가 일치하지 않습니다. 다시 확인해 주세요");
                location.href='/board/';
            </script>
        """
        return render_template_string(message) # 비밀글 패스워드가 틀린 경우, /board/로 이동


# 글 작성 처리
@app.route('/writing/', methods=['GET', 'POST'])
def write():
    userid = request.cookies.get('user_id') # 로그인 시 얻을 수 있는 쿠키를 검사해 로그인 상태를 확인하기
    if not userid: # 로그인 상태가 아닌 경우 메시지 전달과 함께 /login/으로 리다이렉트
        message = """
            <script>
                alert('해당 기능은 로그인 후 이용하실 수 있습니다');
                location.href='/login/';
            </script>
        """
        return render_template_string(message)
    
    # 글 작성 데이터를 보낸 경우
    if request.method == 'POST':
        postData = request.form.to_dict() # 클라이언트에서 보낸 데이터를 딕셔너리로 파싱하기
        file = request.files['file_name']
        if "secret" not in postData:
            postData['secret'] = False

        print(postData)
        print(file.name)

        # 클라이언트에서 입력 폼에 아무런 데이터도 적지 않은 채 요청을 보낸 경우
        if postData['text'] == "" or postData['title'] == "":
            message = """
                <script>
                    alert("제목과 본문을 모두 작성해 주세요");
                    location.href='/writing/';
                </script>
            """
            return render_template_string(message)
        
        # 게시글 업데이트
        if "edit" in postData:
            updateQuery = f"""
                UPDATE board SET 
                title='{postData['title']}',
                text='{postData['text']}',
                file_name='{file.filename}',
                secret='{postData['secret']}'
                WHERE post_id='{postData['post_id']}';
            """

            # 게시글 업데이트
            exeQuery(UPDATE=updateQuery)

            message = """
                <script>
                    alert("수정 완료!");
                    location.href='/board/';
                </script>
            """
            return render_template_string(message)
        
        # 게시글 저장 쿼리
        insertQuery = f"""
            INSERT INTO board (
            user_id,
            user_name,
            plan,
            title,
            text,
            file_name,
            secret,
            date
            ) VALUES (
            {userid},
            (SELECT name FROM TestUser WHERE id='{userid}'),
            (SELECT plan FROM TestUser WHERE id='{userid}'),
            '{postData['title']}',
            '{postData['text']}',
            '{file.filename}',
            '{postData['secret']}',
            '{datetime.datetime.now().replace(microsecond=0)}'
            );
        """
        # 데이터 삽입
        exeQuery(INSERT=insertQuery)
        print(exeQuery(SELECT='SELECT * FROM board;'))

        # 전송된 파일이 있는 경우, 파일 업로드 진행
        if file.filename != "":
            uploadPath = os.path.join(app.root_path, 'static', 'postData', userid)
            print(uploadPath)
            os.makedirs(uploadPath, exist_ok=True)
            file.save(os.path.join(uploadPath, f"{file.filename}"))

        message = """
            <script>
                alert("작성 완료!");
                location.href='/board/';
            </script>
        """
        return render_template_string(message)
    
    # 게시글 수정 또는 삭제 처리
    param = request.args.get('edit')
    post_id = request.args.get('post_id')
    
    if param == 'delete' and post_id: # 게시글 삭제 처리

        deleteQuery = f"DELETE FROM board WHERE post_id={post_id};"
        # 게시글 삭제 쿼리 실행
        exeQuery(DELETE=deleteQuery)
        massage = """
            <script>
                alert("글이 삭제되었습니다");
                location.href='/board/';
            </script>
        """
        return render_template_string(massage)
    
    if param == 'modify' and post_id: # 게시글 수정 처리

        # 데이터베이스에서 기존의 데이터를 가져와 입력 폼에 랜더링 할 수 있도록 SELECT 쿼리를 사용함
        selectQuery = f"SELECT * FROM board WHERE post_id='{post_id}';"
        
        postData = exeQuery(SELECT=selectQuery)[0] # 게시글 데이터 가져오기
        

        return render_template("writing.html", loginState=True, postData=postData)

    return render_template('writing.html', loginState=True)


#댓글 작성 처리
@app.route('/api/comment/', methods=['POST'])
def comment():

    data = json.loads(request.data)  # 클라이언트에서 보낸 json 포맷 데이터 파싱하기
    cookie = request.cookies.get('user_id')
    print(data)
    if data['QueryType'] == 'SELECT': # 이미 작성된 댓글을 가져와 브라우저에 출력하는 경우
        exeQuery = data['Query'] # 브라우저에서 전달한 쿼리
        print(data)
        connect = sqlite3.connect("test.db")
        connect.row_factory = sqlite3.Row
        connect.execute("PRAGMA foreign_keys = ON;")
        Cursor = connect.cursor()
        Cursor.execute(exeQuery)
        rows = Cursor.fetchall()
        connect.commit()
        connect.close()
        data = []
        for row in rows:
            data.append(dict(row))
        return jsonify(data) # 쿼리 실행 결과 반환된 데이터 전송
    
    if data['QueryType'] == 'INSERT': # 새로운 댓글을 작성한 경우
        print(data)
        connect = sqlite3.connect("test.db")
        connect.execute("PRAGMA foreign_keys = ON;")
        Cursor = connect.cursor()
        
        # 데이터베이스 삽입을 위한 쿼리
        exeQuery = f"""
            INSERT INTO comment (
            post_id,
            user_id,
            user_name,
            plan,
            text,
            date
            ) VALUES (
            '{data['post_id']}',
            '{cookie}',
            (SELECT name FROM TestUser WHERE id='{data['user_id']}'),
            (SELECT plan FROM TestUser WHERE id='{data['user_id']}'),
            '{data['data']}',
            '{datetime.datetime.now().replace(microsecond=0)}'
            );
        """
        print(exeQuery)
        Cursor.execute(exeQuery)
        connect.commit()
        connect.close()
        return jsonify({"request": "success"})


# 멤버 리스트
@app.route('/memberList/', methods=['GET'])
def memberList():
    cookie = request.cookies.get('user_id')
    if str(cookie) == str(1):
        selectQuery = f"SELECT * FROM TestUser"
        userData = exeQuery(SELECT=selectQuery)
        return render_template('memberList.html', loginState=True, userData=userData)
    
    message = """
        <script>
            alert("접근이 제한되었습니다");
            location.href='/';
        </script>
    """
    return render_template_string(message)

# 프로필 조회하기
@app.route('/profile/', methods=['GET'])
def profile():
    cookie = request.cookies.get('user_id')
    userid = request.args.get('user_id')

    if bool(cookie) == False: # 로그인 되어 있지 않은 경우
        message = """
            <script>
                alert("해당 기능은 로그인 후 사용 가능합니다");
                location.href='/login/';
            </script>
        """
        return render_template_string(message)
    
    if userid: # 다른 사용자의 정보를 조회한 경우
        selectUserData = f"SELECT * FROM TestUser WHERE id='{userid}';"
        selectCheckListData = f"SELECT text FROM CheckList WHERE user_id='{userid}';"
        selectPostCount = f"SELECT COUNT(*) FROM board WHERE user_id='{userid}';"
        selectcommentCount = f"SELECT COUNT(*) FROM comment WHERE user_id='{userid}';"
        userData = exeQuery(SELECT=selectUserData)[0]
        checkListData = exeQuery(SELECT=selectCheckListData)
        postCount = exeQuery(SELECT=selectPostCount)[0]['COUNT(*)']
        commentCount = exeQuery(SELECT=selectcommentCount)[0]['COUNT(*)']
        return render_template('profile.html', loginState=True, checkListData=checkListData, postCount=postCount, commentCount=commentCount, userData=userData, view=True)
    
    else: # 자신의 정보를 조회한 경우
        selectUserData = f"SELECT * FROM TestUser WHERE id='{cookie}';"
        selectCheckListData = f"SELECT text FROM CheckList WHERE user_id='{cookie}';"
        selectPostCount = f"SELECT COUNT(*) FROM board WHERE user_id='{cookie}';"
        selectCommentCount = f"SELECT COUNT(*) FROM comment WHERE user_id='{cookie}';"
        userData = exeQuery(SELECT=selectUserData)[0]
        checkListData = exeQuery(SELECT=selectCheckListData)
        postCount = exeQuery(SELECT=selectPostCount)[0]['COUNT(*)']
        commentCount = exeQuery(SELECT=selectCommentCount)[0]['COUNT(*)']
        return render_template('profile.html', loginState=True, checkListData=checkListData, postCount=postCount, commentCount=commentCount, userData=userData)
    

# 계정 정보 수정하기
@app.route('/myAccount/', methods=['GET', 'POST'])
def account():
    cookie = request.cookies.get('user_id')
    
    if bool(cookie) == False: # 로그인 되어 있지 않은 경우
        message = """
            <script>
                alert("해당 기능은 로그인 후 사용 가능합니다");
                location.href='/login/';
            </script>
        """
        return render_template_string(message)
    
    if request.method == 'POST': # 사용자의 계정 정보 업데이트 요청 처리하기
        postData = request.form.to_dict()
        file = request.files['file_name']
        fileName = file.filename

        if fileName == "":
            fileName = '/static/images/default.png'
        else:
            fileName = f'/static/images/{cookie}/{fileName}'
            
        print(fileName)

        updateQuery = f"""
            UPDATE TestUser SET 
            login_pw='{postData['login_pw']}',
            email='{postData['email']}',
            affiliation='{postData['affiliation']}',
            file_name='{fileName}'
            WHERE id='{cookie}';
        """
        exeQuery(UPDATE=updateQuery)
        print(exeQuery(SELECT=f"SELECT * FROM TestUser WHERE id='{cookie}';")[0])

        # 전송된 파일이 있는 경우, 파일 업로드 진행
        if file.filename != '':
            uploadPath = os.path.join(app.root_path, 'static', 'images', cookie)
            print(uploadPath)
            os.makedirs(uploadPath, exist_ok=True)
            file.save(os.path.join(uploadPath, f"{file.filename}"))

        message = """
            <script>
                alert("수정되었습니다");
                location.href='/profile/';
            </script>
        """
        return render_template_string(message)


    selectUserData = f"SELECT * FROM TestUser WHERE id='{cookie}';"
    selectCheckListData = f"SELECT text FROM CheckList WHERE user_id='{cookie}';"
    selectPostCount = f"SELECT COUNT(*) FROM board WHERE user_id='{cookie}';"
    selectCommentCount = f"SELECT COUNT(*) FROM comment WHERE user_id='{cookie}';"
    userData = exeQuery(SELECT=selectUserData)[0]
    checkListData = exeQuery(SELECT=selectCheckListData)
    postCount = exeQuery(SELECT=selectPostCount)[0]['COUNT(*)']
    commentCount = exeQuery(SELECT=selectCommentCount)[0]['COUNT(*)']
    return render_template('myAccount.html', loginState=True, checkListData=checkListData, postCount=postCount, commentCount=commentCount, userData=userData)


# 로그아웃 처리
@app.route('/logOut/', methods=['GET'])
def logOut():
    message = """
        <script>
            alert("로그아웃 되었습니다");
            location.href='/';
        </script>
    """
    res = make_response(render_template_string(message)) # 응답 객체 생성하기
    res.delete_cookie('user_id') # 로그인 인증을 위해 발급했던 쿠키 제거하기
    return res

# 회원 탈퇴 처리
@app.route('/exit/', methods=['GET', 'POST'])
def exit():
    if request.method == 'POST':
        userData = request.form.to_dict() # 클라이언트에서 전달된 유저의 데이터
        
        # 데이터베이스에서 해당 유저를 삭제하기 위한 DELETE 쿼리
        deleteQuery = f"DELETE FROM TestUser WHERE login_id='{userData['id']}' and login_pw='{userData['pw']}';"
        exeQuery(DELETE=deleteQuery) # 삭제하기
        message = """
            <script>
                alert("정상적으로 탈퇴 처리 되었습니다");
                location.href='/';
            </script>
        """
        res = make_response(render_template_string(message)) # 응답 객체 생성하기
        res.delete_cookie('user_id') # 발급했던 쿠키 제거하기
        return res
    return render_template('exit.html', loginState=True)


# 템플릿 테스트용
@app.route('/templateTest/', methods=["GET"])
def test():

    selectQuery = f"SELECT * FROM TestUser WHERE id='1';"
    userData = exeQuery(SELECT=selectQuery)[0]
    print(userData)
    return render_template('myAccount.html', loginState=True, userData=userData)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) # 도커 파일을 작성하여 컨테이너를 실행하기 위해 같은 네트워크 내 접근을 허용함.