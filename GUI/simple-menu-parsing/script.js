document.addEventListener("DOMContentLoaded", () => {
    let jsonData = {};
    let currentScreen = 0;
    const app = document.getElementById("app");

    // Fetch JSON data
    fetch("participant-menu.json")
        .then(response => response.json())
        .then(data => {
            jsonData = data;
            renderScreen();
        })
        .catch(error => console.error("Error loading JSON:", error));

    function renderScreen() {
        const screen = jsonData.screens[currentScreen];

        // Apply fade-out animation before updating content
        app.classList.add("hidden");

        setTimeout(() => {
            app.innerHTML = `
                <h2>${screen.title}</h2>
                <p>${screen.description}</p>
                ${screen.options.map(option => `<button onclick="nextScreen()">${option}</button>`).join('')}
            `;

            // Apply fade-in animation after content update
            setTimeout(() => app.classList.remove("hidden"), 100);
        }, 400);
    }

    window.nextScreen = function () {
        if (currentScreen < jsonData.screens.length - 1) {
            currentScreen++;
            renderScreen();
        } else {
            app.innerHTML = "<h2>Thank you for participating!</h2>";
        }
    };
});
