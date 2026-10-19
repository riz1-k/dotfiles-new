<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>name</key>
	<string>Rice</string>
	<key>settings</key>
	<array>
		<dict>
			<key>settings</key>
			<dict>
				<key>background</key>
				<string>{{ background }}</string>
				<key>foreground</key>
				<string>{{ foreground }}</string>
				<key>caret</key>
				<string>{{ foreground }}</string>
				<key>selection</key>
				<string>{{ selection_background }}</string>
				<key>lineHighlight</key>
				<string>{{ ui_surface }}</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Comment</string>
			<key>scope</key>
			<string>comment, punctuation.definition.comment</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ muted }}</string>
				<key>fontStyle</key>
				<string>italic</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>String</string>
			<key>scope</key>
			<string>string, string.quoted, punctuation.definition.string</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ green }}</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Escape</string>
			<key>scope</key>
			<string>constant.character.escape, string.regexp</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ bright_yellow }}</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Number</string>
			<key>scope</key>
			<string>constant.numeric</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ orange }}</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Constant</string>
			<key>scope</key>
			<string>constant.language, constant.other, support.constant, variable.other.constant</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ bright_yellow }}</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Keyword</string>
			<key>scope</key>
			<string>keyword, storage, storage.type, storage.modifier, keyword.operator.word</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ magenta }}</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Operator</string>
			<key>scope</key>
			<string>keyword.operator</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ ui_dim }}</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Function</string>
			<key>scope</key>
			<string>entity.name.function, support.function, meta.function-call variable.function, variable.function</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ blue }}</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Type</string>
			<key>scope</key>
			<string>entity.name.type, entity.name.class, support.type, support.class, entity.other.inherited-class</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ yellow }}</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Variable</string>
			<key>scope</key>
			<string>variable, variable.parameter, variable.other</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ foreground }}</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Language variable</string>
			<key>scope</key>
			<string>variable.language</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ magenta }}</string>
				<key>fontStyle</key>
				<string>italic</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Tag</string>
			<key>scope</key>
			<string>entity.name.tag</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ red }}</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Attribute</string>
			<key>scope</key>
			<string>entity.other.attribute-name</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ yellow }}</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Punctuation</string>
			<key>scope</key>
			<string>punctuation, meta.brace</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ ui_dim }}</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Invalid</string>
			<key>scope</key>
			<string>invalid</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ red }}</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Inserted</string>
			<key>scope</key>
			<string>markup.inserted, meta.diff.header.to-file</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ green }}</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Deleted</string>
			<key>scope</key>
			<string>markup.deleted, meta.diff.header.from-file</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ red }}</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Changed</string>
			<key>scope</key>
			<string>markup.changed, meta.diff.range</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ yellow }}</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Heading</string>
			<key>scope</key>
			<string>markup.heading, entity.name.section</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ accent }}</string>
				<key>fontStyle</key>
				<string>bold</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Bold</string>
			<key>scope</key>
			<string>markup.bold</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ foreground }}</string>
				<key>fontStyle</key>
				<string>bold</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Italic</string>
			<key>scope</key>
			<string>markup.italic</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ foreground }}</string>
				<key>fontStyle</key>
				<string>italic</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Link</string>
			<key>scope</key>
			<string>markup.underline.link</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ foreground }}</string>
				<key>fontStyle</key>
				<string>underline</string>
			</dict>
		</dict>
		<dict>
			<key>name</key>
			<string>Inline code</string>
			<key>scope</key>
			<string>markup.raw, markup.inline.raw</string>
			<key>settings</key>
			<dict>
				<key>foreground</key>
				<string>{{ green }}</string>
			</dict>
		</dict>
	</array>
</dict>
</plist>
