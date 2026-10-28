document.addEventListener('DOMContentLoaded', () => {
    const deleteBtn = document.getElementById('btnProductDelete');
    const container = document; // or a specific parent container

    if (!deleteBtn) return;

    // Only rows the user can see count, so hidden rows (in-page search, mobile/desktop duplicates) are never deleted
    function visibleBoxes() {
        return Array.from(document.querySelectorAll('.checkbox'))
            .filter(cb => cb.id !== 'selectAll' && cb.offsetParent !== null);
    }

    function selectedBarcodes() {
        return [...new Set(visibleBoxes().filter(cb => cb.checked).map(cb => cb.value))];
    }

    function refresh() {
        const boxes = visibleBoxes();
        deleteBtn.classList.toggle('show', selectedBarcodes().length > 0);
        const selectAll = document.getElementById('selectAll');
        if (selectAll) selectAll.checked = boxes.length > 0 && boxes.every(cb => cb.checked);
    }

    deleteBtn.addEventListener('click', () => {
        fetch('/product/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ barcodes: selectedBarcodes() }),
        })
        .then(response => response.json())
        .then(data => {
            console.log('Server response:', data);
            if (data.status === "success") {
                location.reload();
            } else {
                console.error('Error deleting products:', data.message);
            }
        })
        .catch(error => {
            console.error('Error deleting products:', error);
        });
    });

    container.addEventListener('change', (e) => {
        const target = e.target;
        if (target.id === 'selectAll') {
            visibleBoxes().forEach(cb => { cb.checked = target.checked; });
        }
        if (target.classList.contains('checkbox')) refresh();
    });

    document.addEventListener('table-search', refresh);
});
