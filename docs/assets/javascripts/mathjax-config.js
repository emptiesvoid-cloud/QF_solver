window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"], ["$", "$"]],
    displayMath: [["\\[", "\\]"], ["$$", "$$"]],
    processEscapes: true,
    tags: "ams"
  },
  options: {
    ignoreHtmlClass: "no-mathjax",
    processHtmlClass: "arithmatex"
  }
};

document$.subscribe(function () {
  if (window.MathJax && window.MathJax.typesetPromise) {
    window.MathJax.typesetClear();
    window.MathJax.typesetPromise();
  }
});
