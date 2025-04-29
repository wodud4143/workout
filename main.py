# main.py
from fastapi import FastAPI, HTTPException, Depends, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import List, Optional, Dict, Any
import json
import os

# 데이터베이스 모듈 가져오기
from database import engine, SessionLocal
import models

# 데이터베이스 테이블 생성
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="운동 트래커")

# 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 기본 운동 루틴 데이터
default_routines = {
    'push': [
        {'name': '벤치프레스', 'sets': 3, 'reps': '8-10', 'weight': 0},
        {'name': '머신 숄더 프레스', 'sets': 3, 'reps': '10-12', 'weight': 0},
        {'name': '펙덱 플라이', 'sets': 3, 'reps': '15-20', 'weight': 0},
        {'name': '케이블 레터럴 레이즈', 'sets': 3, 'reps': '10-15', 'weight': 0},
        {'name': '오버헤드 케이블 익스텐션', 'sets': 3, 'reps': '5-10', 'weight': 0},
        {'name': '케이블 킥백', 'sets': 3, 'reps': '10-15', 'weight': 0}
    ],
    'pull': [
        {'name': '클로즈 그립 랫 풀다운', 'sets': 3, 'reps': '10-15', 'weight': 0},
        {'name': '체스트 서포트 머신 로우', 'sets': 3, 'reps': '8-10', 'weight': 0},
        {'name': '클로즈 그립 케이블 로우', 'sets': 2, 'reps': '15-20', 'weight': 0},
        {'name': '리버스 케이블 플라이', 'sets': 3, 'reps': '15-20', 'weight': 0},
        {'name': '슈러그', 'sets': 4, 'reps': '15-20', 'weight': 0},
        {'name': 'EZ바 컬', 'sets': 3, 'reps': '10-15', 'weight':.0},
        {'name': '머신 프리쳐컬', 'sets': 3, 'reps': '15-20', 'weight': 0}
    ],
    'leg': [
        {'name': '시티드 레그 컬', 'sets': 3, 'reps': '10-15', 'weight': 0},
        {'name': '스미스 머신 스쿼트', 'sets': 3, 'reps': '5-10', 'weight': 0},
        {'name': '루마니안 데드리프트', 'sets': 3, 'reps': '5-10', 'weight': 0},
        {'name': '레그 익스텐션', 'sets': 3, 'reps': '10-15', 'weight': 0},
        {'name': '어덕션 & 힙 어브덕션', 'sets': 2, 'reps': '15-20', 'weight': 0},
        {'name': '스탠딩 카프 레이즈', 'sets': 4, 'reps': '10-15', 'weight': 0}
    ]
}

# 설정 파일 경로
SETTINGS_FILE = "exercise_settings.json"

# 설정 파일 초기화
def initialize_settings():
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(default_routines, f, ensure_ascii=False, indent=4)
    
    return load_settings()

# 설정 파일 로드
def load_settings():
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)

# 설정 저장
def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)

# 의존성 주입을 위한 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 메인 페이지
@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    settings = initialize_settings()
    return templates.TemplateResponse("index.html", {"request": request, "routines": settings})

# 루틴 페이지
@app.get("/routine/{routine_type}", response_class=HTMLResponse)
async def routine_page(request: Request, routine_type: str, db: Session = Depends(get_db)):
    settings = load_settings()
    if routine_type not in settings:
        raise HTTPException(status_code=404, detail="루틴을 찾을 수 없습니다")
    
    # 오늘 이미 해당 루틴을 수행했는지 확인
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    today_session = db.query(models.WorkoutSession).filter(
        models.WorkoutSession.routine_type == routine_type,
        models.WorkoutSession.date >= today_start,
        models.WorkoutSession.date <= today_end
    ).first()
    
    already_done_today = today_session is not None
    
    return templates.TemplateResponse(
        "routine.html",
        {
            "request": request,
            "routine_type": routine_type,
            "exercises": settings[routine_type],
            "already_done_today": already_done_today
        }
    )

# 운동 세션 저장
@app.post("/save-session")
async def save_session(session_data: Dict[str, Any], db: Session = Depends(get_db)):
    try:
        # 오늘 이미 해당 루틴을 수행했는지 확인
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        existing_session = db.query(models.WorkoutSession).filter(
            models.WorkoutSession.routine_type == session_data["routine_type"],
            models.WorkoutSession.date >= today_start,
            models.WorkoutSession.date <= today_end
        ).first()
        
        if existing_session:
            # 기존 세션이 있으면 관련된 모든 운동 세트 삭제
            db.query(models.ExerciseSet).filter(
                models.ExerciseSet.session_id == existing_session.id
            ).delete()
            
            # 기존 세션 ID 재사용
            session_id = existing_session.id
            
            # 세션 날짜 업데이트
            existing_session.date = datetime.now()
            db.add(existing_session)
            
        else:
            # 새 세션 생성
            new_session = models.WorkoutSession(
                date=datetime.now(),
                routine_type=session_data["routine_type"]
            )
            db.add(new_session)
            db.flush()  # ID 생성
            session_id = new_session.id
        
        # 운동 세트 기록 저장
        for exercise in session_data["exercises"]:
            for set_idx, set_data in enumerate(exercise["sets"]):
                if set_data["status"] in ["success", "fail"]:  # 완료된 세트만 저장
                    exercise_set = models.ExerciseSet(
                        session_id=session_id,
                        exercise_name=exercise["name"],
                        set_number=int(set_data["set_number"]) if isinstance(set_data["set_number"], str) else set_data["set_number"],
                        weight=float(exercise["weight"]),
                        status=set_data["status"]
                    )
                    db.add(exercise_set)
        
        db.commit()
        return {"success": True, "session_id": session_id}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# 운동 세션 중 무게 업데이트
@app.post("/update-weight-during-workout")
async def update_weight_during_workout(
    routine_type: str = Form(...),
    exercise_name: str = Form(...),
    weight: float = Form(...)
):
    try:
        settings = load_settings()
        
        # 해당 운동 무게 업데이트
        for exercise in settings[routine_type]:
            if exercise["name"] == exercise_name:
                exercise["weight"] = weight
                break
        
        save_settings(settings)
        return {"success": True}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

# 운동 기록 페이지
@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request, db: Session = Depends(get_db)):
    # 모든 세션 가져오기 (날짜별로 그룹화된)
    sessions = db.query(models.WorkoutSession).order_by(
        models.WorkoutSession.date.desc()
    ).all()
    
    # 날짜별, 루틴별로 세션 그룹화 (가장 최신 세션만 유지)
    sessions_by_date = {}
    routine_by_date = {}  # 날짜별로 이미 추가된 루틴 유형 추적
    
    for session in sessions:
        date_str = session.date.strftime("%Y-%m-%d")
        
        # 해당 날짜 키가 없으면 생성
        if date_str not in sessions_by_date:
            sessions_by_date[date_str] = []
            routine_by_date[date_str] = set()
        
        # 이미 같은 날짜에 같은 루틴 타입이 있는지 확인
        if session.routine_type not in routine_by_date[date_str]:
            # 새로운 루틴 타입이면 추가
            sessions_by_date[date_str].append({
                "id": session.id,
                "routine_type": session.routine_type,
                "date": session.date.strftime("%Y-%m-%dT%H:%M:%S")
            })
            routine_by_date[date_str].add(session.routine_type)
    
    return templates.TemplateResponse(
        "history.html",
        {"request": request, "sessions_by_date": sessions_by_date}
    )

# 세션 상세 정보
@app.get("/session/{session_id}", response_class=HTMLResponse)
async def session_detail(request: Request, session_id: int, db: Session = Depends(get_db)):
    session = db.query(models.WorkoutSession).filter(models.WorkoutSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    
    # 해당 세션의 모든 운동 세트 가져오기
    exercise_sets = db.query(models.ExerciseSet).filter(
        models.ExerciseSet.session_id == session_id
    ).all()
    
    # 운동별로 그룹화
    exercises = {}
    for exercise_set in exercise_sets:
        if exercise_set.exercise_name not in exercises:
            exercises[exercise_set.exercise_name] = {
                "sets": [],
                "weight": exercise_set.weight,
                "success_count": 0,
                "fail_count": 0
            }
        
        exercises[exercise_set.exercise_name]["sets"].append({
            "set_number": exercise_set.set_number,
            "status": exercise_set.status
        })
        
        if exercise_set.status == "success":
            exercises[exercise_set.exercise_name]["success_count"] += 1
        elif exercise_set.status == "fail":
            exercises[exercise_set.exercise_name]["fail_count"] += 1
    
    return templates.TemplateResponse(
        "session_detail.html",
        {
            "request": request,
            "session": session,
            "exercises": exercises
        }
    )

# 운동 종목별 무게 추이 데이터
@app.get("/exercise-progress/{exercise_name}")
async def exercise_progress(exercise_name: str, db: Session = Depends(get_db)):
    # 해당 운동의 모든 세트 가져오기 (세션 정보와 함께)
    exercise_sets = db.query(models.ExerciseSet, models.WorkoutSession).join(
        models.WorkoutSession,
        models.ExerciseSet.session_id == models.WorkoutSession.id
    ).filter(
        models.ExerciseSet.exercise_name == exercise_name
    ).order_by(
        models.WorkoutSession.date
    ).all()
    
    # 날짜별로 그룹화하여 평균 무게 계산
    progress_data = {}
    for exercise_set, session in exercise_sets:
        date_str = session.date.strftime("%Y-%m-%d")
        if date_str not in progress_data:
            progress_data[date_str] = {
                "total_weight": 0,
                "count": 0
            }
        
        progress_data[date_str]["total_weight"] += exercise_set.weight
        progress_data[date_str]["count"] += 1
    
    # 평균 무게 계산 (JSON 직렬화 가능한 형태로 반환)
    result = []
    for date_str, data in progress_data.items():
        avg_weight = data["total_weight"] / data["count"] if data["count"] > 0 else 0
        result.append({
            "date": date_str,
            "weight": float(avg_weight)  # 확실하게 float으로 변환
        })
    
    return result

# 운동 무게 설정 페이지
@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    settings = load_settings()
    return templates.TemplateResponse("settings.html", {"request": request, "routines": settings})

# 루틴 전체 업데이트
@app.post("/save-routine")
async def save_routine(request: Request, routine_type: str = Form(...)):
    try:
        form_data = await request.form()
        settings = load_settings()
        
        # 폼 데이터 파싱
        for exercise in settings[routine_type]:
            name = exercise["name"]
            weight_key = f"weight_{name}"
            sets_key = f"sets_{name}"
            reps_key = f"reps_{name}"
            
            if weight_key in form_data:
                exercise["weight"] = float(form_data[weight_key])
            if sets_key in form_data:
                exercise["sets"] = int(form_data[sets_key])
            if reps_key in form_data:
                exercise["reps"] = form_data[reps_key]
        
        save_settings(settings)
        return RedirectResponse(url="/settings", status_code=status.HTTP_303_SEE_OTHER)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 루틴 내 모든 운동 무게 일괄 업데이트
@app.post("/update-all-weights")
async def update_all_weights(
    routine_type: str = Form(...),
    weight: float = Form(...)
):
    settings = load_settings()
    
    # 모든 운동의 무게를 지정된 값으로 설정
    for exercise in settings[routine_type]:
        exercise["weight"] = weight
    
    save_settings(settings)
    return RedirectResponse(url="/settings", status_code=status.HTTP_303_SEE_OTHER)

# 루틴 초기화 (무게만 0으로)
@app.post("/reset-weights")
async def reset_weights(routine_type: str = Form(...)):
    settings = load_settings()
    
    # 모든 운동의 무게를 0으로 초기화
    for exercise in settings[routine_type]:
        exercise["weight"] = 0
    
    save_settings(settings)
    return RedirectResponse(url="/settings", status_code=status.HTTP_303_SEE_OTHER)

# 운동 세트 수와 반복 횟수 초기화 (기본값으로)
@app.post("/reset-routine")
async def reset_routine(routine_type: str = Form(...)):
    settings = load_settings()
    default_settings = default_routines
    
    # 해당 루틴의 모든 운동을 기본값으로 초기화
    # 단, 무게는 현재 값 유지
    for i, exercise in enumerate(settings[routine_type]):
        current_weight = exercise["weight"]
        settings[routine_type][i] = default_routines[routine_type][i].copy()
        settings[routine_type][i]["weight"] = current_weight
    
    save_settings(settings)
    return RedirectResponse(url="/settings", status_code=status.HTTP_303_SEE_OTHER)

# 무게 추이 그래프 페이지
@app.get("/progress-graph", response_class=HTMLResponse)
async def progress_graph_page(request: Request):
    settings = load_settings()
    
    # 모든 운동 종목 목록 생성
    all_exercises = []
    for routine_type, exercises in settings.items():
        for exercise in exercises:
            all_exercises.append(exercise["name"])
    
    return templates.TemplateResponse(
        "progress_graph.html",
        {"request": request, "exercises": all_exercises}
    )

# 앱 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)