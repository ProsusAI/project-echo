<template>
  <div class="message-text" v-html="sanitizedContent"></div>
</template>

<script>
import { markdown } from '@/utils/marked';
import sanitizeHtml from 'sanitize-html';

export default {
  name: 'MarkdownComponent',
  props: {
    content: {
      type: String,
      required: true
    }
  },
  computed: {
    sanitizedContent() {
      try {
        const rawHtml = markdown.render(this.content);
        return sanitizeHtml(rawHtml, {
          allowedTags: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'p', 'a', 'ul', 'ol',
            'nl', 'li', 'b', 'i', 'strong', 'em', 'strike', 'code', 'hr', 'br', 'div',
            'table', 'thead', 'caption', 'tbody', 'tr', 'th', 'td', 'pre', 'span', 'img'],
          allowedAttributes: {
            '*': ['class', 'style'],
            'a': ['href', 'name', 'target'],
            'img': ['src', 'alt', 'title']
          },
          transformTags: {
            'a': (tagName, attribs) => {
              return {
                tagName,
                attribs: { ...attribs, target: '_blank' }
              };
            }
          }
        });
      } catch (error) {
        console.error('Error rendering markdown:', error);
        return '<p class="error">Error rendering content</p>';
      }
    }
  },
  mounted() {
    this.$nextTick(() => {
      this.addCopyButtons();
    });
  },
  updated() {
    this.$nextTick(() => {
      this.addCopyButtons();
    });
  },
  methods: {
    addCopyButtons() {
      const codeBlocks = document.querySelectorAll('.message-text pre[class*="language-"]');
      codeBlocks.forEach((block) => {
        if (!block.querySelector('.copy-button')) {
          const button = document.createElement('button');
          button.className = 'copy-button';
          button.innerHTML = 'Copy';
          button.addEventListener('click', () => this.copyCode(block, button));
          block.style.position = 'relative';
          block.appendChild(button);
        }
      });
    },
    copyCode(block, button) {
      const code = block.querySelector('code').innerText;
      navigator.clipboard.writeText(code).then(() => {
        button.innerHTML = 'Copied!';
        setTimeout(() => {
          button.innerHTML = 'Copy';
        }, 2000);
      }, (err) => {
        console.error('Could not copy text: ', err);
        button.innerHTML = 'Error';
      });
    }
  }
}
</script>

<style>
.copy-button {
  position: absolute;
  top: 5px;
  right: 5px;
  padding: 5px 10px;
  background-color: #2d333b;
  color: #c9d1d9;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.3s;
}

pre[class*="language-"]:hover .copy-button {
  opacity: 1;
}

.copy-button:hover {
  background-color: #444c56;
}

.message-text pre[class*="language-"] {
  position: relative;
  padding-top: 2.5em; /* Make room for the copy button */
}
</style>