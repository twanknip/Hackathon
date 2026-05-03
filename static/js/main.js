document.addEventListener('DOMContentLoaded', function () {

 
  const flashContainer = document.getElementById('flash-container');
  if (flashContainer) {
    setTimeout(function () {
      const flashes = flashContainer.querySelectorAll('.flash');
      flashes.forEach(function (flash) {
        flash.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
        flash.style.opacity    = '0';
        flash.style.transform  = 'translateX(30px)';
        setTimeout(function () { flash.remove(); }, 400);
      });
    }, 5000); 
  }



  const statValues = document.querySelectorAll('.stat-value');
  statValues.forEach(function (el) {
    const text = el.textContent.trim();
    const num  = parseInt(text, 10);

    if (!isNaN(num) && num > 0) {
      animateCounter(el, num);
    }
  });

  function animateCounter(element, target) {
    const duration = 800;       
    const steps    = 30;        
    const interval = duration / steps;
    let   current  = 0;

    const timer = setInterval(function () {
      current += target / steps;
      if (current >= target) {
        current = target;
        clearInterval(timer);
      }
      element.textContent = Math.floor(current);
    }, interval);
  }


  const clickableRows = document.querySelectorAll('tr[data-href]');
  clickableRows.forEach(function (row) {
    row.style.cursor = 'pointer';
    row.addEventListener('click', function () {
      window.location.href = row.getAttribute('data-href');
    });
  });


  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {
      const searchInput = document.querySelector('input[name="q"]');
      if (searchInput) {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
      }
    }
  });

  const clockEl = document.getElementById('live-clock');
  if (clockEl) {
    function updateClock() {
      const now = new Date();
      clockEl.textContent = now.toLocaleTimeString('en-GB', {
        hour:   '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    }
    updateClock();
    setInterval(updateClock, 1000);
  }

  console.log(
    '%c MediFile Systems v1.0 ',
    'background: #00c8ff; color: #050b14; font-weight: bold; padding: 4px 8px; border-radius: 4px;'
  );
  console.log('%c All activity is logged for security auditing.', 'color: #7a9bbf;');

});