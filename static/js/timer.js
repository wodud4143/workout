// 타이머 관련 변수
let timerInterval;
let timerRunning = false;
let completedExercises = 0;
let totalExercises = 0;
let lastTimer = 60; // 마지막으로 설정한 타이머 값(초)
let timerEndTime = null; // 타이머 종료 예정 시간

// 페이지 로딩 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 알림 권한 요청
    requestNotificationPermission();
    
    // 총 운동 개수 설정
    const exerciseCards = document.querySelectorAll('.exercise-card');
    totalExercises = exerciseCards.length;
    
    // 초기 진행률 업데이트
    updateRoutineProgress();
    
    // 세트 클릭 이벤트 리스너 등록
    setupSetCircleListeners();
    
    // 무게 폼 이벤트 처리
    setupWeightFormSubmission();
    
    // 타이머 상태 복원 시도
    restoreTimerState();
});

// 세트 클릭 이벤트 리스너 설정
function setupSetCircleListeners() {
    const setCircles = document.querySelectorAll('.set-circle');
    setCircles.forEach(circle => {
        circle.addEventListener('click', function() {
            onCircleClick(this);
        });
    });
}

// 무게 폼 제출 이벤트 처리
function setupWeightFormSubmission() {
    const weightForms = document.querySelectorAll('.weight-form');
    weightForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault(); // 기본 제출 동작 방지
            
            const formData = new FormData(this);
            const exerciseName = formData.get('exercise');
            const weight = formData.get('weight');
            
            // 서버에 무게 업데이트 요청
            fetch('/update_weight', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (response.ok) {
                    // 성공적으로 업데이트되면 알림 표시
                    showNotification(`${exerciseName} 무게가 ${weight}kg으로 업데이트되었습니다.`);
                }
            })
            .catch(error => {
                console.error('무게 업데이트 오류:', error);
            });
        });
    });
}

// 알림 권한 요청 함수
function requestNotificationPermission() {
    if ('Notification' in window) {
        if (Notification.permission !== "granted" && Notification.permission !== "denied") {
            Notification.requestPermission();
        }
    }
}

// 알림 표시 함수
function showNotification(message) {
    // 브라우저 내 알림 표시
    const notificationElement = document.createElement('div');
    notificationElement.className = 'notification';
    notificationElement.textContent = message;
    
    document.body.appendChild(notificationElement);
    
    // 3초 후 알림 자동 제거
    setTimeout(() => {
        notificationElement.classList.add('fadeout');
        setTimeout(() => {
            document.body.removeChild(notificationElement);
        }, 500);
    }, 3000);
}

// 세트 상태 업데이트 함수
function updateSetStatus(element, state) {
    // 기존 클래스 제거
    element.classList.remove('success', 'fail');
    
    // 새 상태에 따라 클래스 추가
    if (state === 1) {
        element.classList.add('success');
    } else if (state === 2) {
        element.classList.add('fail');
    }
    
    // 데이터 상태 업데이트
    element.setAttribute('data-state', state.toString());
    
    // 해당 세트의 hidden input 값 업데이트
    const exerciseName = element.getAttribute('data-ex');
    const setIndex = element.getAttribute('data-set');
    
    // 올바른 input 선택을 위한 고유 ID 사용
    const inputId = `input_${exerciseName}_${setIndex}`;
    const statusInput = document.getElementById(inputId);
    
    if (statusInput) {
        statusInput.value = state.toString();
    }
}

// 운동 완료 상태 업데이트 함수
function updateRoutineProgress() {
    // 모든 운동 카드를 검사하여 완료된 운동 수 계산
    const exerciseCards = document.querySelectorAll('.exercise-card');
    let completed = 0;
    
    exerciseCards.forEach(card => {
        const sets = card.querySelectorAll('.set-circle');
        const completedSets = Array.from(sets).filter(set => 
            set.classList.contains('success') || set.classList.contains('fail')
        ).length;
        const totalSets = sets.length;
        
        // 모든 세트가 시도되면 운동 완료로 간주
        if (completedSets === totalSets) {
            completed++;
        }
        
        // 진행률 표시줄 업데이트
        const progressFill = card.querySelector('.progress-fill');
        if (progressFill) {
            const progress = totalSets > 0 ? (completedSets / totalSets) * 100 : 0;
            progressFill.style.width = `${progress}%`;
        }
    });
    
    // 전체 루틴 진행률 업데이트
    const progressElement = document.getElementById('routine-progress');
    if (progressElement) {
        progressElement.textContent = `${completed}/${totalExercises}`;
    }
    
    // 전역 변수 업데이트
    completedExercises = completed;
}

// 세트 클릭 처리 함수
function onCircleClick(el) {
    if (!el) return;
    
    const currentState = parseInt(el.getAttribute('data-state') || '0');
    const exerciseName = el.getAttribute('data-ex');
    
    let newState;
    let timerDuration;
    
    // 상태 순환: 0(미완료) -> 1(성공) -> 2(실패) -> 0(미완료)
    if (currentState === 0) {
        // 성공 상태로 변경
        newState = 1;
        timerDuration = 60; // 성공 후 기본 휴식 시간
    } else if (currentState === 1) {
        // 실패 상태로 변경
        newState = 2;
        timerDuration = 90; // 실패 후 더 긴 휴식 시간
    } else {
        // 초기 상태로 돌아감
        newState = 0;
        timerDuration = 0; // 타이머 시작 안함
    }
    
    // 상태 업데이트
    updateSetStatus(el, newState);
    
    // 타이머 시작 (값이 0보다 클 때만)
    if (timerDuration > 0) {
        startTimer(timerDuration);
    }
    
    // 진행률 업데이트
    updateRoutineProgress();
    
    // 로컬 스토리지에 상태 저장
    saveExerciseState();
}

// 타이머 시작 함수
function startTimer(sec) {
    // 유효한 시간값인지 확인
    if (!sec || sec <= 0 || isNaN(sec)) {
        sec = 60; // 기본값
    }
    
    // 이미 실행 중인 타이머가 있다면 초기화
    if (timerRunning) {
        clearInterval(timerInterval);
    }
    
    // 타이머 설정
    let remaining = sec;
    const timerEl = document.getElementById('timer');
    timerRunning = true;
    lastTimer = sec;
    
    // 종료 예정 시간 저장
    timerEndTime = Date.now() + (sec * 1000);
    
    // 타이머 업데이트
    updateTimerDisplay();
    
    // 타이머 인터벌 설정
    timerInterval = setInterval(() => {
        remaining--;
        updateTimerDisplay();
        
        // 타이머 종료 처리
        if (remaining <= 0) {
            clearInterval(timerInterval);
            timerRunning = false;
            timerEndTime = null;
            playTimerEndSound();
            
            // 로컬 스토리지에서 타이머 상태 제거
            localStorage.removeItem('timerEndTime');
        } else {
            // 타이머 상태 저장
            localStorage.setItem('timerEndTime', timerEndTime);
            localStorage.setItem('lastTimer', lastTimer);
        }
    }, 1000);
    
    // 타이머 표시 업데이트 함수
    function updateTimerDisplay() {
        if (timerEl) {
            let m = Math.floor(remaining / 60);
            let s = remaining % 60;
            m = String(m).padStart(2, '0');
            s = String(s).padStart(2, '0');
            timerEl.textContent = `${m}:${s}`;
        }
    }
}

// 타이머 초기화 함수
function resetTimer() {
    if (timerRunning) {
        clearInterval(timerInterval);
        timerRunning = false;
        timerEndTime = null;
        
        const timerEl = document.getElementById('timer');
        if (timerEl) {
            timerEl.textContent = '00:00';
        }
        
        // 로컬 스토리지에서 타이머 상태 제거
        localStorage.removeItem('timerEndTime');
        localStorage.removeItem('lastTimer');
    }
}

// 타이머 상태 복원 함수
function restoreTimerState() {
    const storedEndTime = localStorage.getItem('timerEndTime');
    const storedLastTimer = localStorage.getItem('lastTimer');
    
    if (storedEndTime) {
        const endTime = parseInt(storedEndTime, 10);
        const now = Date.now();
        
        // 아직 종료되지 않은 타이머가 있는 경우 복원
        if (endTime > now) {
            const remainingMs = endTime - now;
            const remainingSec = Math.ceil(remainingMs / 1000);
            
            if (remainingSec > 0) {
                startTimer(remainingSec);
                return;
            }
        }
    }
    
    // 종료된 타이머가 있거나 저장된 상태가 없는 경우 초기화
    const timerEl = document.getElementById('timer');
    if (timerEl) {
        timerEl.textContent = '00:00';
    }
}

// 운동 상태 저장 함수
function saveExerciseState() {
    const exerciseStates = {};
    
    // 모든 세트 상태 수집
    document.querySelectorAll('.set-circle').forEach(set => {
        const exerciseName = set.getAttribute('data-ex');
        const setNumber = set.getAttribute('data-set');
        const state = set.getAttribute('data-state');
        
        if (!exerciseStates[exerciseName]) {
            exerciseStates[exerciseName] = {};
        }
        
        exerciseStates[exerciseName][setNumber] = state;
    });
    
    // 로컬 스토리지에 저장
    localStorage.setItem('exerciseStates', JSON.stringify(exerciseStates));
}

// 타이머 종료 알림음
function playTimerEndSound() {
    // 브라우저 알림 API 사용
    if ('Notification' in window && Notification.permission === "granted") {
        const notification = new Notification("휴식 시간 종료", {
            body: "다음 세트를 시작할 시간입니다!",
            icon: "/favicon.ico"
        });
        
        // 5초 후 알림 닫기
        setTimeout(() => notification.close(), 5000);
    }
    
    // 알림음 재생
    try {
        const audio = new Audio('data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA/+M4wAAAAAAAAAAAAEluZm8AAAAPAAAAAwAAAbAAkJCQkJCQkJCQkJCQkJCQwMDAwMDAwMDAwMDAwMDAwODg4ODg4ODg4ODg4ODg4OD///////////////////////////////////////////////8AAAAATGF2YzU4LjEzAAAAAAAAAAAAAAAAJAUHAAAAAAAAALDXGNI2AAAAAAAAAAAAAAAAAAAAAP/jYMQAEvgiwl9DAAAAO1ALSi19XgYC7u7u7vd+WDOT5CCTnBwcHEokDmv8vz6yz9YuXVJ1zolS9iwRFv8TeKDn/J2JdhQiaMwHjwII/jTOMlI8eZFxWHhwHBwcEf4J9nCPg4ODg4IuDg4OD/hP6Dg4OIEeREQTRMLBwcQQQQmcHBxAhP//jYMQ0HzDCdDsMGliwODiBAYeNfJBw8Hyj4IODg4v+EfBBwcQI7IeGdlAsHBxDxCsiHBwcOLvLg4ODi7jTyIctcAAIITOhP7UJUHBwcHCfwcHBwf4R8pysdJRDg4OIEcHBxAhwcHB3Qg4ODu7xAOOIEi4iHlDpQODg48ZUSCJ//5cDg4OL/hONzJK//jYMRGILDSYkwkYIhc6UDAEHdCBChHwn5QMTODg4ODg54lAHBwcHBBwcHBwQcHBwcEEcRDxohwcHDhKJ+Ig4OCA4R8HBwcXlwcHBwTDiXCLg4OScsiQGBBwcHBwnwODg4L/8sHBwdzI74KCPiXiHE4UdKDg4OEg4OCDg4OLu7o8SgkTOsXNu7u7uwA=');
        audio.volume = 0.5;
        audio.play()
        .catch(error => {
            console.log('알림음을 재생할 수 없습니다:', error);
        });
    } catch (error) {
        console.log('알림음을 재생할 수 없습니다:', error);
    }
    
    // 사용자에게 알림 표시
    alert('휴식 시간이 종료되었습니다!');
}

// CSS 스타일 추가
function addNotificationStyles() {
    const style = document.createElement('style');
    style.textContent = `
    .notification {
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: rgba(49, 130, 206, 0.9);
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        z-index: 1000;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
        transition: opacity 0.5s ease-out;
    }
    
    .notification.fadeout {
        opacity: 0;
    }
    
    .set-circle {
        cursor: pointer;
        transition: transform 0.2s ease;
    }
    
    .set-circle:hover {
        transform: scale(1.1);
    }
    `;
    
    document.head.appendChild(style);
}

// 스타일 추가
addNotificationStyles();