#!/usr/bin/env python3
"""Write the Codex syntax themes (TextMate .tmTheme) for both modes.

  gen/tmtheme.py      -> codex/vesper.tmTheme, codex/flexoki-light.tmTheme
"""
from pathlib import Path
from xml.sax.saxutils import escape

THEMES = {
    "vesper": dict(
        name="Vesper", bg="#101010", fg="#ffffff", sel="#343434", line="#161616",
        comment="#7e7e7e", string="#99ffe4", number="#ffc799", constant="#ffc799",
        keyword="#a0a0a0", function="#ffc799", type="#ffc799", variable="#ffffff",
        tag="#a0a0a0", attr="#ffc799", punct="#a0a0a0", invalid="#ff8080",
        inserted="#99ffe4", deleted="#ff8080", changed="#ffc799", heading="#ffc799",
    ),
    "flexoki-light": dict(
        name="Flexoki Light", bg="#fffcf0", fg="#100f0f", sel="#dad8ce", line="#f2f0e5",
        comment="#878580", string="#24837b", number="#5e409d", constant="#ad8301",
        keyword="#66800b", function="#bc5215", type="#ad8301", variable="#205ea6",
        tag="#205ea6", attr="#ad8301", punct="#6f6e69", invalid="#af3029",
        inserted="#66800b", deleted="#af3029", changed="#ad8301", heading="#bc5215",
    ),
}

SCOPES = [  # (name, scope, color key, font style)
    ("Comment", "comment, punctuation.definition.comment", "comment", "italic"),
    ("String", "string, string.quoted, punctuation.definition.string", "string", ""),
    ("Escape", "constant.character.escape, string.regexp", "constant", ""),
    ("Number", "constant.numeric", "number", ""),
    ("Constant", "constant.language, constant.other, support.constant, variable.other.constant", "constant", ""),
    ("Keyword", "keyword, storage, storage.type, storage.modifier, keyword.operator.word", "keyword", ""),
    ("Operator", "keyword.operator", "punct", ""),
    ("Function", "entity.name.function, support.function, meta.function-call variable.function, variable.function", "function", ""),
    ("Type", "entity.name.type, entity.name.class, support.type, support.class, entity.other.inherited-class", "type", ""),
    ("Variable", "variable, variable.parameter, variable.other", "variable", ""),
    ("Language variable", "variable.language", "keyword", "italic"),
    ("Tag", "entity.name.tag", "tag", ""),
    ("Attribute", "entity.other.attribute-name", "attr", ""),
    ("Punctuation", "punctuation, meta.brace", "punct", ""),
    ("Invalid", "invalid", "invalid", ""),
    ("Inserted", "markup.inserted, meta.diff.header.to-file", "inserted", ""),
    ("Deleted", "markup.deleted, meta.diff.header.from-file", "deleted", ""),
    ("Changed", "markup.changed, meta.diff.range", "changed", ""),
    ("Heading", "markup.heading, entity.name.section", "heading", "bold"),
    ("Bold", "markup.bold", "fg", "bold"),
    ("Italic", "markup.italic", "fg", "italic"),
    ("Link", "markup.underline.link", "variable", "underline"),
    ("Inline code", "markup.raw, markup.inline.raw", "string", ""),
]


def kv(key, val, indent):
    return f"{indent}<key>{key}</key>\n{indent}<string>{escape(val)}</string>\n"


def render(t):
    out = ['<?xml version="1.0" encoding="UTF-8"?>\n',
           '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
           '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n',
           '<plist version="1.0">\n<dict>\n',
           kv("name", t["name"], "\t"), "\t<key>settings</key>\n\t<array>\n",
           "\t\t<dict>\n\t\t\t<key>settings</key>\n\t\t\t<dict>\n"]
    for k, c in (("background", "bg"), ("foreground", "fg"), ("caret", "fg"),
                 ("selection", "sel"), ("lineHighlight", "line")):
        out.append(kv(k, t[c], "\t\t\t\t"))
    out.append("\t\t\t</dict>\n\t\t</dict>\n")
    for name, scope, color, style in SCOPES:
        out += ["\t\t<dict>\n", kv("name", name, "\t\t\t"), kv("scope", scope, "\t\t\t"),
                "\t\t\t<key>settings</key>\n\t\t\t<dict>\n", kv("foreground", t[color], "\t\t\t\t")]
        if style:
            out.append(kv("fontStyle", style, "\t\t\t\t"))
        out.append("\t\t\t</dict>\n\t\t</dict>\n")
    out.append("\t</array>\n</dict>\n</plist>\n")
    return "".join(out)


if __name__ == "__main__":
    dst = Path(__file__).resolve().parent.parent / "codex"
    for slug, t in THEMES.items():
        (dst / f"{slug}.tmTheme").write_text(render(t))
