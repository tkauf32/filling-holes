document.addEventListener("DOMContentLoaded", () => {
  const imageInput = document.querySelector("#image-input");
  const imageHelp = document.querySelector("#image-help");
  if (imageInput && imageHelp) {
    imageInput.addEventListener("change", () => {
      const count = imageInput.files ? imageInput.files.length : 0;
      if (count > 3) {
        imageHelp.textContent = "Too many images. Keep it to 3.";
        imageHelp.classList.add("text-red-600");
      } else {
        imageHelp.textContent = count
          ? `${count} image${count === 1 ? "" : "s"} selected.`
          : "Add up to 3 images. Wide shots help. So do receipts from your mechanic, spiritually.";
        imageHelp.classList.remove("text-red-600");
      }
    });
  }

  document.querySelectorAll("[data-copy-url]").forEach((button) => {
    button.addEventListener("click", async () => {
      const url = button.getAttribute("data-copy-url");
      if (!url) return;
      try {
        await navigator.clipboard.writeText(url);
        button.textContent = "Link copied";
      } catch {
        button.textContent = url;
      }
    });
  });

  document.querySelectorAll("[data-calculating]").forEach((button) => {
    button.form?.addEventListener("submit", () => {
      button.disabled = true;
      button.textContent = "Calculating estimate...";
    });
  });
});
