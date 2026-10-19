# {{ rice_theme_name }} (rice template, from theme-sync's Vesper file)
# vim:fileencoding=utf-8:foldmethod=marker

# : Manager {{{

[mgr]
cwd = { fg = "{{ accent }}" }

# Find
find_keyword  = { fg = "{{ ui_warning }}", bold = true, italic = true, underline = true }
find_position = { fg = "{{ bright_magenta }}", bg = "reset", bold = true, italic = true }

# Marker
marker_copied   = { fg = "{{ ui_success }}", bg = "{{ ui_success }}" }
marker_cut      = { fg = "{{ ui_danger }}", bg = "{{ ui_danger }}" }
marker_marked   = { fg = "{{ ui_success }}", bg = "{{ ui_success }}" }
marker_selected = { fg = "{{ ui_warning }}", bg = "{{ ui_warning }}" }

# Count
count_copied   = { fg = "{{ background }}", bg = "{{ ui_success }}" }
count_cut      = { fg = "{{ background }}", bg = "{{ ui_danger }}" }
count_selected = { fg = "{{ background }}", bg = "{{ ui_warning }}" }

# Border
border_symbol = "│"
border_style  = { fg = "{{ ui_border }}" }

# : }}}


# : Tabs {{{

[tabs]
active   = { fg = "{{ background }}", bg = "{{ accent }}", bold = true }
inactive = { fg = "{{ muted }}", bg = "{{ ui_surface }}" }

# : }}}


# : Mode {{{

[mode]

normal_main = { fg = "{{ background }}", bg = "{{ accent }}", bold = true }
normal_alt  = { fg = "{{ accent }}", bg = "{{ selection }}" }

# Select mode
select_main = { fg = "{{ background }}", bg = "{{ ui_success }}", bold = true }
select_alt  = { fg = "{{ ui_success }}", bg = "{{ selection }}" }

# Unset mode
unset_main = { fg = "{{ background }}", bg = "{{ ui_warning }}", bold = true }
unset_alt  = { fg = "{{ ui_warning }}", bg = "{{ selection }}" }

# : }}}


# : Status bar {{{

[status]
# Permissions
perm_sep   = { fg = "{{ muted }}" }
perm_type  = { fg = "{{ accent }}" }
perm_read  = { fg = "{{ ui_warning }}" }
perm_write = { fg = "{{ ui_danger }}" }
perm_exec  = { fg = "{{ ui_success }}" }

# Progress
progress_label  = { fg = "{{ foreground }}", bold = true }
progress_normal = { fg = "{{ ui_success }}", bg = "{{ selection }}" }
progress_error  = { fg = "{{ ui_warning }}", bg = "{{ ui_danger }}" }

# : }}}


# : Pick {{{

[pick]
border   = { fg = "{{ accent }}" }
active   = { fg = "{{ bright_magenta }}", bold = true }
inactive = {}

# : }}}


# : Input {{{

[input]
border   = { fg = "{{ accent }}" }
title    = {}
value    = {}
selected = { reversed = true }

# : }}}


# : Completion {{{

[cmp]
border = { fg = "{{ accent }}" }

# : }}}


# : Tasks {{{

[tasks]
border  = { fg = "{{ accent }}" }
title   = {}
hovered = { fg = "{{ bright_magenta }}", bold = true }

# : }}}


# : Which {{{

[which]
border          = { fg = "{{ accent }}" }
cand            = { fg = "{{ ui_success }}" }
rest            = { fg = "{{ ui_faint }}" }
desc            = { fg = "{{ bright_magenta }}" }
separator       = "  "
separator_style = { fg = "{{ muted }}" }

# : }}}


# : Help {{{

[help]
on      = { fg = "{{ ui_success }}" }
run     = { fg = "{{ bright_magenta }}" }
hovered = { reversed = true, bold = true }
footer  = { fg = "{{ background }}", bg = "{{ foreground }}" }

# : }}}


# : Spotter {{{

[spot]
border   = { fg = "{{ accent }}" }
title    = { fg = "{{ accent }}" }
tbl_col  = { fg = "{{ ui_success }}" }
tbl_cell = { fg = "{{ bright_magenta }}", bg = "{{ selection }}" }

# : }}}


# : Notification {{{

[notify]
title_info  = { fg = "{{ ui_success }}" }
title_warn  = { fg = "{{ ui_warning }}" }
title_error = { fg = "{{ ui_danger }}" }

# : }}}


# : File-specific styles {{{

[filetype]

rules = [
	# Image
	{ mime = "**/image/*", fg = "{{ ui_success }}" },
	# Media
	{ mime = "**/{audio,video}/*", fg = "{{ ui_warning }}" },
	# Archive
	{ mime = "**/application/{zip,rar,7z*,tar,gzip,xz,zstd,bzip*,lzma,compress,archive,cpio,arj,xar,ms-cab*}", fg = "{{ bright_magenta }}" },
	# Document
	{ mime = "**/application/{pdf,doc,rtf}", fg = "{{ ui_success }}" },
	# Virtual file system
	{ mime = "vfs/{absent,stale}", fg = "{{ ui_faint }}" },
	# Fallback
	{ url = "*", fg = "{{ foreground }}" },
	{ url = "*/", fg = "{{ accent }}" },
]

# : }}}

[icon]

conds = [
	# Special files
	{ if = "orphan", text = "", fg = "{{ foreground }}" },
	{ if = "link", text = "", fg = "{{ muted }}" },
	{ if = "block", text = "", fg = "{{ ui_warning }}" },
	{ if = "char", text = "", fg = "{{ ui_warning }}" },
	{ if = "fifo", text = "", fg = "{{ ui_warning }}" },
	{ if = "sock", text = "", fg = "{{ ui_warning }}" },
	{ if = "sticky", text = "", fg = "{{ ui_warning }}" },
	{ if = "dummy", text = "", fg = "{{ ui_danger }}" },

	# Fallback
	{ if = "dir & hovered", text = "", fg = "{{ accent }}" },
	{ if = "dir", text = "", fg = "{{ accent }}" },
	{ if = "exec", text = "", fg = "{{ ui_success }}" },
	{ if = "!dir", text = "", fg = "{{ foreground }}" },
]
