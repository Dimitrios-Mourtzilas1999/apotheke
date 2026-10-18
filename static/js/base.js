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

  // Mobile menu toggle
  const mobileMenuToggle = document.getElementById('mobileMenuToggle');
  const mobileCloseBtn = document.getElementById('mobileCloseBtn');
  const sidebarOverlay = document.getElementById('sidebarOverlay');
  const sidebarMenu = document.getElementById('sidebarMenu');
  const body = document.body;

  function openMenu() {
    body.classList.add('sidebar-open');
    body.classList.remove('sidebar-closed');
  }

  function closeMenu() {
    body.classList.remove('sidebar-open');
    body.classList.add('sidebar-closed');
  }

  if (mobileMenuToggle) {
    mobileMenuToggle.addEventListener('click', openMenu);
  }

  if (mobileCloseBtn) {
    mobileCloseBtn.addEventListener('click', closeMenu);
  }

  if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', closeMenu);
  }

  // Close menu when clicking a link (for better UX)
  const sidebarLinks = document.querySelectorAll('.sidebar__btn');
  sidebarLinks.forEach(link => {
    link.addEventListener('click', closeMenu);
  });

  // Initialize as closed on mobile
  if (window.innerWidth <= 768) {
    body.classList.add('sidebar-closed');
  }
});
