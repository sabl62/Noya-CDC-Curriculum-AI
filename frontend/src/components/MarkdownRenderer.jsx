import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

// Map of language identifiers to display names
const languageNames = {
  bash: "Bash",
  shell: "Shell",
  sh: "Shell",
  python: "Python",
  py: "Python",
  javascript: "JavaScript",
  js: "JavaScript",
  html: "HTML",
  css: "CSS",
  json: "JSON",
  sql: "SQL",
  java: "Java",
  cpp: "C++",
  c: "C",
  go: "Go",
  rust: "Rust",
  typescript: "TypeScript",
  ts: "TypeScript",
  xml: "XML",
  yaml: "YAML",
  yml: "YAML",
  markdown: "Markdown",
  md: "Markdown",
};

const getLanguageName = (lang) => {
  if (!lang) return null;
  return languageNames[lang.toLowerCase()] || lang;
};

// Code block with language header
const CodeBlock = ({ children, className }) => {
  const match = /language-(\w+)/.exec(className || "");
  const language = match ? match[1] : null;
  const displayName = getLanguageName(language);

  return (
    <div className="my-3 overflow-hidden rounded-[var(--radius-sm)] border border-[var(--border-strong)]">
      {displayName && (
        <div className="flex items-center justify-between bg-[var(--ink)] px-3 py-1.5 font-[var(--font-mono)] text-[12px] font-semibold text-[var(--bg)]">
          <span>{displayName}</span>
        </div>
      )}
      <pre className="overflow-x-auto bg-[var(--ink)] px-4 py-3 font-[var(--font-mono)] text-[13px] leading-relaxed text-[var(--bg)]">
        <code className={className}>{children}</code>
      </pre>
    </div>
  );
};

// Inline code
const InlineCode = ({ children }) => (
  <code className="rounded-[4px] bg-[var(--pine-tint)] px-[6px] py-[2px] font-[var(--font-mono)] text-[0.875em] font-medium text-[var(--pine-strong)]">
    {children}
  </code>
);

// Headings — left-border accent encodes hierarchy depth
const headingStyles = {
  1: "text-[22px] font-bold border-l-[3px] border-[var(--pine)] pl-3 mt-6 mb-2.5 leading-snug",
  2: "text-[19px] font-bold border-l-[3px] border-[var(--brass)] pl-3 mt-5 mb-2 leading-snug",
  3: "text-[16px] font-semibold mt-4 mb-1.5 leading-snug",
  4: "text-[15px] font-semibold mt-3 mb-1 leading-snug",
};

const Heading = ({ level, children }) => {
  const className = headingStyles[level] || headingStyles[4];
  const Tag = `h${level}`;
  const text = Array.isArray(children) ? children.join("") : String(children ?? "");
  const id = text.toLowerCase().replace(/[^\w]+/g, "-") || undefined;

  return (
    <Tag id={id} className={`${className} text-[var(--ink)] scroll-mt-20`}>
      {children}
    </Tag>
  );
};

// Hard-word tooltip: a tap/click-and-focus-friendly glossary mark,
// not a hover-only affordance (works for touch and keyboard).
const HardWord = ({ children, meaning, simple, example }) => {
  const [open, setOpen] = useState(false);

  return (
    <span className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        onBlur={() => setOpen(false)}
        aria-expanded={open}
        className="marginalia cursor-help border-b border-dashed border-[var(--brass)] text-[1em] not-italic font-semibold text-[var(--brass)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brass)]/40"
      >
        {children}
      </button>
      {open && (
        <span
          role="tooltip"
          className="animate-fade-in absolute bottom-full left-1/2 z-50 mb-2 w-64 -translate-x-1/2 rounded-[var(--radius-sm)] border border-[var(--border-strong)] bg-[var(--surface-raised)] p-3 text-left text-[12.5px] font-normal not-italic text-[var(--ink-soft)] shadow-[0_8px_24px_rgba(0,0,0,0.16)]"
        >
          <span className="mb-1.5 block border-b border-[var(--border)] pb-1.5 font-[var(--font-body)] text-[13px] font-bold text-[var(--ink)]">
            {children}
          </span>
          {meaning && (
            <span className="mb-1.5 block">
              <span className="mb-0.5 block font-semibold text-[var(--pine)]">Meaning</span>
              {meaning}
            </span>
          )}
          {simple && (
            <span className="mb-1.5 block">
              <span className="mb-0.5 block font-semibold text-[var(--brass)]">Simple version</span>
              {simple}
            </span>
          )}
          {example && (
            <span className="block italic">
              <span className="mb-0.5 block font-semibold text-[var(--ink-faint)] not-italic">Example</span>
              {example}
            </span>
          )}
        </span>
      )}
    </span>
  );
};

const MarkdownLink = ({ href, children }) => {
  if (href?.startsWith("hardword://")) {
    try {
      const details = decodeURIComponent(href.replace("hardword://", ""));
      const [meaning = "", simple = "", example = ""] = details.split("|").map((p) => p.trim());
      return (
        <HardWord meaning={meaning} simple={simple} example={example}>
          {children}
        </HardWord>
      );
    } catch {
      // fall through to a plain link if parsing fails
    }
  }

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="font-medium text-[var(--pine)] underline underline-offset-2 hover:text-[var(--pine-strong)]"
    >
      {children}
    </a>
  );
};

const List = ({ ordered, children }) => {
  const Component = ordered ? "ol" : "ul";
  return (
    <Component className={`my-1.5 ml-1 flex flex-col gap-1 pl-5 ${ordered ? "list-decimal" : "list-disc"}`}>
      {children}
    </Component>
  );
};

const ListItem = ({ children }) => <li className="pl-0.5 leading-[1.7]">{children}</li>;

const Blockquote = ({ children }) => (
  <blockquote className="my-3 rounded-r-[var(--radius-sm)] border-l-[3px] border-[var(--brass)] bg-[var(--brass-tint)] px-4 py-2.5 leading-relaxed text-[var(--ink-soft)]">
    {children}
  </blockquote>
);

const Table = ({ children }) => (
  <div className="my-3 overflow-x-auto rounded-[var(--radius-sm)] border border-[var(--border)]">
    <table className="w-full border-collapse text-[14px] tabular">{children}</table>
  </div>
);

const TableHead = ({ children }) => <thead className="bg-[var(--pine-tint)] font-semibold">{children}</thead>;
const TableBody = ({ children }) => <tbody>{children}</tbody>;
const TableRow = ({ children }) => <tr className="border-b border-[var(--border)] last:border-0">{children}</tr>;
const TableHeader = ({ children }) => <th className="px-3.5 py-2.5 text-left font-semibold text-[var(--ink)]">{children}</th>;
const TableCell = ({ children }) => <td className="px-3.5 py-2 text-[var(--ink-soft)]">{children}</td>;

const HorizontalRule = () => <hr className="my-4 border-t border-[var(--border)]" />;

const normalizeContent = (content) => {
  if (!content) return "";

  let text = "";
  if (typeof content === "string") {
    const trimmed = content.trim();
    if (trimmed.startsWith("{")) {
      try {
        text = JSON.parse(trimmed).response || trimmed;
      } catch {
        text = content;
      }
    } else {
      text = content;
    }
  } else {
    text = content?.response || "";
  }

  let result = text
    .replace(/\\\[((?:.|\n)*?)\\\]/g, (_, equation) => {
      const cleaned = equation.trim().replace(/<sub>(.*?)<\/sub>/g, '_{$1}').replace(/<sup>(.*?)<\/sup>/g, '^{$1}');
      return `\n$$${cleaned}$$\n`;
    })
    .replace(/\\\(((?:.|\n)*?)\\\)/g, (_, equation) => {
      const cleaned = equation.trim().replace(/<sub>(.*?)<\/sub>/g, '_{$1}').replace(/<sup>(.*?)<\/sup>/g, '^{$1}');
      return `$${cleaned}$`;
    })
    .replace(/(\S+)/g, (token) => {
      if (/<sub>|<sup>/i.test(token)) {
        return `$${token.replace(/<sub>(.*?)<\/sub>/g, '_{$1}').replace(/<sup>(.*?)<\/sup>/g, '^{$1}')}$`;
      }
      return token;
    })
    .replace(/\[\[([^:]+):\s*(.*?)\]\]/g, (_, term, details) => {
      return `[${term.trim()}](hardword://${encodeURIComponent(details.trim())})`;
    });

  return result;
};

const MarkdownRenderer = ({ content, className = "", onQuestionClick }) => {
  const sanitizedContent = normalizeContent(content);

  if (!sanitizedContent) return null;

  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[[rehypeKatex, { strict: false, throwOnError: false }]]}
        components={{
          code: ({ className, children }) => {
            const isInline = !className;
            return isInline ? <InlineCode>{children}</InlineCode> : <CodeBlock className={className}>{children}</CodeBlock>;
          },
          strong: ({ children }) => <strong className="font-bold text-[var(--ink)]">{children}</strong>,
          h1: ({ children }) => <Heading level={1}>{children}</Heading>,
          h2: ({ children }) => <Heading level={2}>{children}</Heading>,
          h3: ({ children }) => <Heading level={3}>{children}</Heading>,
          h4: ({ children }) => <Heading level={4}>{children}</Heading>,
          h5: ({ children }) => <Heading level={4}>{children}</Heading>,
          h6: ({ children }) => <Heading level={4}>{children}</Heading>,
          a: ({ href, children }) => {
            if (href === "#ask") {
              const text = Array.isArray(children) ? children.join("") : children;
              return (
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    onQuestionClick?.(text);
                  }}
                  className="inline-flex items-center gap-1.5 text-left font-medium text-[var(--pine)] transition-colors hover:text-[var(--pine-strong)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pine)]/40"
                >
                  <ChevronTick /> <span>{children}</span>
                </button>
              );
            }
            return <MarkdownLink href={href}>{children}</MarkdownLink>;
          },
          ul: ({ children }) => <List ordered={false}>{children}</List>,
          ol: ({ children }) => <List ordered>{children}</List>,
          li: ListItem,
          blockquote: Blockquote,
          table: Table,
          thead: TableHead,
          tbody: TableBody,
          tr: TableRow,
          th: TableHeader,
          td: TableCell,
          hr: HorizontalRule,
          p: ({ children }) => <p className="mb-2.5 leading-[1.7] text-[var(--ink)] last:mb-0">{children}</p>,
        }}
      >
        {sanitizedContent}
      </ReactMarkdown>
    </div>
  );
};

const ChevronTick = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true" className="shrink-0">
    <path d="M9 18l6-6-6-6" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export default MarkdownRenderer;
