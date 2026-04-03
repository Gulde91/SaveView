function formatCurrency(amount) {
  return amount.toLocaleString('da-DK', { style: 'currency', currency: 'DKK', maximumFractionDigits: 2 });
}

function formatAxisCurrency(amount) {
  return amount.toLocaleString('da-DK', { maximumFractionDigits: 0 });
}

function formatAxisDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('da-DK', { day: '2-digit', month: '2-digit' });
}

function parseISODate(dateStr) {
  return new Date(`${dateStr}T00:00:00`);
}

function getRangeStart(maxDateStr, rangeKey) {
  const end = parseISODate(maxDateStr);
  const start = new Date(end);
  if (rangeKey === 'week') start.setDate(start.getDate() - 7);
  if (rangeKey === 'month') start.setMonth(start.getMonth() - 1);
  if (rangeKey === 'quarter') start.setMonth(start.getMonth() - 3);
  return start;
}

function computeScale(canvas, allValues) {
  const padding = { top: 28, right: 14, bottom: 46, left: 62 };
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const yTicks = computeNiceTicks(min, max);
  const yMin = yTicks[0];
  const yMax = yTicks[yTicks.length - 1];

  return {
    padding,
    yMin,
    yMax,
    yTicks,
    toX(index, total) {
      const width = canvas.width - padding.left - padding.right;
      return padding.left + (index * width) / Math.max(total - 1, 1);
    },
    toY(value) {
      const height = canvas.height - padding.top - padding.bottom;
      return canvas.height - padding.bottom - ((value - yMin) * height) / Math.max(yMax - yMin, 1);
    }
  };
}

function computeNiceTicks(min, max, tickCount = 5) {
  if (min === max) {
    const base = Math.max(Math.abs(min), 1);
    const step = Math.pow(10, Math.floor(Math.log10(base)));
    const start = Math.floor((min - 2 * step) / step) * step;
    return Array.from({ length: tickCount }, (_, i) => start + i * step);
  }

  const range = max - min;
  const roughStep = range / Math.max(tickCount - 1, 1);
  const magnitude = Math.pow(10, Math.floor(Math.log10(roughStep)));
  const normalized = roughStep / magnitude;
  let niceNormalizedStep = 10;

  if (normalized <= 1) niceNormalizedStep = 1;
  else if (normalized <= 2) niceNormalizedStep = 2;
  else if (normalized <= 5) niceNormalizedStep = 5;

  const step = niceNormalizedStep * magnitude;
  const niceMin = Math.floor(min / step) * step;
  const niceMax = Math.ceil(max / step) * step;
  const count = Math.round((niceMax - niceMin) / step) + 1;

  return Array.from({ length: count }, (_, i) => niceMin + i * step);
}

function drawAxes(ctx, canvas, padding) {
  ctx.strokeStyle = '#d1d5db';
  ctx.lineWidth = 1;

  ctx.beginPath();
  ctx.moveTo(padding.left, padding.top);
  ctx.lineTo(padding.left, canvas.height - padding.bottom);
  ctx.lineTo(canvas.width - padding.right, canvas.height - padding.bottom);
  ctx.stroke();
}

function drawAxisLabels(ctx, canvas, padding, xLabel, yLabel) {
  ctx.fillStyle = '#6b7280';
  ctx.font = '12px Arial';
  ctx.textAlign = 'center';
  ctx.fillText(xLabel, (canvas.width + padding.left - padding.right) / 2, canvas.height - 10);

  if (yLabel) {
    ctx.save();
    ctx.translate(16, (canvas.height + padding.top - padding.bottom) / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'center';
    ctx.fillText(yLabel, 0, 0);
    ctx.restore();
  }
}

function drawTicks(ctx, canvas, scale, points) {
  const xTickCount = Math.min(4, points.length - 1);
  ctx.font = '11px Arial';

  for (const value of scale.yTicks) {
    const y = scale.toY(value);
    ctx.strokeStyle = '#eef2f7';
    ctx.beginPath();
    ctx.moveTo(scale.padding.left, y);
    ctx.lineTo(canvas.width - scale.padding.right, y);
    ctx.stroke();

    ctx.fillStyle = '#6b7280';
    ctx.textAlign = 'right';
    ctx.fillText(formatAxisCurrency(value), scale.padding.left - 6, y + 3);
  }

  for (let i = 0; i <= xTickCount; i += 1) {
    const pointIndex = Math.round((i * (points.length - 1)) / Math.max(xTickCount, 1));
    const point = points[pointIndex];
    const x = scale.toX(pointIndex, points.length);

    ctx.strokeStyle = '#eef2f7';
    ctx.beginPath();
    ctx.moveTo(x, scale.padding.top);
    ctx.lineTo(x, canvas.height - scale.padding.bottom);
    ctx.stroke();

    ctx.fillStyle = '#6b7280';
    ctx.textAlign = 'center';
    ctx.fillText(formatAxisDate(point.date), x, canvas.height - scale.padding.bottom + 16);
  }
}

function syncCanvasSize(canvas) {
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(1, Math.round(rect.width));
  const height = Math.max(1, Math.round(rect.height));

  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
}

function drawLineChart(canvasId, points, label, xLabel, yLabel, color = '#2563eb') {
  const canvas = document.getElementById(canvasId);
  syncCanvasSize(canvas);
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!points.length) {
    ctx.fillText('Ingen data', 20, 20);
    return;
  }

  const scale = computeScale(canvas, points.map((p) => p.value));
  drawAxes(ctx, canvas, scale.padding);
  drawTicks(ctx, canvas, scale, points);
  drawAxisLabels(ctx, canvas, scale.padding, xLabel, yLabel);

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
  ctx.font = '13px Arial';
  ctx.textAlign = 'left';
  ctx.fillText(label, scale.padding.left, 18);
}

function drawMultiLineChart(canvasId, seriesMap, xLabel, yLabel) {
  const colors = ['#2563eb', '#16a34a', '#e11d48', '#d97706', '#7c3aed'];
  const canvas = document.getElementById(canvasId);
  syncCanvasSize(canvas);
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const categories = Object.keys(seriesMap).filter((category) => seriesMap[category].length);
  if (!categories.length) {
    ctx.fillText('Ingen data', 20, 20);
    return [];
  }

  const allValues = categories.flatMap((category) => seriesMap[category].map((p) => p.værdi));
  const basePoints = seriesMap[categories[0]].map((p) => ({ date: p.dato }));
  const scale = computeScale(canvas, allValues);
  drawAxes(ctx, canvas, scale.padding);
  drawTicks(ctx, canvas, scale, basePoints);
  drawAxisLabels(ctx, canvas, scale.padding, xLabel, yLabel);

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

  return categories.map((category, idx) => ({
    category,
    color: colors[idx % colors.length]
  }));
}

function filterBalanceSeries(series, rangeKey) {
  if (!series.length) return [];
  const start = getRangeStart(series[series.length - 1].date, rangeKey);
  return series.filter((point) => parseISODate(point.date) >= start);
}

function filterCategorySeries(seriesMap, rangeKey) {
  const allSeries = Object.values(seriesMap);
  if (!allSeries.length) return {};

  let maxDate = null;
  allSeries.forEach((series) => {
    if (!series.length) return;
    const lastDate = series[series.length - 1].dato;
    if (!maxDate || lastDate > maxDate) {
      maxDate = lastDate;
    }
  });

  if (!maxDate) return {};
  const start = getRangeStart(maxDate, rangeKey);

  return Object.fromEntries(
    Object.entries(seriesMap).map(([category, series]) => [
      category,
      series.filter((point) => parseISODate(point.dato) >= start)
    ])
  );
}

function downsampleSeries(points, maxPoints = 500) {
  if (!points.length || points.length <= maxPoints) {
    return points;
  }

  const step = (points.length - 1) / (maxPoints - 1);
  const sampled = [];
  for (let i = 0; i < maxPoints; i += 1) {
    const index = Math.round(i * step);
    sampled.push(points[index]);
  }
  return sampled;
}

function downsampleCategorySeries(seriesMap, maxPoints = 500) {
  return Object.fromEntries(
    Object.entries(seriesMap).map(([category, series]) => [category, downsampleSeries(series, maxPoints)])
  );
}

async function fetchDashboardData() {
  const endpoints = ['/api/dashboard', '/api/data'];
  let lastError = null;

  for (const endpoint of endpoints) {
    try {
      const response = await fetch(endpoint);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      lastError = error;
    }
  }

  throw new Error(`Kunne ikke hente dashboard-data (${lastError})`);
}

function activateRangeButton(activeValue) {
  document.querySelectorAll('[data-range]').forEach((button) => {
    button.classList.toggle('active', button.dataset.range === activeValue);
  });
}

function updateCategoryLegend(items) {
  const legend = document.getElementById('categoryLegend');
  legend.innerHTML = '';
  items.forEach((item) => {
    const chip = document.createElement('span');
    chip.className = 'legend-item';
    chip.innerHTML = `<span class="legend-dot" style="background:${item.color}"></span>${item.category}`;
    legend.appendChild(chip);
  });
}

function setLoadingStep(text) {
  const status = document.getElementById('loadingStatus');
  if (status) {
    status.textContent = text;
  }
}

function hideLoadingOverlay() {
  const overlay = document.getElementById('loadingOverlay');
  if (overlay) {
    overlay.classList.add('hidden');
    overlay.setAttribute('aria-hidden', 'true');
  }
}

function nextPaint() {
  return new Promise((resolve) => {
    requestAnimationFrame(() => setTimeout(resolve, 0));
  });
}

async function loadDashboard() {
  setLoadingStep('Loader data fra Dropbox/lokal mappe …');
  await nextPaint();
  const data = await fetchDashboardData();

  if (data.fejl) {
    document.body.innerHTML = `<p>Fejl: ${data.fejl}</p>`;
    return;
  }

  setLoadingStep('Behandler data …');
  await nextPaint();


  const warningBox = document.getElementById('warningBox');
  if (data.ugyldigeFiler.length) {
    warningBox.classList.remove('hidden');
    warningBox.innerHTML = `<strong>Advarsel:</strong> Følgende filnavne matcher ikke mønsteret og bør kontrolleres:<br>${data.ugyldigeFiler.join('<br>')}`;
  }

  const list = document.getElementById('categoryList');
  list.innerHTML = '';
  document.getElementById('totalBalance').textContent = `Total saldo: ${formatCurrency(data.totalSaldo ?? 0)}`;
  data.opsparingPrKategori.forEach((entry) => {
    const li = document.createElement('li');
    li.innerHTML = `<span>${entry.kategori}</span><strong>${formatCurrency(entry.beløb)}</strong>`;
    list.appendChild(li);
  });

  const fullBalanceSeries = data.saldoUdvikling.map((p) => ({ date: p.dato, value: p.saldo }));
  const fullCategorySeries = data.kategoriUdvikling;

  const renderCharts = (rangeKey) => {
    const filteredBalance = downsampleSeries(filterBalanceSeries(fullBalanceSeries, rangeKey));
    const filteredCategories = downsampleCategorySeries(filterCategorySeries(fullCategorySeries, rangeKey));
    drawLineChart('saldoCanvas', filteredBalance, 'Saldo over tid', 'Dato', '');
    const legendItems = drawMultiLineChart('categoryCanvas', filteredCategories, 'Dato', '');
    updateCategoryLegend(legendItems);
    activateRangeButton(rangeKey);
  };

  document.querySelectorAll('[data-range]').forEach((button) => {
    button.addEventListener('click', () => renderCharts(button.dataset.range));
  });

  setLoadingStep('Konstruerer plots …');
  await nextPaint();
  renderCharts('month');
  hideLoadingOverlay();
}

loadDashboard().catch((error) => {
  document.body.innerHTML = `<p>Fejl: ${error.message}</p>`;
});
