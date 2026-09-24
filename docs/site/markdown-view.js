// Markdown source highlighting for demo documents (IDE-style: source stays visible, tokens get color).
// Only wraps text in spans, so element.textContent still equals the original document.
(root => {
  "use strict";
  const esc = value => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
  const span = (cls, text) => '<span class="' + cls + '">' + esc(text) + "</span>";
  const INLINE = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\[[^\]]+\]\([^)\s]+\))|(<!--.*?-->)|(<\/?[a-z][a-z-]*(?:\s[^<>]*)?\/?>)|(~~[^~]+~~)/gi;

  function inline(text) {
    let html = "";
    let last = 0;
    for (const m of text.matchAll(INLINE)) {
      html += esc(text.slice(last, m.index));
      const [tok, code, strong, link, comment, tag, strike] = m;
      if (code) html += span("md-inline", tok);
      else if (strong) html += span("md-strong", tok);
      else if (link) {
        const cut = tok.indexOf("](");
        html += span("md-link", tok.slice(0, cut + 1)) + span("md-url", tok.slice(cut + 1));
      } else if (comment) html += span("md-comment", tok);
      else if (tag) html += span("md-tag", tok);
      else if (strike) html += span("md-strike", tok);
      last = m.index + tok.length;
    }
    return html + esc(text.slice(last));
  }

  function lines(text) {
    const src = String(text).split("\n");
    let inFront = src[0] === "---";
    let inFence = false;
    return src.map((line, i) => {
      if (inFront) {
        if (i > 0 && line === "---") inFront = false;
        const kv = line.match(/^(\s*-?\s*)([\w.]+)(:)(.*)$/);
        if (kv) return esc(kv[1]) + span("md-key", kv[2] + kv[3]) + span("md-meta", kv[4]);
        return span("md-meta", line);
      }
      if (/^\s*```/.test(line)) { inFence = !inFence; return span("md-fence", line); }
      if (inFence) return span("md-code", line);
      let m;
      if ((m = line.match(/^(#{1,6}\s)(.*)$/))) return span("md-mark", m[1]) + '<span class="md-h">' + inline(m[2]) + "</span>";
      if (/^(-{3,}|─{3,})$/.test(line)) return span("md-mark", line);
      if ((m = line.match(/^(\s*)([-*]|\d+\.)(\s)(.*)$/))) return esc(m[1]) + span("md-mark", m[2]) + esc(m[3]) + inline(m[4]);
      if ((m = line.match(/^(>\s?)(.*)$/))) return span("md-mark", m[1]) + '<span class="md-quote">' + inline(m[2]) + "</span>";
      if (line.startsWith("|")) return line.split(/(\|)/).map(part => part === "|" ? span("md-mark", part) : inline(part)).join("");
      if ((m = line.match(/^(\[[\d-]+ [\d:]+ )(\w+)(\])(.*)$/))) return span("md-meta", m[1]) + span("md-key", m[2]) + span("md-meta", m[3]) + inline(m[4]);
      return inline(line);
    });
  }

  root.DevSkillsMarkdown = { lines, html: text => lines(text).join("\n") };
})(typeof window !== "undefined" ? window : globalThis);
