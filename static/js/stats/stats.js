document.addEventListener('DOMContentLoaded', () => {
  const page = document.querySelector('.stats-page[data-chart-url]');
  if (!page) return;

  const status = page.querySelector('[data-chart-status]');
  const error = page.querySelector('[data-chart-error]');
  const content = page.querySelector('[data-chart-content]');
  const buttons = Array.from(page.querySelectorAll('[data-range]'));
  const retry = page.querySelector('[data-chart-retry]');
  let selectedRange = '7';
  let sugarChart;
  let calorieChart;

  const setSummary = (data) => {
    const summary = data.summary;
    page.querySelector('[data-summary="average-sugar"]').textContent =
      `${summary.average_sugar_g.toFixed(1)}g`;
    page.querySelector('[data-summary="average-calories"]').textContent =
      `${summary.average_calories.toFixed(0)} kcal`;
    page.querySelector('[data-summary="total-entries"]').textContent =
      summary.total_entries.toString();

    if (summary.highest_sugar_day) {
      page.querySelector('[data-summary="highest-sugar"]').textContent =
        `${summary.highest_sugar_day.sugar_g.toFixed(1)}g`;
      page.querySelector('[data-summary="highest-sugar-date"]').textContent =
        new Date(`${summary.highest_sugar_day.date}T00:00:00`).toLocaleDateString(
          undefined,
          { month: 'short', day: 'numeric' },
        );
    } else {
      page.querySelector('[data-summary="highest-sugar"]').textContent = '—';
      page.querySelector('[data-summary="highest-sugar-date"]').textContent =
        'No logged days';
    }

    const overLimit = page.querySelector('[data-summary="days-over-limit"]');
    const limitCaption = page.querySelector('[data-summary="limit-caption"]');
    if (summary.days_over_limit === null) {
      overLimit.textContent = '—';
      limitCaption.textContent = 'Set a daily sugar limit to track this';
    } else {
      overLimit.textContent = summary.days_over_limit.toString();
      limitCaption.textContent = 'Days above your daily sugar limit';
    }
  };

  const buildCharts = (data) => {
    if (typeof window.Chart !== 'function') {
      throw new Error('Chart.js is unavailable.');
    }
    const labels = data.dates.map((date) =>
      new Date(`${date}T00:00:00`).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
      }),
    );
    const sugarDatasets = [{
      label: 'Sugar intake',
      data: data.daily_sugar,
      backgroundColor: 'rgba(20, 92, 84, 0.72)',
      borderRadius: 6,
      maxBarThickness: 26,
    }];
    if (data.sugar_limit_g !== null) {
      sugarDatasets.push({
        type: 'line',
        label: `Daily limit (${data.sugar_limit_g}g)`,
        data: labels.map(() => data.sugar_limit_g),
        borderColor: '#c98a22',
        borderDash: [6, 5],
        borderWidth: 2,
        pointRadius: 0,
        pointHitRadius: 8,
      });
    }
    const commonOptions = {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      plugins: {
        legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } },
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true } },
        y: { beginAtZero: true, grid: { color: 'rgba(22, 33, 29, 0.08)' } },
      },
    };

    if (sugarChart) sugarChart.destroy();
    if (calorieChart) calorieChart.destroy();
    sugarChart = new window.Chart(page.querySelector('[data-sugar-chart]'), {
      type: 'bar',
      data: { labels, datasets: sugarDatasets },
      options: commonOptions,
    });
    calorieChart = new window.Chart(page.querySelector('[data-calorie-chart]'), {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Calories',
          data: data.daily_calories,
          backgroundColor: 'rgba(226, 166, 59, 0.78)',
          borderRadius: 6,
          maxBarThickness: 26,
        }],
      },
      options: commonOptions,
    });
  };

  const loadData = async () => {
    status.hidden = false;
    status.textContent = 'Loading your trends…';
    error.hidden = true;
    content.hidden = true;
    buttons.forEach((button) => {
      button.disabled = true;
    });
    try {
      const url = new URL(page.dataset.chartUrl, window.location.origin);
      url.searchParams.set('range', selectedRange);
      const response = await fetch(url, {
        headers: { Accept: 'application/json' },
        credentials: 'same-origin',
      });
      if (!response.ok) throw new Error(`Statistics request failed: ${response.status}`);
      const data = await response.json();
      setSummary(data);
      buildCharts(data);
      content.hidden = false;
      status.hidden = true;
    } catch (requestError) {
      status.hidden = true;
      error.hidden = false;
    } finally {
      buttons.forEach((button) => {
        button.disabled = false;
      });
    }
  };

  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      selectedRange = button.dataset.range;
      buttons.forEach((item) => {
        const active = item === button;
        item.classList.toggle('is-active', active);
        item.setAttribute('aria-pressed', active.toString());
      });
      loadData();
    });
  });
  retry.addEventListener('click', loadData);
  loadData();
});
