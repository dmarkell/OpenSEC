function toggleQuery() {
    var prompt = document.getElementById("query");
    if (prompt.placeholder === "Manager Name") {
        prompt.placeholder = "Ticker";
    } else {
        prompt.placeholder = "Manager Name";
    }
}