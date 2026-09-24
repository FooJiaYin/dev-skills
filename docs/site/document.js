(() => {
  "use strict";
  const params = new URLSearchParams(location.search);
  const id = params.get("skill");
  const registry = window.DEV_SKILLS_DEMOS || {};
  const demo = id === "improve" ? null : id === "meeting-transcript" ? registry["meeting-notes"]?.source : Object.hasOwn(registry, id) ? registry[id] : null;
  const $ = selector => document.querySelector(selector);
  document.body.classList.toggle("light", params.get("theme") === "light");
  function updateThemeLabel() {
    $(".theme-toggle").setAttribute("aria-label", "切換至 " + (document.body.classList.contains("light") ? "原版深色" : "Catppuccin Latte"));
  }
  $(".theme-toggle").addEventListener("click", () => {
    document.body.classList.toggle("light");
    updateThemeLabel();
  });
  updateThemeLabel();
  if (!demo) {
    document.title = "找不到示範文件";
    $("#document-title").textContent = "找不到這份示範文件";
    $("#document-path").textContent = "請從網站裡的文件按鈕重新開啟。";
    $("#document-content").hidden = true;
    return;
  }
  const filename = demo.output.split("/").filter(Boolean).at(-1);
  document.title = filename + " · 琢奧 ERP 示範";
  $("#document-title").textContent = filename;
  $("#document-path").textContent = (id === "meeting-transcript" ? "資料來源" : "/" + demo.id) + " ／ " + demo.output;
  $("#document-content").textContent = demo.artifact;
  if (window.DevSkillsMarkdown) $("#document-content").innerHTML = window.DevSkillsMarkdown.html(demo.artifact);
  $("#document-back").href = "index.html#demo-" + encodeURIComponent(id === "meeting-transcript" ? "meeting-notes" : id);
})();
