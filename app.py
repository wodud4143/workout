import os
import sqlite3
from flask import Flask, render_template, abort, g, request, jsonify, redirect, url_for, flash
from datetime import datetime
import calendar

app = Flask(__name__)
app.secret_key = 'your-secret-key'
app.config['DATABASE'] = os.path.join(app.root_path, 'workout.db')

def get_db():
    db = getattr(g, '_database', None)
    if not db:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db

@app.before_request
def init_db():
    db = get_db()
    db.execute('''
      CREATE TABLE IF NOT EXISTS record (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        routine TEXT NOT NULL
      )
    ''')
    db.execute('''
      CREATE TABLE IF NOT EXISTS record_detail (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id INTEGER NOT NULL,
        exercise TEXT NOT NULL,
        total_sets INTEGER NOT NULL,
        success INTEGER NOT NULL,
        fail INTEGER NOT NULL,
        weight REAL NOT NULL,
        FOREIGN KEY(record_id) REFERENCES record(id) ON DELETE CASCADE
      )
    ''')
    db.execute('''
      CREATE TABLE IF NOT EXISTS weights (
        exercise TEXT PRIMARY KEY,
        weight REAL
      )
    ''')
    db.commit()

@app.teardown_appcontext
def close_db(exc):
    db = getattr(g, '_database', None)
    if db:
        db.close()

ROUTINES = {
    'push': [
        { 'name': '벤치프레스', 'sets': 3, 'reps': '8-10' },
        { 'name': '머신 숄더 프레스', 'sets': 3, 'reps': '10-12' },
        { 'name': '펙덱 플라이', 'sets': 3, 'reps': '15-20' },
        { 'name': '케이블 레터럴 레이즈', 'sets': 3, 'reps': '10-15' },
        { 'name': '오버헤드 케이블 익스텐션', 'sets': 3, 'reps': '5-10' },
        { 'name': '케이블 킥백', 'sets': 3, 'reps': '10-15' }
    ],
    'pull': [
        { 'name': '클로즈 그립 랫 풀다운', 'sets': 3, 'reps': '10-15' },
        { 'name': '체스트 서포트 머신 로우', 'sets': 3, 'reps': '8-10' },
        { 'name': '클로즈 그립 케이블 로우', 'sets': 2, 'reps': '15-20' },
        { 'name': '리버스 케이블 플라이', 'sets': 3, 'reps': '15-20' },
        { 'name': '슈러그', 'sets': 4, 'reps': '15-20' },
        { 'name': 'EZ바 컬', 'sets': 3, 'reps': '10-15' },
        { 'name': '머신 프리쳐컬', 'sets': 3, 'reps': '15-20' }
    ],
    'leg': [
        { 'name': '시티드 레그 컬', 'sets': 3, 'reps': '10-15' },
        { 'name': '스미스 머신 스쿼트', 'sets': 3, 'reps': '5-10' },
        { 'name': '루마니안 데드리프트', 'sets': 3, 'reps': '5-10' },
        { 'name': '레그 익스텐션', 'sets': 3, 'reps': '10-15' },
        { 'name': '어덕션 & 힙 어브덕션', 'sets': 2, 'reps': '15-20' },
        { 'name': '스탠딩 카프 레이즈', 'sets': 4, 'reps': '10-15' }
    ]
}

@app.route('/')
def index():
    return render_template('index.html', routines=ROUTINES)

@app.route('/routine/<string:name>')
def routine(name):
    routine_list = ROUTINES.get(name)
    if not routine_list:
        abort(404)
    db = get_db()
    rows = db.execute('SELECT exercise, weight FROM weights').fetchall()
    weight_map = {r['exercise']: r['weight'] for r in rows}

    exercises = []
    for ex in routine_list:
        e = ex.copy()
        e['weight'] = weight_map.get(e['name'], '')
        exercises.append(e)

    return render_template('routine.html', name=name, exercises=exercises)

@app.route('/record', methods=['POST'])
def add_record():
    data = request.get_json()
    routine = data.get('routine')
    details = data.get('details', [])
    if routine not in ROUTINES:
        return jsonify({'error':'invalid routine'}), 400

    db = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    cur = db.execute(
        'INSERT INTO record (date, routine) VALUES (?, ?)',
        (today, routine)
    )
    record_id = cur.lastrowid

    for d in details:
        db.execute(
            'INSERT INTO record_detail '
            '(record_id, exercise, total_sets, success, fail, weight) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (record_id, d['name'], d['total_sets'], d['success'], d['fail'], d['weight'])
        )
    db.commit()
    return jsonify({'status':'ok'})

@app.route('/records')
def records():
    now = datetime.now()
    year, month = now.year, now.month
    cal = calendar.monthcalendar(year, month)

    db = get_db()
    rows = db.execute(
        "SELECT id, date, routine FROM record WHERE date LIKE ?",
        (f'{year:04d}-{month:02d}-%',)
    ).fetchall()

    records_by_day = {}
    for r in rows:
        day = int(r['date'].split('-')[2])
        records_by_day.setdefault(day, []).append(r['routine'])

    return render_template('records.html',
                           year=year, month=month,
                           cal=cal, records=records_by_day)

@app.route('/trend/<string:routine>')
def trend(routine):
    if routine not in ROUTINES:
        abort(404)
    db = get_db()
    rows = db.execute(
        "SELECT r.date, d.exercise, d.weight FROM record r "
        "JOIN record_detail d ON r.id=d.record_id "
        "WHERE r.routine = ? ORDER BY r.date",
        (routine,)
    ).fetchall()

    trend_data = {}
    for ex in ROUTINES[routine]:
        trend_data[ex['name']] = []
    for row in rows:
        ex_name = row['exercise'].strip()      
        if ex_name in trend_data:
            trend_data[ex_name].append({
                'date': row['date'],
                'weight': row['weight']
            })
     # else: DB에 저장된 이름이 ROUTINES에 없는 경우 무시

    return render_template('trend.html',
                           routine=routine,
                           trend_data=trend_data)

@app.route('/settings', methods=['GET','POST'])
def settings():
    db = get_db()
    exercise_names = sorted({ex['name'] for lst in ROUTINES.values() for ex in lst})

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'apply_all':
            bulk = request.form.get('bulk_weight', '').strip()
            try:
                w = float(bulk)
                for name in exercise_names:
                    db.execute(
                        'INSERT OR REPLACE INTO weights(exercise, weight) VALUES (?, ?)',
                        (name, w)
                    )
                db.commit()
                flash(f'모든 종목에 {w}kg 일괄 적용되었습니다.')
            except ValueError:
                flash('유효한 숫자를 입력해주세요.')
            return redirect(url_for('settings'))

        if action == 'reset_all':
            db.execute('DELETE FROM weights')
            db.commit()
            flash('모든 무게 설정이 초기화되었습니다.')
            return redirect(url_for('settings'))

        for name, val in request.form.items():
            if name in exercise_names:
                v = val.strip()
                if v == '':
                    db.execute('DELETE FROM weights WHERE exercise=?', (name,))
                else:
                    try:
                        w = float(v)
                        db.execute(
                            'INSERT OR REPLACE INTO weights(exercise, weight) VALUES (?, ?)',
                            (name, w)
                        )
                    except ValueError:
                        pass
        db.commit()
        flash('개별 무게 설정이 저장되었습니다.')
        return redirect(url_for('settings'))

    rows = db.execute('SELECT exercise, weight FROM weights').fetchall()
    weight_map = {r['exercise']: r['weight'] for r in rows}
    return render_template('settings.html',
                           exercises=exercise_names,
                           weight_map=weight_map)

if __name__ == '__main__':
    app.run(debug=True)
