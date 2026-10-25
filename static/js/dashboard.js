// dashboard.js
document.addEventListener("DOMContentLoaded", () => {
  const readJson = (id) => {
    const el = document.getElementById(id);
    return el ? JSON.parse(el.textContent) : { labels: [], values: [] };
  };

  const euro = new Intl.NumberFormat("el-GR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
  const euroCompact = new Intl.NumberFormat("el-GR", { style: "currency", currency: "EUR", notation: "compact" });
  const number = new Intl.NumberFormat("el-GR");
  const textColor = "#e6e9ef";
  const gridColor = "rgba(255, 255, 255, 0.08)";

  const showEmpty = (canvas, message) => {
    const p = document.createElement("p");
    p.className = "chart-empty";
    p.textContent = message;
    canvas.parentElement.replaceWith(p);
  };

  const initStatusChart = (id, dataObj) => {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    const total = dataObj.values.reduce((a, b) => a + b, 0);
    if (!total) return showEmpty(canvas, "Δεν υπάρχουν προϊόντα.");

    new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: dataObj.labels,
        datasets: [{
          data: dataObj.values,
          backgroundColor: ["#22c55e", "#eab308", "#ef4444"],
          borderColor: "#1c1f26",
          borderWidth: 2,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "60%",
        plugins: {
          legend: { position: "bottom", labels: { color: textColor, font: { size: 13 } } },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.label}: ${number.format(ctx.parsed)} (${Math.round((ctx.parsed / total) * 100)}%)`
            }
          }
        }
      }
    });
  };

  // Horizontal bars sorted by value: easier to compare than pie slices once there are more than a few groups.
  const initValueBarChart = (id, dataObj, color) => {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    if (!dataObj.labels.length) return showEmpty(canvas, "Δεν υπάρχουν δεδομένα.");

    new Chart(canvas, {
      type: "bar",
      data: {
        labels: dataObj.labels,
        datasets: [{ data: dataObj.values, backgroundColor: color, borderRadius: 6, maxBarThickness: 28 }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => euro.format(ctx.parsed.x),
              afterLabel: (ctx) => `${number.format(dataObj.counts[ctx.dataIndex])} προϊόντα`
            }
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            ticks: { color: textColor, maxTicksLimit: 6, maxRotation: 0, callback: (v) => euroCompact.format(v) },
            grid: { color: gridColor }
          },
          y: { ticks: { color: textColor }, grid: { display: false } }
        }
      }
    });
  };

  initStatusChart("stockStatusChart", readJson("stock-status-data"));
  initValueBarChart("categoryChart", readJson("category-data"), "#0d6efd");
  initValueBarChart("supplierChart", readJson("supplier-data"), "#20c997");

  // ===== ANIMATED COUNTERS =====
  document.querySelectorAll(".summary-card p[data-count]").forEach((counter) => {
    const value = Number(counter.dataset.count);
    const suffix = counter.dataset.suffix || "";
    if (!Number.isFinite(value)) return;

    const duration = 800;
    const startTime = performance.now();
    const step = (now) => {
      const progress = Math.min((now - startTime) / duration, 1);
      counter.textContent = number.format(Math.round(value * progress)) + suffix;
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  });
});
