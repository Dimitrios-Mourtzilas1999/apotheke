document.addEventListener("DOMContentLoaded", () => {
  const flashes = document.querySelectorAll(".flash-message");

  flashes.forEach((flash, index) => {
    // Stagger animations slightly
    flash.style.animationDelay = `${index * 100}ms`;

    // Auto-dismiss after 4 seconds
    const timeout = setTimeout(() => {
      closeFlash(flash);
    }, 2000);

    // Cancel auto-dismiss if user hovers
    flash.addEventListener("mouseenter", () => {
      clearTimeout(timeout);
    });
  });

  function closeFlash(flash) {
    flash.classList.remove("show");
    flash.classList.add("fade");

    // Remove from DOM after animation
    setTimeout(() => {
      flash.remove();
    }, 300);
  }
});
