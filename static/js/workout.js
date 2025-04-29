document.addEventListener('DOMContentLoaded', () => {
  let timerInterval;

  function startTimer(seconds, label) {
    clearInterval(timerInterval);
    const display = document.getElementById('timer-count');
    const timerBox = document.getElementById('timer');
    document.getElementById('timer-label').textContent = label;
    timerBox.style.display = 'block';

    let remaining = seconds;
    function update() {
      const m = String(Math.floor(remaining / 60)).padStart(2, '0');
      const s = String(remaining % 60).padStart(2, '0');
      display.textContent = `${m}:${s}`;
      if (remaining-- <= 0) {
        clearInterval(timerInterval);
        document.getElementById('alarm').play();
        setTimeout(() => { timerBox.style.display = 'none'; }, 1000);
      }
    }
    update();
    timerInterval = setInterval(update, 1000);
  }

  document.querySelectorAll('.circle').forEach(circle => {
    circle.addEventListener('click', () => {
      let clicks = parseInt(circle.dataset.clicks) + 1;
      if (clicks >= 3) {
        circle.dataset.clicks = 0;
        circle.classList.remove('complete', 'fail');
        clearInterval(timerInterval);
        document.getElementById('timer').style.display = 'none';
      } else {
        circle.dataset.clicks = clicks;
        if (clicks === 1) {
          circle.classList.add('complete');
          startTimer(60, '휴식 (1분)');
        } else if (clicks === 2) {
          circle.classList.remove('complete');
          circle.classList.add('fail');
          startTimer(90, '휴식 (1분 30초)');
        }
      }
    });
  });

  const completeBtn = document.getElementById('complete-btn');
  if (completeBtn) {
    completeBtn.addEventListener('click', () => {
      const details = Array.from(document.querySelectorAll('.exercise')).map(ex => {
        const title = ex.querySelector('h3').textContent;
        const name = title.split(' (')[0].trim();
        const total_sets = ex.dataset.sets;
        const weight = parseFloat(ex.dataset.weight) || 0;
        const circles = ex.querySelectorAll('.circle');
        const success = Array.from(circles).filter(c => c.dataset.clicks==='1').length;
        const fail    = Array.from(circles).filter(c => c.dataset.clicks==='2').length;
        return { name, total_sets, success, fail, weight };
      });

      const routineName = document.querySelector('h2').textContent.split(' ')[0].toLowerCase();
      fetch('/record', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ routine: routineName, details })
      })
      .then(res => res.json())
      .then(res => {
        if (res.status === 'ok') {
          alert('오늘 운동이 기록되었습니다!');
          window.location.href = `/trend/${routineName}`;
        }
      });
    });
  }
});
