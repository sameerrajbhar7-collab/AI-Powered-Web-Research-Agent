document.addEventListener("DOMContentLoaded", () => {
  const searchForm = document.getElementById("searchForm");
  const questionInput = document.getElementById("questionInput");
  const searchBtn = document.getElementById("searchBtn");
  const btnSpinner = document.getElementById("btnSpinner");
  const btnText = document.getElementById("btnText");
  const loadingIndicator = document.getElementById("loadingIndicator");
  const statusText = document.getElementById("statusText");
  const resultsSection = document.getElementById("resultsSection");
  const answerContent = document.getElementById("answerContent");

  searchForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = questionInput.value.trim();
    if (!question) return;

    // Set Loading State
    searchBtn.disabled = true;
    btnSpinner.style.display = "inline-block";
    btnText.textContent = "Searching...";
    loadingIndicator.style.display = "flex";
    statusText.textContent = "Searching the web with Playwright...";

    // Reset previous results
    resultsSection.style.display = "none";
    answerContent.innerHTML = "";

    try {
      const response = await fetch("/research/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: question,
          max_depth: 1,
          max_sources: 3,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop();

        for (const block of lines) {
          const trimmed = block.trim();
          if (trimmed.startsWith("data:")) {
            const jsonStr = trimmed.replace(/^data:\s*/, "");
            try {
              const event = JSON.parse(jsonStr);
              handleStreamEvent(event);
            } catch (err) {
              console.error("JSON parse error:", err);
            }
          }
        }
      }
    } catch (err) {
      statusText.textContent = `Error: ${err.message}`;
    } finally {
      searchBtn.disabled = false;
      btnSpinner.style.display = "none";
      btnText.textContent = "Search";
    }
  });

  function handleStreamEvent(event) {
    if (event.step === "SEARCHING") {
      statusText.textContent = "Searching web pages with Playwright...";
    } else if (event.step === "CRAWLING") {
      statusText.textContent = "Opening relevant pages & extracting text...";
    } else if (event.step === "SYNTHESIZING") {
      statusText.textContent = "Qwen is reading web content & formulating answer...";
    } else if (event.step === "COMPLETE" && event.details) {
      loadingIndicator.style.display = "none";
      renderResults(event.details);
    }
  }

  function renderResults(data) {
    resultsSection.style.display = "flex";

    // Render Answer and Sources Used
    const answer = data.answer || data.report || "No answer generated.";
    if (typeof marked !== "undefined") {
      answerContent.innerHTML = marked.parse(answer);
    } else {
      answerContent.textContent = answer;
    }
  }
});
