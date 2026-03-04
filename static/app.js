function formatCurrency(amount) {
  return amount.toLocaleString('da-DK', { style: 'currency', currency: 'DKK', maximumFractionDigits: 2 });
}

function computeScale(canvas, allValues) {
  const padding = 36;
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const range = max - min || 1;

  return {
    padding,
    toX(index, total) {
      return padding + (index * (canvas.width - 2 * padding)) / Math.max(total - 1, 1);
    },
    toY(value) {
      return canvas.height - padding - ((value - min) * (canvas.height - 2 * padding)) / range;
    }
  };
}

function drawAxes(ctx, canvas, padding) {
  ctx.strokeStyle = '#d1d5db';
  ctx.beginPath();
  ctx.moveTo(padding, canvas.height - padding);
  ctx.lineTo(canvas.width - padding, canvas.height - padding);
  ctx.stroke();
}

function drawLineChart(canvasId, points, label, color = '#2563eb') {
  const canvas = document.getElementById(canvasId);
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!points.length) {
    ctx.fillText('Ingen data', 20, 20);
    return;
  }

  const scale = computeScale(canvas, points.map((p) => p.value));
  drawAxes(ctx, canvas, scale.padding);

  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.beginPath();
  points.forEach((p, index) => {
    const x = scale.toX(index, points.length);
    const y = scale.toY(p.value);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.fillStyle = '#374151';
  ctx.fillText(label, scale.padding, 18);
}

function drawMultiLineChart(canvasId, seriesMap) {
  const colors = ['#2563eb', '#16a34a', '#e11d48', '#d97706', '#7c3aed'];
  const canvas = document.getElementById(canvasId);
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const categories = Object.keys(seriesMap);
  if (!categories.length) {
    ctx.fillText('Ingen data', 20, 20);
    return;
  }

  const allValues = categories.flatMap((category) => seriesMap[category].map((p) => p.værdi));
  const scale = computeScale(canvas, allValues);
  drawAxes(ctx, canvas, scale.padding);

  categories.forEach((category, idx) => {
    const points = seriesMap[category];
    ctx.strokeStyle = colors[idx % colors.length];
    ctx.lineWidth = 2;
    ctx.beginPath();
    points.forEach((p, index) => {
      const x = scale.toX(index, points.length);
      const y = scale.toY(p.værdi);
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  });

  let legendY = 18;
  categories.forEach((category, idx) => {
    ctx.fillStyle = colors[idx % colors.length];
    ctx.fillRect(16, legendY - 8, 10, 10);
    ctx.fillStyle = '#111827';
    ctx.fillText(category, 32, legendY);
    legendY += 16;
  });
}

async function fetchDashboardData() {
  const endpoints = ['/api/dashboard', '/api/data'];
  let lastError = null;

  for (const endpoint of endpoints) {
    try {
      const response = await fetch(endpoint);
      let body = null;
      try {
        body = await response.json();
      } catch (_error) {
        body = null;
      }

      if (!response.ok) {
        const serverError = body && body.fejl ? `: ${body.fejl}` : '';
        throw new Error(`HTTP ${response.status}${serverError}`);
      }

      return body || {};
    } catch (error) {
      lastError = error;
    }
  }

  throw new Error(`Kunne ikke hente dashboard-data (${lastError})`);
}

async function loadDashboard() {
  const data = await fetchDashboardData();

  if (data.fejl) {
    document.body.innerHTML = `<p>Fejl: ${data.fejl}</p>`;
    return;
  }

  document.getElementById('sourceLabel').textContent = `Datakilde: ${data.datakilde}`;

  const warningBox = document.getElementById('warningBox');
  const warnings = [];
  if (data.ugyldigeFiler.length) {
    warnings.push(`Følgende filnavne matcher ikke mønsteret og bør kontrolleres:<br>${data.ugyldigeFiler.join('<br>')}`);
  }
  if (data.ulæseligeFiler && data.ulæseligeFiler.length) {
    warnings.push(`Følgende filer kunne ikke læses og blev sprunget over:<br>${data.ulæseligeFiler.join('<br>')}`);
  }

  if (warnings.length) {
    warningBox.classList.remove('hidden');
    warningBox.innerHTML = `<strong>Advarsel:</strong><br>${warnings.join('<br><br>')}`;
  }

  const list = document.getElementById('categoryList');
  list.innerHTML = '';
  data.opsparingPrKategori.forEach((entry) => {
    const li = document.createElement('li');
    li.innerHTML = `<span>${entry.kategori}</span><strong>${formatCurrency(entry.beløb)}</strong>`;
    list.appendChild(li);
  });

  const balanceSeries = data.saldoUdvikling.map((p) => ({ date: p.dato, value: p.saldo }));
  drawLineChart('saldoCanvas', balanceSeries, 'Saldo over tid');
  drawMultiLineChart('categoryCanvas', data.kategoriUdvikling);
}

loadDashboard().catch((error) => {
  document.body.innerHTML = `<p>Fejl: ${error.message}</p>`;
});
