
const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const loginTab = document.getElementById("loginTab");
const registerTab = document.getElementById("registerTab");
const authMessage = document.getElementById("authMessage");

function showLogin() {
    loginForm.style.display = "block";
    registerForm.style.display = "none";
    loginTab.classList.add("active");
    registerTab.classList.remove("active");
    authMessage.textContent = "";
}

function showRegister() {
    loginForm.style.display = "none";
    registerForm.style.display = "block";
    registerTab.classList.add("active");
    loginTab.classList.remove("active");
    authMessage.textContent = "";
}

loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const button = loginForm.querySelector("button[type='submit']");
    button.disabled = true;
    button.textContent = "Logging in...";

    try {
        const response = await fetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                email: document.getElementById("loginEmail").value,
                password: document.getElementById("loginPassword").value
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Login failed.");
        }

        authMessage.textContent = "Login successful! Opening dashboard...";
        window.location.href = "/";

    } catch (error) {
        authMessage.textContent = error.message;
    } finally {
        button.disabled = false;
        button.textContent = "Login";
    }
});

registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const button = registerForm.querySelector("button[type='submit']");
    button.disabled = true;
    button.textContent = "Creating account...";

    try {
        const response = await fetch("/api/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                full_name: document.getElementById("registerName").value,
                email: document.getElementById("registerEmail").value,
                password: document.getElementById("registerPassword").value
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Registration failed.");
        }

        showLogin();
        authMessage.textContent = "Account created! Please log in.";

        document.getElementById("loginEmail").value =
            document.getElementById("registerEmail").value;

    } catch (error) {
        authMessage.textContent = error.message;
    } finally {
        button.disabled = false;
        button.textContent = "Create Account";
    }
});
