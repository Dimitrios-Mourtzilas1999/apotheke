// dashboard.js
document.addEventListener("DOMContentLoaded", () => {
  console.log("Dashboard initialized");

  // ===== CHART CONFIG HELPERS =====
  const defaultColors = [
    "#0d6efd", "#6610f2", "#6f42c1", "#20c997",
    "#198754", "#ffc107", "#dc3545", "#0dcaf0",
    "#fd7e14", "#adb5bd"
  ];

  /**
   * Initialize a chart safely
   * @param {string} id - Canvas element ID
   * @param {string} type - Chart type ('pie', 'doughnut', etc.)
   * @param {Object} dataObj - { labels: [...], values: [...] }
   * @param {Object} [options={}] - Optional Chart.js overrides
   */
  const initChart = (id, type, dataObj, options = {}) => {
    const canvas = document.getElementById(id);
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    const data = {
      labels: dataObj.labels,
      datasets: [
        {
          data: dataObj.values,
          backgroundColor: defaultColors.slice(0, dataObj.values.length),
          borderColor: "#1c1f26",
          borderWidth: 2,
          hoverOffset: 6
        }
      ]
    };

    const defaultOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            color: "#e6e9ef",
            font: { size: 13 }
          }
        },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.label}: ${ctx.formattedValue}`
          }
        }
      }
    };

    new Chart(ctx, {
      type,
      data,
      options: { ...defaultOptions, ...options }
    });
  };

  // ===== FETCH DATA FROM EMBEDDED JSON =====
  // These are injected by Flask: {{ category_data|tojson }} and {{ supplier_data|tojson }}
  const categoryData = window.categoryData || {};
  const supplierData = window.supplierData || {};

  // ===== INITIALIZE CHARTS =====
  initChart("categoryChart", "pie", categoryData);
  initChart("supplierChart", "doughnut", supplierData);

  // ===== OPTIONAL: ANIMATED COUNTERS =====
  const counters = document.querySelectorAll(".summary-card p");
  counters.forEach(counter => {
    const value = parseFloat(counter.textContent.replace(/[^\d.]/g, ""));
    if (isNaN(value)) return;

    let start = 0;
    const duration = 800; // in ms
    const increment = value / (duration / 16); // frame = ~16ms

    const animate = () => {
      start += increment;
      if (start >= value) {
        counter.textContent = value.toLocaleString();
        return;
      }
      counter.textContent = Math.floor(start).toLocaleString();
      requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  });
});
