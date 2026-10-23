document.addEventListener('DOMContentLoaded', function() {
    const chatbotToggle = document.getElementById('chatbotToggle');
    const chatbotWindow = document.getElementById('chatbotWindow');
    const chatbotClose = document.getElementById('chatbotClose');
    const chatbotInput = document.getElementById('chatbotInput');
    const chatbotSend = document.getElementById('chatbotSend');
    const chatbotMessages = document.getElementById('chatbotMessages');
    const chatbotTyping = document.getElementById('chatbotTyping');

    // Toggle chatbot window
    chatbotToggle.addEventListener('click', function() {
        chatbotWindow.classList.toggle('open');
        if (chatbotWindow.classList.contains('open')) {
            chatbotInput.focus();
        }
    });

    // Close chatbot window
    chatbotClose.addEventListener('click', function() {
        chatbotWindow.classList.remove('open');
    });

    // Close on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && chatbotWindow.classList.contains('open')) {
            chatbotWindow.classList.remove('open');
        }
    });

    // Send message on Enter key
    chatbotInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            chatbotSend.click();
        }
    });

    // Send message
    chatbotSend.addEventListener('click', function() {
        const message = chatbotInput.value.trim();
        if (!message) return;

        // Disable send button while processing
        chatbotSend.disabled = true;
        chatbotInput.disabled = true;

        // Add user message to chat
        addMessage('user', message);
        chatbotInput.value = '';

        // Show typing indicator
        chatbotTyping.classList.add('show');

        // Send to backend
        fetch('/chatbot', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ message: message })
        })
        .then(response => response.json())
        .then(data => {
            chatbotTyping.classList.remove('show');
            chatbotSend.disabled = false;
            chatbotInput.disabled = false;
            chatbotInput.focus();
            
            if (data.success) {
                addMessage('bot', data.response);
            } else {
                addMessage('bot', 'Συγνώμη: ' + (data.error || 'Δεν ήταν δυνατή η επεξεργασία του αιτήματος.'));
            }
        })
        .catch(error => {
            chatbotTyping.classList.remove('show');
            chatbotSend.disabled = false;
            chatbotInput.disabled = false;
            chatbotInput.focus();
            addMessage('bot', 'Συγνώμη: Παρουσιάστηκε σφάλμα σύνδεσης. Παρακαλώ δοκιμάστε ξανά.');
            console.error('Chatbot error:', error);
        });
    });

    function addMessage(sender, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chatbot-message ${sender}`;
        
        const senderDiv = document.createElement('div');
        senderDiv.className = 'message-sender';
        senderDiv.textContent = sender === 'user' ? 'Εσείς' : 'Assistant';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Handle markdown-like formatting
        contentDiv.innerHTML = formatMessage(content);
        
        messageDiv.appendChild(senderDiv);
        messageDiv.appendChild(contentDiv);
        
        chatbotMessages.appendChild(messageDiv);
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    }

    function formatMessage(text) {
        // Simple formatting - convert newlines to <br>
        let formatted = text.replace(/\n/g, '<br>');
        
        // Bold text **text**
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Italic text *text*
        formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        return formatted;
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
