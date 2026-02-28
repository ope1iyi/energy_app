/* ── main.js — Energy Analytics Dashboard ─────────────────── */

document.addEventListener('DOMContentLoaded', () => {

  /* 1. File input — update label text on selection
     The label[for="file"] click is handled natively by the browser.
     We only update its text content after a file is chosen.
  ─────────────────────────────────────────────── */
  const fileInput = document.getElementById('file');
  const fileLabel = document.querySelector('label[for="file"]');

  if (fileInput && fileLabel) {
    // Set initial label content — keep it as a plain text node, never innerHTML
    // so we never risk destroying the input element or its form association.
    fileLabel.textContent = '📂 Choose .xls / .xlsx';

    // On file selected: update label text and highlight it
    fileInput.addEventListener('change', () => {
      const name = fileInput.files[0]?.name || '📂 Choose .xls / .xlsx';
      fileLabel.textContent = '📄 ' + name;
      fileLabel.classList.add('file-selected');
    });
  }


  /* 2. Loading overlay on form submit
  ─────────────────────────────────────────────── */
  const form = document.querySelector('.navbar-form');
  if (form) {
    // Inject overlay
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
      <div class="spinner"></div>
      <div class="loading-text">PROCESSING DATA…</div>
    `;
    document.body.appendChild(overlay);

    form.addEventListener('submit', (e) => {
      const hasFile = fileInput && fileInput.files.length > 0;
      if (hasFile) {
        overlay.classList.add('active');
      }
    });
  }


  /* 3. Auto-dismiss flash messages
  ─────────────────────────────────────────────── */
  function wrapFlashMessages() {
    // Flask with_categories flash uses <ul class="flashes">
    const flashes = document.querySelectorAll('.flash, .flashes li');
    flashes.forEach((el, i) => {
      setTimeout(() => {
        el.style.transition = 'opacity 0.4s, transform 0.4s';
        el.style.opacity = '0';
        el.style.transform = 'translateX(30px)';
        setTimeout(() => el.remove(), 400);
      }, 4000 + i * 500);
    });
  }
  wrapFlashMessages();


  /* 4. Wrap all tables in .table-responsive
  ─────────────────────────────────────────────── */
  document.querySelectorAll('table').forEach(table => {
    if (!table.parentElement.classList.contains('table-responsive')) {
      const wrapper = document.createElement('div');
      wrapper.className = 'table-responsive';
      table.parentNode.insertBefore(wrapper, table);
      wrapper.appendChild(table);
    }
  });


  /* 5. Parse overview paragraph → stat cards
  ─────────────────────────────────────────────── */
  const overviewDiv = document.querySelector('.overview');
  if (overviewDiv && overviewDiv.innerHTML.trim()) {
    const rawHTML = overviewDiv.innerHTML;

    // Extract key values from the generated <p> tags
    const stats = [];
    // Patterns handle both old format <b>Label: value unit</b>
    // and new format <b>Label:</b> value unit (value outside bold tag)
    const daysMatch   = rawHTML.match(/for <b>(\d+ days[^<]*)<\/b>/);
    const avgMatch    = rawHTML.match(/Average power(?:<\/b>)?:?(?:<\/b>)?\s*([\d.]+)\s*kW/);
    const peakMatch   = rawHTML.match(/Peak power(?:<\/b>)?:?(?:<\/b>)?\s*([\d.]+)\s*kW/);
    const energyMatch = rawHTML.match(/Total energy[^:]*:(?:<\/b>)?\s*([\d.]+)\s*kWh/);
    const pfMatch     = rawHTML.match(/Trimmed Power Factor(?:<\/b>)?:?(?:<\/b>)?[^>]*?>\s*([\d.]+)/);

    if (daysMatch)   stats.push({ label: 'Duration',       value: daysMatch[1],   unit: '' });
    if (avgMatch)    stats.push({ label: 'Avg Power',      value: avgMatch[1],    unit: 'kW' });
    if (peakMatch)   stats.push({ label: 'Peak Power',     value: peakMatch[1],   unit: 'kW' });
    if (energyMatch) stats.push({ label: 'Total Energy',   value: energyMatch[1], unit: 'kWh' });
    if (pfMatch)     stats.push({ label: 'Power Factor',   value: pfMatch[1],     unit: '' });

    if (stats.length) {
      // Build stat cards
      let html = `<div class="card" style="padding:20px 28px">
        <div class="card-title">Overview</div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;">`;

      stats.forEach(s => {
        html += `
          <div class="stat-card">
            <div class="stat-label">${s.label}</div>
            <div class="stat-value">${s.value} ${s.unit ? `<span>${s.unit}</span>` : ''}</div>
          </div>`;
      });

      html += '</div></div>';

      // Also keep the original text below in a card
      const origCard = document.createElement('div');
      origCard.className = 'card';
      origCard.style.cssText = 'display:none';
      origCard.innerHTML = rawHTML;

      overviewDiv.innerHTML = html;
      overviewDiv.appendChild(origCard);
    }
  }


  /* 6. Wrap result sections in cards
  ─────────────────────────────────────────────── */
  const sections = [
    { sel: '.head-table',   icon: '📋' },
    { sel: '.energy-table', icon: '⚡' },
    { sel: '.night-table',  icon: '🌙' },
  ];

  sections.forEach(({ sel, icon }) => {
    const el = document.querySelector(sel);
    if (el && el.innerHTML.trim()) {
      el.classList.add('card');
      const firstH3 = el.querySelector('h3');
      if (firstH3) {
        firstH3.innerHTML = `${icon} ${firstH3.textContent}`;
      }
    }
  });


  /* 7. Wrap everything in .page-content if not already
  ─────────────────────────────────────────────── */
  const body = document.body;
  const navEl = document.querySelector('nav');
  if (navEl && !document.querySelector('.page-content')) {
    const children = Array.from(body.children).filter(c => c !== navEl && !c.classList.contains('loading-overlay') && !c.classList.contains('flash-messages'));
    const wrapper = document.createElement('div');
    wrapper.className = 'page-content';
    children.forEach(c => wrapper.appendChild(c));
    body.appendChild(wrapper);
  }


  /* 8. Number formatting in tables
  ─────────────────────────────────────────────── */
  document.querySelectorAll('table td').forEach(td => {
    const val = parseFloat(td.textContent);
    if (!isNaN(val) && td.textContent.trim() === String(val)) {
      td.textContent = val.toLocaleString(undefined, { maximumFractionDigits: 3 });
    }
  });

});