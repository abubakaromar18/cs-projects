import type { Language } from "./types";

/**
 * A small, dependency-free syntax highlighter.
 *
 * It is a *regex-driven lexer*: for each language we list rules in priority
 * order. At every position in the source we try each rule as a sticky (`y`)
 * regex anchored at that position; the first rule that matches wins, emits a
 * token, and the cursor advances past it. Ordering matters — comments and
 * strings come first so that `"// not a comment"` stays a string.
 *
 * The output is a flat list of typed tokens. Rendering is left to React, which
 * escapes text automatically, so highlighted code can never inject HTML.
 */

export type TokenKind =
  | "comment"
  | "string"
  | "number"
  | "keyword"
  | "literal" // true/false/null and friends
  | "type"
  | "function"
  | "variable" // e.g. $VAR in bash
  | "property" // JSON object keys
  | "operator"
  | "punctuation"
  | "plain";

export interface Token {
  kind: TokenKind;
  text: string;
}

interface Rule {
  kind: TokenKind;
  re: RegExp;
}

/** Build a sticky regex matching any of the given words as whole words. */
function words(list: string, flags = ""): RegExp {
  return new RegExp(`\\b(?:${list.trim().split(/\s+/).join("|")})\\b`, "y" + flags);
}

const NUMBER: Rule = { kind: "number", re: /\b(?:0[xX][\da-fA-F_]+|0[bB][01_]+|\d[\d_]*(?:\.\d+)?(?:[eE][+-]?\d+)?)\b/y };
const DQ_STRING: Rule = { kind: "string", re: /"(?:[^"\\\n]|\\.)*"?/y };
const SQ_STRING: Rule = { kind: "string", re: /'(?:[^'\\\n]|\\.)*'?/y };
const FUNC_CALL: Rule = { kind: "function", re: /\b[A-Za-z_]\w*(?=\s*\()/y };
const CAP_TYPE: Rule = { kind: "type", re: /\b[A-Z]\w*\b/y };
const OPERATOR: Rule = { kind: "operator", re: /[+\-*/%=!<>&|^~?:]+/y };
const PUNCT: Rule = { kind: "punctuation", re: /[()[\]{},;.]/y };
const WORD: Rule = { kind: "plain", re: /\w+/y };

const JS_KEYWORDS =
  "async await break case catch class const continue debugger default delete do else export extends finally for from function if import in instanceof let new of return static super switch this throw try typeof var void while with yield";

const javascript: Rule[] = [
  { kind: "comment", re: /\/\/[^\n]*|\/\*[\s\S]*?(?:\*\/|$)/y },
  { kind: "string", re: /`(?:[^`\\]|\\[\s\S])*`?/y },
  DQ_STRING,
  SQ_STRING,
  { kind: "literal", re: words("true false null undefined NaN Infinity") },
  { kind: "keyword", re: words(JS_KEYWORDS) },
  NUMBER,
  FUNC_CALL,
  CAP_TYPE,
  WORD,
  OPERATOR,
  PUNCT,
];

const typescript: Rule[] = [
  ...javascript.slice(0, 5),
  { kind: "keyword", re: words(JS_KEYWORDS + " type interface enum implements private public protected readonly declare namespace abstract as satisfies keyof infer is") },
  { kind: "type", re: words("string number boolean any unknown never void object bigint symbol") },
  ...javascript.slice(6),
];

const python: Rule[] = [
  { kind: "comment", re: /#[^\n]*/y },
  { kind: "string", re: /[rbfRBF]{0,2}(?:"""[\s\S]*?(?:"""|$)|'''[\s\S]*?(?:'''|$))/y },
  { kind: "string", re: /[rbfRBF]{0,2}(?:"(?:[^"\\\n]|\\.)*"?|'(?:[^'\\\n]|\\.)*'?)/y },
  { kind: "literal", re: words("True False None") },
  { kind: "keyword", re: words("and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield match case") },
  { kind: "function", re: /@[\w.]+/y }, // decorators
  NUMBER,
  FUNC_CALL,
  CAP_TYPE,
  WORD,
  OPERATOR,
  PUNCT,
];

const go: Rule[] = [
  javascript[0],
  { kind: "string", re: /`[^`]*`?/y },
  DQ_STRING,
  SQ_STRING,
  { kind: "literal", re: words("true false nil iota") },
  { kind: "keyword", re: words("break case chan const continue default defer else fallthrough for func go goto if import interface map package range return select struct switch type var") },
  { kind: "type", re: words("bool byte complex64 complex128 error float32 float64 int int8 int16 int32 int64 rune string uint uint8 uint16 uint32 uint64 uintptr any") },
  NUMBER,
  FUNC_CALL,
  CAP_TYPE,
  WORD,
  OPERATOR,
  PUNCT,
];

const rust: Rule[] = [
  javascript[0],
  { kind: "string", re: /r#*"[\s\S]*?"#*/y },
  DQ_STRING,
  { kind: "string", re: /'(?:[^'\\\n]|\\.)'/y }, // char literal (lifetimes like 'a fall through)
  { kind: "literal", re: words("true false None Some Ok Err") },
  { kind: "keyword", re: words("as async await break const continue crate dyn else enum extern fn for if impl in let loop match mod move mut pub ref return self Self static struct super trait type unsafe use where while") },
  { kind: "type", re: words("i8 i16 i32 i64 i128 isize u8 u16 u32 u64 u128 usize f32 f64 bool char str String Vec Option Result Box") },
  { kind: "function", re: /\b[a-z_]\w*!/y }, // macros: println!
  NUMBER,
  FUNC_CALL,
  CAP_TYPE,
  WORD,
  OPERATOR,
  PUNCT,
];

const bash: Rule[] = [
  { kind: "comment", re: /#[^\n]*/y },
  DQ_STRING,
  { kind: "string", re: /'[^']*'?/y }, // no escapes inside single quotes in sh
  { kind: "variable", re: /\$(?:\{[^}]*\}|\w+|[@#?$!*0-9])/y },
  { kind: "keyword", re: words("if then else elif fi for while until do done case esac in function return local export readonly select") },
  { kind: "function", re: words("echo printf cd ls grep sed awk cat find xargs curl git mkdir rm cp mv chmod chown test read set source") },
  NUMBER,
  { kind: "plain", re: /[\w./-]+/y },
  OPERATOR,
  PUNCT,
];

const sql: Rule[] = [
  { kind: "comment", re: /--[^\n]*|\/\*[\s\S]*?(?:\*\/|$)/y },
  { kind: "string", re: /'(?:[^']|'')*'?/y }, // SQL escapes a quote by doubling it
  { kind: "property", re: /"(?:[^"]|"")*"?/y }, // quoted identifier
  { kind: "literal", re: words("NULL TRUE FALSE", "i") },
  { kind: "keyword", re: words("select from where and or not insert into values update set delete create table index view drop alter add join left right inner outer full on group by order having limit offset as distinct union all case when then else end primary key foreign references default exists in is like between with returning", "i") },
  { kind: "type", re: words("int integer bigint smallint text varchar char boolean date timestamp numeric real serial", "i") },
  NUMBER,
  FUNC_CALL,
  WORD,
  OPERATOR,
  PUNCT,
];

const json: Rule[] = [
  { kind: "property", re: /"(?:[^"\\\n]|\\.)*"(?=\s*:)/y },
  DQ_STRING,
  { kind: "literal", re: words("true false null") },
  { kind: "number", re: /-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/y },
  { kind: "punctuation", re: /[{}[\],:]/y },
];

const RULES: Record<Language, Rule[]> = {
  javascript,
  typescript,
  python,
  go,
  rust,
  bash,
  sql,
  json,
  text: [],
};

/**
 * Tokenise `code`. Whitespace and any character no rule recognises become
 * "plain" tokens; adjacent tokens of the same kind are merged so the output
 * stays compact. Concatenating every token's text always reproduces `code`.
 */
export function highlight(code: string, language: Language): Token[] {
  const rules = RULES[language] ?? [];
  const tokens: Token[] = [];
  const push = (kind: TokenKind, text: string) => {
    const last = tokens[tokens.length - 1];
    if (last && last.kind === kind) last.text += text;
    else tokens.push({ kind, text });
  };

  let pos = 0;
  outer: while (pos < code.length) {
    // Whitespace is never significant for colouring.
    const ch = code[pos];
    if (ch === " " || ch === "\t" || ch === "\n" || ch === "\r") {
      push("plain", ch);
      pos++;
      continue;
    }
    for (const rule of rules) {
      rule.re.lastIndex = pos;
      const m = rule.re.exec(code);
      if (m && m[0].length > 0) {
        push(rule.kind, m[0]);
        pos += m[0].length;
        continue outer;
      }
    }
    push("plain", ch);
    pos++;
  }
  return tokens;
}

/** Split tokens into lines (for line numbers). Tokens spanning newlines are cut. */
export function toLines(tokens: Token[]): Token[][] {
  const lines: Token[][] = [[]];
  for (const t of tokens) {
    const parts = t.text.split("\n");
    parts.forEach((part, i) => {
      if (i > 0) lines.push([]);
      if (part) lines[lines.length - 1].push({ kind: t.kind, text: part });
    });
  }
  return lines;
}
