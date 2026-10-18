// Copy barcode functionality
document.addEventListener('DOMContentLoaded', function() {
    const copyButtons = document.querySelectorAll('.btn-copy-barcode');

    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const barcode = this.getAttribute('data-barcode');

            // Copy to clipboard
            navigator.clipboard.writeText(barcode).then(function() {
                // Show toast notification
                showToast('Barcode αντιγράφηκε!');
            }).catch(function(err) {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = barcode;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                showToast('Barcode αντιγράφηκε!');
            });
        });
    });

    // Toast notification function
    function showToast(message) {
        // Remove existing toast if any
        const existingToast = document.querySelector('.toast-notification');
        if (existingToast) {
            existingToast.remove();
        }

        // Create toast element
        const toast = document.createElement('div');
        toast.className = 'toast-notification';
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background-color: #10b981;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 10000;
            animation: slideIn 0.3s ease;
            font-weight: 500;
        `;

        // Add animation keyframes if not already present
        if (!document.querySelector('#toast-animations')) {
            const style = document.createElement('style');
            style.id = 'toast-animations';
            style.textContent = `
                @keyframes slideIn {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                @keyframes slideOut {
                    from {
                        transform: translateX(0);
                        opacity: 1;
                    }
                    to {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(toast);

        // Remove toast after 2 seconds
        setTimeout(function() {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(function() {
                toast.remove();
            }, 300);
        }, 2000);
    }
});
