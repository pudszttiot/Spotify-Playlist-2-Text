document.addEventListener("DOMContentLoaded", function() {
    const button = document.createElement("button");
    button.textContent = "Click Me!";
    button.style.padding = "10px 20px";
    button.style.marginTop = "20px";
    button.style.backgroundColor = "#4CAF50";
    button.style.color = "white";
    button.style.border = "none";
    button.style.cursor = "pointer";

    button.addEventListener("click", function() {
        alert("Button was clicked!");
    });

    document.body.appendChild(button);
});
