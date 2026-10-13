document.addEventListener("DOMContentLoaded", () => {
    const alerts = document.querySelectorAll(".flashes .alert");

    alerts.forEach(alert => {
        // Auto-hide after 4 seconds (4000ms)
        setTimeout(() => {
            alert.classList.add("fade-out");

            // Remove from DOM after animation completes (500ms)
            setTimeout(() => alert.remove(), 500);
        }, 4000);
    });
});
