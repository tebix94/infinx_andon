// app/static/user_js/SignupFormDataValidation.js
console.log("Validation Script Active! 🚀");

const validatePassword = () => {
    const password = document.getElementById('password');
    const confirm = document.getElementById('password_confirmation');
    const message = document.getElementById('message');

    // If the user hasn't typed in the second box yet, keep it quiet
    if (confirm.value.length === 0) {
        message.innerText = "";
        confirm.setCustomValidity("");
        return;
    }

    if (password.value === confirm.value) {
        message.innerText = "✅ Las contraseñas coinciden";
        message.style.color = "green";
        confirm.setCustomValidity(""); // Valid state
    } else {
        message.innerText = "❌ Las contraseñas no coinciden";
        message.style.color = "red";
        confirm.setCustomValidity("Invalid"); // Invalid state
    }
};

document.addEventListener('DOMContentLoaded', () => {
    const p = document.getElementById('password');
    const c = document.getElementById('password_confirmation');

    if (p && c) {
        p.addEventListener('input', validatePassword);
        c.addEventListener('input', validatePassword);
        console.log("Listeners attached to inputs! 👂");
    } else {
        console.error("Could not find password fields by ID.");
    }
});