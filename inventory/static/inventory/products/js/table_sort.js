document.addEventListener("DOMContentLoaded", () => {
  const table = document.querySelector(".products-table");
  if (!table) return;
  const tbody = document.querySelector("#productTableBody");
  const headers = table.querySelectorAll("th");

  headers.forEach(header => {
    header.addEventListener("click", () => {
      const columnIndex = header.cellIndex;

      const currentOrder = header.classList.contains("asc")
        ? "asc"
        : header.classList.contains("desc")
        ? "desc"
        : null;

      headers.forEach(h => h.classList.remove("asc", "desc"));

      const newOrder = currentOrder === "asc" ? "desc" : "asc"; 
      header.classList.add(newOrder);

      const rows = Array.from(tbody.querySelectorAll("tr"));

      const getCellValue = (row) => {
        let value = row.cells[columnIndex].textContent.trim();

        // Remove currency symbols & spaces
        value = value.replace(/[€,$]/g, "").replace(/\s+/g, "");

        // Try numeric conversion
        const number = parseFloat(value.replace(",", "."));

        return !isNaN(number) && value !== ""
          ? number
          : value.toLowerCase();
      };

      rows.sort((a, b) => {
        const A = getCellValue(a);
        const B = getCellValue(b);

        if (typeof A === "number" && typeof B === "number") {
          return newOrder === "asc" ? A - B : B - A;
        }

        return newOrder === "asc"
          ? A.localeCompare(B, undefined, { numeric: true, sensitivity: "base" })
          : B.localeCompare(A, undefined, { numeric: true, sensitivity: "base" });
      });

      tbody.innerHTML = "";
      rows.forEach(row => tbody.appendChild(row));
    });
  });
});
