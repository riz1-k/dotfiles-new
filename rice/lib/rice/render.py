"""Template rendering with Omarchy's placeholder syntax (basecamp/omarchy, MIT).

  {{ key }}  {{ key_strip }}  {{ key_rgb }}
  {{ mix a b 30% }}  {{ mix_strip a b 0.3 }}  {{ mix_rgb a b 30 }}
  {{ hypr_gradient key [fallback] }}  {{ gradient_start key [fallback] }}  {{ shell_gradient key [fallback] }}

The scan matches omarchy-theme-set-templates' awk renderer byte for byte: each
`{{ ... }}` span is looked up whole, an unknown span is left as it is, and lines
keep their own endings.
"""
import os
import re

from . import colormath as cm
from . import palette

MIX = re.compile(r"\{\{\s*(mix(?:_strip|_rgb)?)\s+([A-Za-z0-9_]+)\s+([A-Za-z0-9_]+)\s+([0-9]+(?:\.[0-9]+)?%?)\s*\}\}")
GRADIENT = re.compile(r"\{\{\s*(hypr_gradient|gradient_start|shell_gradient)\s+([^}]+)\s*\}\}")
ANGLE = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?deg$")


class Renderer:
    def __init__(self, colors, extra=None):
        self.colors = dict(colors)
        if extra:
            self.colors.update(extra)
        self.values = palette.template_values(self.colors)
        self._cache = {}

    # -- functions -------------------------------------------------------------

    def _function(self, token):
        if token in self._cache:
            return self._cache[token]
        value = None
        m = MIX.fullmatch(token)
        if m:
            fn, a, b, amount = m.groups()
            start, end = self.colors.get(a, ""), self.colors.get(b, "")
            if cm.is_hex(start) and cm.is_hex(end):
                value = cm.mix(start, end, amount)
                if fn == "mix_strip":
                    value = value[1:]
                elif fn == "mix_rgb":
                    value = cm.rgb_string(value)
        else:
            m = GRADIENT.fullmatch(token)
            if m:
                parts = m.group(2).split(None, 2)
                key = parts[0] if parts else ""
                fallback = parts[1] if len(parts) > 1 else ""
                if len(parts) > 2:
                    fallback = f"{parts[1]} {parts[2]}"
                value = getattr(self, "_" + m.group(1))(key, fallback)
        self._cache[token] = value
        return value

    def _ref(self, ref, fallback):
        if ref in self.colors:
            return self.colors[ref]
        if fallback and fallback in self.colors:
            return self.colors[fallback]
        return fallback or ref

    def _gradient(self, spec):
        colors, angle = [], ""
        for part in spec.split():
            if ANGLE.match(part):
                angle = part[:-3]
            else:
                part = part.strip()
                colors.append(self.colors.get(part, part))
        return colors, angle

    def _shell_hex(self, color):
        color = self.colors.get(color.strip(), color.strip())
        if re.fullmatch(r"#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?", color):
            return color[:7]
        m = re.fullmatch(r"[Rr][Gg][Bb][Aa]?\(([0-9A-Fa-f]{6})([0-9A-Fa-f]{2})?\)", color)
        if m:
            return "#" + m.group(1)
        m = re.fullmatch(r"[Rr][Gg][Bb][Aa]?\(([0-9]+),([0-9]+),([0-9]+)(,[0-9.]+)?\)", color)
        if m:
            return "#%02x%02x%02x" % tuple(min(int(m.group(i)), 255) for i in (1, 2, 3))
        if re.fullmatch(r"0x[0-9A-Fa-f]{8}", color):
            return "#" + color[4:10]
        return color

    def _hypr_gradient(self, key, fallback):
        spec = self._ref(key, fallback)
        colors, angle = self._gradient(spec)
        if not colors:
            return f'"{spec}"'
        if len(colors) == 1:
            return f'"{colors[0]}"'
        value = "{ colors = {" + ",".join(f' "{c}"' for c in colors) + " }"
        if angle:
            value += f", angle = {angle}"
        return value + " }"

    def _gradient_start(self, key, fallback):
        spec = self._ref(key, fallback)
        colors, _ = self._gradient(spec)
        return self._shell_hex(colors[0] if colors else spec)

    def _shell_gradient(self, key, fallback):
        spec = self._ref(key, fallback)
        colors, angle = self._gradient(spec)
        if not colors:
            return spec
        return " ".join(colors) + (f" {angle}deg" if angle else "")

    # -- scanning --------------------------------------------------------------

    def line(self, line):
        out = []
        while True:
            open_ = line.find("{{")
            if open_ < 0:
                break
            close = line.find("}}", open_ + 2)
            if close < 0:
                break
            token = line[open_:close + 2]
            value = self.values.get(token)
            if value is None:
                value = self._function(token)
            if value is not None:
                out.append(line[:open_] + value)
                line = line[open_ + len(token):]
            else:
                out.append(line[:open_ + 1])
                line = line[open_ + 1:]
        out.append(line)
        return "".join(out)

    def text(self, text):
        return "".join(self.line(l) for l in text.splitlines(keepends=True))


def template_files(*dirs):
    files = []
    for d in dirs:
        if d.is_dir():
            files.extend(sorted(p for p in d.iterdir() if p.name.endswith(".tpl") and p.is_file()))
    return files


def render_into(out_dir, colors, templates, extra=None):
    """Render each template into out_dir. The first template for an output name wins
    (user templates come first), and a file the theme already ships is never
    overwritten. Returns the output names written."""
    renderer = Renderer(colors, extra)
    written = []
    seen = set()
    for tpl in templates:
        name = tpl.name[:-4]
        if name in seen or (out_dir / name).exists() or (out_dir / name).is_symlink():
            continue
        seen.add(name)
        data = renderer.text(tpl.read_text(errors="replace"))
        tmp = out_dir / f".{name}.tmp"
        tmp.write_text(data)
        os.replace(tmp, out_dir / name)
        written.append(name)
    return written
