/**
 * charts.js
 * ApexCharts konfiqurasiyası — sparkline, analitika xətti, radial skor
 * index.html-dəki #spark-*, #chart-analytics, #chart-score elementlərinə bağlanır
 */

(function () {
  'use strict';

  /** ApexCharts yüklənməyibsə — dayandır */
  if (typeof ApexCharts === 'undefined') {
    console.warn('ApexCharts tapılmadı. CDN yoxlayın.');
    return;
  }

  /* ---------- Ortak dark tema ---------- */
  var chartBg = 'transparent';
  var gridColor = '#1E2533';
  var labelColor = '#8B95A8';

  /**
   * Kiçik sparkline — stat kartlarının altında
   * @param {string} elId - DOM element id
   * @param {number[]} data - seriya
   * @param {string} color - xətt rəngi
   */
  function makeSparkline(elId, data, color) {
    var el = document.querySelector(elId);
    if (!el) return;

    var chart = new ApexCharts(el, {
      series: [{ data: data }],
      chart: {
        type: 'area',
        height: 36,
        sparkline: { enabled: true },
        background: chartBg,
        animations: { enabled: true, speed: 700 },
      },
      stroke: { curve: 'smooth', width: 2 },
      fill: {
        type: 'gradient',
        gradient: {
          shadeIntensity: 1,
          opacityFrom: 0.35,
          opacityTo: 0.02,
          stops: [0, 100],
        },
      },
      colors: [color],
      tooltip: { enabled: false },
    });
    chart.render();
  }

  /* --- 4 sparkline --- */
  makeSparkline('#spark-products', [12, 18, 14, 22, 19, 28, 24, 32, 30, 36], '#A78BFA');
  makeSparkline('#spark-orders', [8, 14, 11, 16, 20, 18, 24, 22, 28, 26], '#22D3EE');
  makeSparkline('#spark-stock', [30, 28, 26, 24, 22, 20, 18, 16, 14, 12], '#34D399');
  makeSparkline('#spark-delivery', [10, 12, 11, 15, 14, 18, 17, 20, 19, 22], '#60A5FA');

  /* ---------- Analitika — böyük xətt qrafiki ---------- */
  var analyticsEl = document.querySelector('#chart-analytics');
  if (analyticsEl) {
    var analyticsChart = new ApexCharts(analyticsEl, {
      series: [
        {
          name: 'Giriş',
          data: [12, 15, 14, 18, 22, 20, 25.5, 24, 28, 26, 30, 29],
        },
        {
          name: 'Çıxış',
          data: [8, 10, 12, 11, 14, 16, 15, 18, 17, 20, 19, 22],
        },
      ],
      chart: {
        type: 'area',
        height: 280,
        background: chartBg,
        toolbar: { show: false },
        zoom: { enabled: false },
        fontFamily: 'Inter, system-ui, sans-serif',
      },
      colors: ['#22D3EE', '#A78BFA'],
      dataLabels: { enabled: false },
      stroke: { curve: 'smooth', width: 2.5 },
      fill: {
        type: 'gradient',
        gradient: {
          shadeIntensity: 1,
          opacityFrom: 0.4,
          opacityTo: 0.02,
          stops: [0, 90, 100],
        },
      },
      grid: {
        borderColor: gridColor,
        strokeDashArray: 4,
        padding: { left: 8, right: 8 },
      },
      xaxis: {
        categories: [
          'May 1', 'May 5', 'May 10', 'May 15', 'May 18', 'May 20',
          'May 22', 'May 24', 'May 26', 'May 28', 'May 30', 'Jun 1',
        ],
        labels: { style: { colors: labelColor, fontSize: '11px' } },
        axisBorder: { show: false },
        axisTicks: { show: false },
      },
      yaxis: {
        labels: {
          style: { colors: labelColor, fontSize: '11px' },
          formatter: function (v) { return v + 'K'; },
        },
      },
      legend: { show: false },
      tooltip: {
        theme: 'dark',
        y: { formatter: function (v) { return v + 'K vahid'; } },
        style: { fontSize: '12px' },
      },
      markers: {
        size: 0,
        hover: { size: 5 },
      },
    });
    analyticsChart.render();
  }

  /* ---------- Radial skor — Anbar Skoru ---------- */
  var scoreEl = document.querySelector('#chart-score');
  if (scoreEl) {
    var scoreChart = new ApexCharts(scoreEl, {
      series: [92],
      chart: {
        type: 'radialBar',
        height: 200,
        background: chartBg,
      },
      plotOptions: {
        radialBar: {
          startAngle: -135,
          endAngle: 135,
          hollow: { size: '65%' },
          track: {
            background: '#1E2533',
            strokeWidth: '100%',
          },
          dataLabels: {
            name: {
              show: true,
              fontSize: '12px',
              color: '#34D399',
              offsetY: 24,
            },
            value: {
              show: true,
              fontSize: '32px',
              fontWeight: 700,
              color: '#FFFFFF',
              offsetY: -10,
              formatter: function (v) { return v; },
            },
          },
        },
      },
      fill: {
        type: 'gradient',
        gradient: {
          shade: 'dark',
          type: 'horizontal',
          gradientToColors: ['#22D3EE'],
          stops: [0, 100],
        },
      },
      stroke: { lineCap: 'round' },
      colors: ['#34D399'],
      labels: ['Əla'],
    });
    scoreChart.render();
  }
})();
