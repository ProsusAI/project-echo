import MarkdownIt from 'markdown-it';
import Prism from 'prismjs';
import 'prismjs/themes/prism.css';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-typescript';
import 'prismjs/components/prism-bash';
import 'prismjs/components/prism-json';
import 'prismjs/components/prism-markdown';
import 'prismjs/components/prism-yaml';
import 'prismjs/components/prism-docker';
import 'prismjs/components/prism-java';
import 'prismjs/components/prism-rust';
import 'prismjs/components/prism-csharp';
import 'prismjs/components/prism-sql';
import 'prismjs/components/prism-css';
import 'prismjs/components/prism-scss';
import 'prismjs/components/prism-json';
import 'prismjs/components/prism-regex';

const md = new MarkdownIt({
  html: true,
  breaks: true,
  linkify: true,
  highlight: function (str, lang) {
    if (lang && Prism.languages[lang]) {
      try {
        return '<pre class="language-' + lang + '"><code>' +
               Prism.highlight(str, Prism.languages[lang], lang) +
               '</code></pre>';
      } catch (__) {
        return '<pre class="language-none"><code>' + md.utils.escapeHtml(str) + '</code></pre>';
      }
    }
    return '<pre class="language-none"><code>' + md.utils.escapeHtml(str) + '</code></pre>';
  }
});

// Add target="_blank" to all links
md.renderer.rules.link_open = function (tokens, idx, options, env, self) {
  // If the link does not have target attribute, add target="_blank"
  const aIndex = tokens[idx].attrIndex('target');
  if (aIndex < 0) {
    tokens[idx].attrPush(['target', '_blank']); // add new attribute
  } else {
    tokens[idx].attrs[aIndex][1] = '_blank'; // replace value of existing attribute
  }
  // pass token to default renderer.
  return self.renderToken(tokens, idx, options);
};

export { md as markdown };