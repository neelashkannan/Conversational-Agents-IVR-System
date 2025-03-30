document.addEventListener('DOMContentLoaded', function() {
    // Get elements
    const searchInput = document.querySelector('.search-bar input');
    const menuButtons = document.querySelectorAll('.menu-button');
    const closeButton = document.querySelector('.close-button');
    const performanceNotice = document.querySelector('.performance-notice');
    const backButton = document.querySelector('.back-button');

    // Add event listeners
    searchInput.addEventListener('focus', function() {
        this.placeholder = '';
    });

    searchInput.addEventListener('blur', function() {
        this.placeholder = 'E.g. Need a bank statement';
    });

    menuButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Simulate button press effect
            this.style.opacity = '0.7';
            setTimeout(() => {
                this.style.opacity = '1';
                alert(`You selected: ${this.textContent}`);
            }, 200);
        });
    });

    // Close performance notice
    if (closeButton && performanceNotice) {
        closeButton.addEventListener('click', function() {
            performanceNotice.style.display = 'none';
        });
    }

    // Back button functionality
    if (backButton) {
        backButton.addEventListener('click', function() {
            // Simulate going back
            alert('Going back...');
        });
    }
});