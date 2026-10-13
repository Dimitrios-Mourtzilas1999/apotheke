// Adds Django's CSRF header to every non-GET fetch() so the existing JSON
// fetch calls (products.js, category_info.js, ...) keep working unchanged.
(function () {
  const meta = document.querySelector('meta[name="csrf-token"]');
  const token = meta ? meta.content : "";
  const original = window.fetch;
  window.fetch = function (input, init) {
    init = init || {};
    const method = (init.method || "GET").toUpperCase();
    if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
      const headers = new Headers(init.headers || {});
      if (!headers.has("X-CSRFToken")) headers.set("X-CSRFToken", token);
      init = Object.assign({}, init, { headers });
    }
    return original.call(this, input, init);
  };
})();
