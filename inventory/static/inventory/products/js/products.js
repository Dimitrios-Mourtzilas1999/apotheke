document.addEventListener('DOMContentLoaded', () => {
    const deleteBtn = document.getElementById('btnProductDelete');
    const container = document; // or a specific parent container

    if (!deleteBtn) return;

    // Store checked values
    let barcodes = [];

    function toggleDeleteBtn() {
        if (barcodes.length > 0) {
            deleteBtn.classList.add('show');
        } else {
            deleteBtn.classList.remove('show');
        }
    }


    deleteBtn.addEventListener('click', () => {
        fetch('/product/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ barcodes }),
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

    // Single delegated listener
    container.addEventListener('change', (e) => {
        const target = e.target;

        // Check if it's the "select all" checkbox
        if (target.id === 'selectAll') {
            const checkboxes = document.querySelectorAll('.checkbox');
            checkboxes.forEach(cb => {
                cb.checked = target.checked;
            });
            barcodes = target.checked 
                ? Array.from(document.querySelectorAll('.checkbox')).map(cb => cb.value)
                : [];
            toggleDeleteBtn();
            return;
        }

        // Check if it's an individual checkbox
        if (target.classList.contains('checkbox')) {
            const value = target.value;
            if (target.checked) {
                if (!barcodes.includes(value)) barcodes.push(value);
            } else {
                barcodes = barcodes.filter(v => v !== value);
            }

            // Update selectAll checkbox state
            const selectAll = document.getElementById('selectAll');
            if (selectAll) {
                selectAll.checked = Array.from(document.querySelectorAll('.checkbox')).every(cb => cb.checked);
            }

            toggleDeleteBtn();
        }
    });
});
