document.querySelectorAll("[data-table-search]").forEach((container) => {
    const input = document.querySelector(container.dataset.searchInput);
    const table = document.querySelector(container.dataset.searchTable);
    const count = document.querySelector(container.dataset.searchCount);

    if (!input || !table) return;

    const rows = Array.from(table.tBodies[0].rows);

    // Column indexes to search, starting from zero.
    const columns = JSON.parse(container.dataset.searchColumns || "[]");

    function search(query) {
        const term = query.trim().toLocaleLowerCase("el-GR");
        let visible = 0;

        rows.forEach((row) => {
            const text = columns
                .map((index) => row.cells[index]?.textContent || "")
                .join(" ")
                .toLocaleLowerCase("el-GR");

            const matches = !term || text.includes(term);

            row.hidden = !matches;

            if (matches) visible++;
        });

        if (count) {
            count.textContent = `${visible} αποτελέσματα`;
        }
    }

    input.addEventListener("input", () => search(input.value));
    search("");
});
