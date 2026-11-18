import { highlight, toLines } from "@/lib/highlight";
import type { Language } from "@/lib/types";

/**
 * Render highlighted code with line numbers. Pure and hook-free, so it works
 * in both Server and Client Components. Each token becomes a <span> whose
 * class (tok-keyword, tok-string, ...) is coloured in globals.css.
 */
export function CodeBlock({
  code,
  language,
  maxLines,
}: {
  code: string;
  language: Language;
  maxLines?: number;
}) {
  let lines = toLines(highlight(code, language));
  const truncated = maxLines !== undefined && lines.length > maxLines;
  if (truncated) lines = lines.slice(0, maxLines);
  return (
    <pre className="code" data-language={language}>
      <code>
        {lines.map((line, i) => (
          <span className="line" key={i}>
            <span className="ln" aria-hidden="true">
              {i + 1}
            </span>
            {line.map((t, j) =>
              t.kind === "plain" ? t.text : (
                <span key={j} className={`tok-${t.kind}`}>
                  {t.text}
                </span>
              ),
            )}
            {"\n"}
          </span>
        ))}
        {truncated && <span className="more">…</span>}
      </code>
    </pre>
  );
}
