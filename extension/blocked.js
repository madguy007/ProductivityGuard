const params = new URLSearchParams(location.search);
document.getElementById("site").textContent = params.get("site") || "This site";
document.getElementById("balance").textContent = params.get("balance") || "0";
