document.addEventListener('DOMContentLoaded', function() {
  const selectAllCheckbox = document.getElementById('selectAll');
  const checkboxes = document.querySelectorAll('.products-table tbody .checkbox');
  const deleteBtn = document.getElementById('deleteSelectedBtn'); // reference to delete button

  // Array to store selected barcode values
  let selectedBarcodes = [];

  // Hide delete button by default
  deleteBtn.style.display = 'none';

  // Function to update selectedBarcodes array and toggle delete button
  function updateSelectedBarcodes() {
    selectedBarcodes = [];
    checkboxes.forEach(cb => {
      if (cb.checked) selectedBarcodes.push(cb.value);
    });
    console.log('Selected barcodes:', selectedBarcodes); // For testing

    // Show button only if at least one checkbox is selected
    if (selectedBarcodes.length > 0) {
      deleteBtn.style.display = 'inline-flex';
    } else {
      deleteBtn.style.display = 'none';
    }
  }


deleteBtn.addEventListener('click', function() {
    if (selectedBarcodes.length === 0) {
        alert('Select at least one product to delete.');
        return;
    }

    fetch('/product/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ barcodes: selectedBarcodes }),
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
  // Handle selectAll checkbox
  selectAllCheckbox.addEventListener('change', function() {
    checkboxes.forEach(cb => {
      cb.checked = selectAllCheckbox.checked;
    });
    updateSelectedBarcodes();
  });

  // Handle individual checkboxes
  checkboxes.forEach(cb => {
    cb.addEventListener('change', function() {
      // If any checkbox is unchecked, uncheck selectAll
      if (!cb.checked) {
        selectAllCheckbox.checked = false;
      } else if (Array.from(checkboxes).every(c => c.checked)) {
        // If all checkboxes are checked, check selectAll
        selectAllCheckbox.checked = true;
      }
      updateSelectedBarcodes();
    });
  });
});
