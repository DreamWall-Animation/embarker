import re
from PySide6 import QtWidgets, QtCore, QtGui
from keyword import kwlist
from embarker.api import EmbarkerDockWidget
from embarker import preferences


PLUGIN_NAME = 'PythonConsole'
__version__ = '1.0'
__author__ = 'David Williams'


class ScriptEditorDock(EmbarkerDockWidget):
    TITLE = 'Python console'
    DOCK_AREA = QtCore.Qt.LeftDockWidgetArea
    OBJECT_NAME = 'ScriptsEditor'
    APPEARANCE_PRIORITY = 98
    VISIBLE_BY_DEFAULT = False
    ENABLE_DURING_PLAYBACK = True

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.scripteditor = ScriptsPanel()
        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.scripteditor)


UI_CLASSES = [ScriptEditorDock]

def ctrl_pressed():
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    return modifiers == (modifiers | QtCore.Qt.ControlModifier)


def shift_pressed():
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    return modifiers == (modifiers | QtCore.Qt.ShiftModifier)


def alt_pressed():
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    return modifiers == (modifiers | QtCore.Qt.AltModifier)


KEYWORDS = [f"\\b{w}\\b" for w in kwlist]


def _get_console_font():
    font = QtGui.QFont()
    font.setFamily('Consolas')
    font.setPixelSize(14)
    return font


def is_structure_definer(line):
    patterns = [
        r"^\s*def\s+.*:",
        r"^\s*class\s+.*:",
        r"^\s*while\s+.*:",
        r"^\s*if\s+.*:",
        r"^\s*elif\s+.*:",
        r"^\s*else\s*:",
        r"^\s*with\s+.*:",
        r"^\s*match\s+.*:",
        r"^\s*case\s+.*:",
        r"^\s*for\s+.*\s+in\s+.*:",
    ]
    combined_pattern = "|".join(patterns)
    return re.match(combined_pattern, line) is not None


class PythonHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        self.highlighting_rules = []

        keyword_format = QtGui.QTextCharFormat()
        keyword_format.setForeground(QtCore.Qt.yellow)
        font = _get_console_font()
        font.setBold(True)
        keyword_format.setFont(font)
        for keyword in KEYWORDS:
            pattern = QtCore.QRegularExpression(keyword)
            self.highlighting_rules.append((pattern, keyword_format))

        comment_format = QtGui.QTextCharFormat()
        comment_format.setForeground(QtCore.Qt.darkGreen)
        comment_pattern = QtCore.QRegularExpression("#[^\n]*")
        self.highlighting_rules.append((comment_pattern, comment_format))

        string_format = QtGui.QTextCharFormat()
        color = QtGui.QColor('#a67c00')
        string_format.setForeground(color)
        font = _get_console_font()
        font.setItalic(True)
        string_format.setFont(font)
        string_patterns = [
            QtCore.QRegularExpression("\"([^\"]*?)\""),
            QtCore.QRegularExpression("\'([^\']*?)\'"),]
        for pattern in string_patterns:
            self.highlighting_rules.append((pattern, string_format))

        self.triple_quote_format = QtGui.QTextCharFormat()
        self.triple_quote_format.setForeground(QtGui.QColor('#a67c00'))
        self.triple_single_pattern = r"'''"
        self.triple_double_pattern = r'"""'

    def highlightBlock(self, text):
        for pattern, format_ in self.highlighting_rules:
            expression = pattern.globalMatch(text)
            while expression.hasNext():
                match = expression.next()
                start = match.capturedStart()
                length = match.capturedLength()
                self.setFormat(start, length, format_)

        self.highlight_multiline(
            text, self.triple_single_pattern, self.triple_quote_format)
        self.highlight_multiline(
            text, self.triple_double_pattern, self.triple_quote_format)

    def highlight_multiline(self, text, delimiter, fmt):
        in_multiline = self.previousBlockState() == 1

        start = 0
        if not in_multiline:
            start = text.find(delimiter)

        while start >= 0:
            if in_multiline:
                end = text.find(delimiter, start)
                if end == -1:
                    self.setFormat(start, len(text) - start, fmt)
                    self.setCurrentBlockState(1)
                    return
                else:
                    self.setFormat(start, end - start + len(delimiter), fmt)
                    start = text.find(delimiter, end + len(delimiter))
                    in_multiline = False
            else:
                end = text.find(delimiter, start + len(delimiter))
                if end == -1:
                    self.setFormat(start, len(text) - start, fmt)
                    self.setCurrentBlockState(1)
                    return
                else:
                    self.setFormat(start, end - start + len(delimiter), fmt)
                    start = text.find(delimiter, end + len(delimiter))

        self.setCurrentBlockState(0)


class LineNumberArea(QtWidgets.QWidget):
    def __init__(self, editor):
        super(LineNumberArea, self).__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QtCore.QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.code_editor.paint_line_number(event)


class ScriptEditor(QtWidgets.QPlainTextEdit):
    execute_code = QtCore.Signal(str)

    def __init__(
            self, executable=True, auto_fit_height=False,
            indent=0, line_count_start=1, parent=None):
        super().__init__(parent)
        self.setCursorWidth(5)
        self.auto_fit_height = auto_fit_height
        self.indent = indent
        self.line_count_start = line_count_start
        self.executable = executable
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.setFont(_get_console_font())
        self.highlighter = PythonHighlighter(self.document())
        self.history = []
        self.index = 0

        self.line_numbers = LineNumberArea(self)

        self.blockCountChanged.connect(self.update_line_number_width)
        self.updateRequest.connect(self.update_line_number)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.update_line_number_width(0)

        if auto_fit_height:
            self.textChanged.connect(self.adjust_height)
            self.adjust_height()

    def set_code(self, code):
        # Remove indent.
        if self.indent:
            code = '\n'.join([
                line[self.indent:] if
                line.startswith(' ' * self.indent) else line
                for line in code.split('\n')])
        self.setPlainText(code)
        if self.auto_fit_height:
            self.adjust_height()

    def adjust_height(self):
        line_count = self.document().blockCount() + 2
        font_metrics = self.fontMetrics()
        line_height = font_metrics.lineSpacing()

        # Calculer la hauteur totale en ajoutant les marges
        document_height = line_height * line_count + self.frameWidth() * 2
        self.setFixedHeight(document_height)

    def sizeHint(self):
        return QtCore.QSize(
            self.width(),
            self.document().size().height() + self.frameWidth() * 2 + 2)

    def set_cursor_at_block_start(self, cursor):
        block = cursor.block()
        text = block.text()
        start = block.position()
        position = start + (len(text) - len(text.lstrip(' ')))
        mode = (
            QtGui.QTextCursor.KeepAnchor if shift_pressed() else
            QtGui.QTextCursor.MoveAnchor)
        if position < cursor.position():
            cursor.setPosition(position, mode)
        else:
            cursor.setPosition(start, mode)
        self.setTextCursor(cursor)

    def backspace(self, event, cursor):
        cursor.movePosition(
            QtGui.QTextCursor.StartOfBlock,
            QtGui.QTextCursor.KeepAnchor)
        text_before_cursor = cursor.selectedText()

        if not text_before_cursor.isspace():
            super().keyPressEvent(event)
            return

        remainder = len(text_before_cursor) % 4
        cursor.movePosition(QtGui.QTextCursor.StartOfBlock)
        cursor.movePosition(
            QtGui.QTextCursor.Right,
            QtGui.QTextCursor.KeepAnchor,
            remainder or 4)
        cursor.removeSelectedText()

    def move_line_down(self, cursor: QtGui.QCursor):
        # Retrieve cursor position in current line.
        cursor.movePosition(
            QtGui.QTextCursor.StartOfBlock,
            QtGui.QTextCursor.KeepAnchor)
        position_in_line = len(cursor.selectedText())
        # Delete current line.
        cursor.movePosition(QtGui.QTextCursor.StartOfBlock)
        cursor.movePosition(
            QtGui.QTextCursor.EndOfBlock, QtGui.QTextCursor.KeepAnchor)
        cursor.setPosition(
            cursor.position() + 1,
            QtGui.QTextCursor.KeepAnchor)
        current_block_text = cursor.selectedText()
        cursor.removeSelectedText()
        # Insert line below.
        cursor.movePosition(QtGui.QTextCursor.Down)
        cursor.movePosition(QtGui.QTextCursor.StartOfBlock)
        cursor.insertText(current_block_text)
        # Retrieve cursor position.
        cursor.movePosition(QtGui.QTextCursor.StartOfBlock)
        cursor.movePosition(QtGui.QTextCursor.Up)
        cursor.setPosition(cursor.position() + position_in_line)
        self.setTextCursor(cursor)

    def move_line_up(self, cursor):
        if cursor.blockNumber() == 0:
            return
        # Retrieve cursor position in current line.
        cursor.movePosition(
            QtGui.QTextCursor.StartOfBlock,
            QtGui.QTextCursor.KeepAnchor)
        position_in_line = len(cursor.selectedText())
        # Delete current line.
        cursor.movePosition(QtGui.QTextCursor.StartOfBlock)
        cursor.movePosition(
            QtGui.QTextCursor.EndOfBlock, QtGui.QTextCursor.KeepAnchor)
        cursor.setPosition(
            cursor.position() + 1,
            QtGui.QTextCursor.KeepAnchor)
        current_block_text = cursor.selectedText()
        cursor.removeSelectedText()
        # Insert line below.
        cursor.movePosition(QtGui.QTextCursor.Up)
        cursor.movePosition(QtGui.QTextCursor.StartOfBlock)
        cursor.insertText(current_block_text)
        # Retrieve cursor position.
        cursor.movePosition(QtGui.QTextCursor.StartOfBlock)
        cursor.movePosition(QtGui.QTextCursor.Up)
        cursor.setPosition(cursor.position() + position_in_line)
        self.setTextCursor(cursor)

    def duplicate_line(self, cursor, up=True):
        start_position = cursor.position()
        cursor.movePosition(QtGui.QTextCursor.StartOfBlock)
        cursor.beginEditBlock()
        text = f'{cursor.block().text()}\n'
        cursor.insertText(text)
        cursor.endEditBlock()
        position = start_position if up else (start_position + len(text))
        cursor.setPosition(position)
        self.setTextCursor(cursor)

    def keyPressEvent(self, event):
        if self.executable:
            if event.key() == QtCore.Qt.Key_Return and ctrl_pressed():
                return self.execute()
            if event.key() == QtCore.Qt.Key_Enter and ctrl_pressed():
                return self.execute()
            if event.key() == QtCore.Qt.Key_Up and ctrl_pressed():
                return self.set_previous_snippet()
            if event.key() == QtCore.Qt.Key_Down and ctrl_pressed():
                return self.set_next_snippet()

        pairs = {'(': ')', '{': '}', '[': ']', '\'': '\'', '"': '"'}
        cursor = self.textCursor()
        next_char = self.toPlainText()[cursor.position():cursor.position() + 1]

        if event.key() == QtCore.Qt.Key_Backspace:
            return self.backspace(event, cursor)

        if event.key() == QtCore.Qt.Key_Home:
            return self.set_cursor_at_block_start(cursor)

        if event.text() in pairs.values() and next_char == event.text():
            cursor.movePosition(QtGui.QTextCursor.NextCharacter)
            self.setTextCursor(cursor)
            return

        if event.text() in pairs and is_cursor_at_end_of_block(cursor):
            opening_char = event.text()
            closing_char = pairs[opening_char]
            cursor.insertText(opening_char + closing_char)
            cursor.movePosition(QtGui.QTextCursor.Left)
            self.setTextCursor(cursor)
            return

        if event.key() == QtCore.Qt.Key_Up:
            if shift_pressed() and alt_pressed():
                return self.duplicate_line(cursor)
            elif alt_pressed():
                return self.move_line_up(cursor)

        if event.key() == QtCore.Qt.Key_Down:
            if shift_pressed() and alt_pressed():
                return self.duplicate_line(cursor, False)
            elif alt_pressed():
                return self.move_line_down(cursor)

        if event.key() == QtCore.Qt.Key_X and ctrl_pressed():
            if not cursor.hasSelection():
                return self.copy_line(cursor, cut=True)

        if event.key() == QtCore.Qt.Key_C and ctrl_pressed():
            if not cursor.hasSelection():
                return self.copy_line(cursor)

        if event.key() == QtCore.Qt.Key_Backtab:
            return self.unindent_selected_lines()

        if event.key() == QtCore.Qt.Key_Tab:
            if self.textCursor().hasSelection():
                return self.indent_selected_lines()
            return self.textCursor().insertText('    ')

        if event.key() == QtCore.Qt.Key_Return:
            return self.auto_indent()

        return super().keyPressEvent(event)

    def copy_line(self, cursor, cut=False):
        cursor.select(QtGui.QTextCursor.BlockUnderCursor)
        clipboard = QtGui.QGuiApplication.clipboard()
        clipboard.setText(cursor.selectedText())
        if not cut:
            return
        cursor.removeSelectedText()
        cursor.movePosition(QtGui.QTextCursor.EndOfBlock)
        self.setTextCursor(cursor)

    def indent_selected_lines(self):
        cursor = self.textCursor()
        selection = cursor.selection()
        selection_start = cursor.selectionStart()
        selection_end = cursor.selectionEnd()

        selected_text = selection.toPlainText()
        lines = selected_text.split("\n")

        indented_lines = ['    ' + line for line in lines]
        indented_text = "\n".join(indented_lines)

        cursor.beginEditBlock()
        cursor.insertText(indented_text)
        cursor.endEditBlock()

        cursor.setPosition(selection_start)
        cursor.setPosition(
            selection_end + (len(lines) * 4),
            QtGui.QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)

    def unindent_selected_lines(self):
        cursor = self.textCursor()
        selection = cursor.selection()
        selection_start = cursor.selectionStart()
        selection_end = cursor.selectionEnd()

        selected_text = selection.toPlainText()
        lines = selected_text.split("\n")

        unindented_lines = [
            line[4:] if line.startswith('    ') else line for line in lines]
        unindented_text = "\n".join(unindented_lines)

        cursor.beginEditBlock()
        cursor.insertText(unindented_text)
        cursor.endEditBlock()

        cursor.setPosition(selection_start)
        cursor.setPosition(
            selection_end - (len(lines) * 4),
            QtGui.QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)

    def get_current_line(self):
        cursor = self.textCursor()
        cursor.select(QtGui.QTextCursor.LineUnderCursor)
        return cursor.selectedText()

    def auto_indent(self):
        cursor = self.textCursor()
        current_line = self.get_current_line()
        leading_spaces = len(current_line) - len(current_line.lstrip(" "))
        if is_structure_definer(current_line):
            leading_spaces += 4
        cursor.insertText("\n" + " " * leading_spaces)

    def set_next_snippet(self):
        if not self.history:
            return
        self.index += 1
        if self.index >= len(self.history):
            self.index = 0
        self.setPlainText(self.history[self.index])

    def set_previous_snippet(self):
        if not self.history:
            return
        self.index -= 1
        if self.index < 0:
            self.index = len(self.history) - 1
        self.setPlainText(self.history[self.index])

    def execute(self, code=None):
        self.update_history()
        if not code:
            selected_code = self.textCursor().selectedText()
            if not selected_code:
                code = self.toPlainText()
                self.clear()
            else:
                code = selected_code

        code = code.replace('\u2029', '\n')
        if not code.strip(' \n'):
            return
        if len(code.split('\n')) == 1:
            try:
                result = eval(code, globals())
                if not code.startswith('print('):
                    print(f'# {result}')
            except SyntaxError:
                exec(code, globals())
        else:
            exec(code, globals())

    def update_history(self):
        content = self.toPlainText()
        if content in self.history:
            return
        self.history.append(content)
        if len(self.history) > 200:
            self.history.pop(0)

    def code(self):
        indent = ' ' * self.indent
        return indent + f'\n{indent}'.join(self.toPlainText().split('\n'))

    def line_number_width(self):
        digits = 1
        max_num = max(digits, self.blockCount() + (self.line_count_start - 1))
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = 3 + self.fontMetrics().horizontalAdvance('16') * digits
        return space

    def update_line_number_width(self, _):
        self.setViewportMargins(self.line_number_width(), 0, 0, 0)

    def update_line_number(self, rect, dy):
        if dy:
            self.line_numbers.scroll(0, dy)
        else:
            self.line_numbers.update(
                0, rect.y(), self.line_numbers.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        content = self.contentsRect()
        rect = QtCore.QRect(
            content.left(),
            content.top(),
            self.line_number_width(),
            content.height())
        self.line_numbers.setGeometry(rect)

    def paint_line_number(self, event):
        painter = QtGui.QPainter(self.line_numbers)
        color = QtGui.QColor('#222222')
        painter.fillRect(event.rect(), color)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber() + self.line_count_start - 1
        top = self.blockBoundingGeometry(block).translated(
            self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        font = QtGui.QFont('Terminal')
        font.setBold(True)
        painter.setPen(QtGui.QPen('#EEEEEE'))
        painter.setFont(font)
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(
                    0, top,
                    self.line_numbers.width(),
                    self.fontMetrics().height(),
                    QtCore.Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def set_line_offset(self, offset=0):
        self.line_count_start = offset
        self.repaint()

    def highlight_current_line(self):
        extra_selection = []

        if not self.isReadOnly():
            selection = QtWidgets.QTextEdit.ExtraSelection()
            line_color = QtGui.QColor(QtCore.Qt.yellow).lighter(200)
            line_color.setAlpha(20)
            selection.format.setBackground(line_color)
            selection.format.setProperty(
                QtGui.QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selection.append(selection)

        self.setExtraSelections(extra_selection)

    def insert_pair(self, opening_char, closing_char):
        cursor = self.textCursor()

        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            cursor.insertText(f"{opening_char}{selected_text}{closing_char}")
        else:
            cursor.insertText(f"{opening_char}{closing_char}")
            cursor.movePosition(QtGui.QTextCursor.Left)

        self.setTextCursor(cursor)


def execute_and_return_last_value(code, context):
    lines = code.strip().split('\n')

    for line in lines[:-1]:
        exec(line, context)

    last_line = lines[-1].strip()
    if last_line:
        try:
            result = eval(last_line, context)
            return result
        except BaseException:
            exec(last_line, context)
            return None


def is_cursor_at_end_of_block(cursor):
    block = cursor.block()
    block_text = block.text()
    position_in_block = cursor.position() - block.position()
    return position_in_block == len(block_text)


class ScriptsPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Free string id to define where to save temp code.
        self.tab = QtWidgets.QTabWidget()
        self.tab.setTabsClosable(True)

        tabbar = RightClickTabBar()
        tabbar.right_clicked.connect(self.tabbar_context_menu)

        self.tab.setTabBar(tabbar)
        self.tab.setTabsClosable(True)
        self.tab.setMovable(True)
        self.tab.tabBar().tabBarDoubleClicked.connect(self.change_title)
        self.tab.currentChanged.connect(self.save_scripts)
        self.tab.tabCloseRequested.connect(self.remove_tab)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tab)

        self.restore_tabs()
        QtWidgets.QApplication.instance().aboutToQuit.connect(
            self.save_scripts)

    def remove_tab(self, index):
        if self.tab.count() > 1:
            self.tab.removeTab(index)
        self.save_scripts()

    def save_scripts(self, *_):
        data = {
            self.tab.tabText(i): self.tab.widget(i).code()
            for i in range(self.tab.count())}
        preferences.set('scripts', data)

    def tabbar_context_menu(self, global_pos):
        action = QtGui.QAction('New script', self)
        menu = QtWidgets.QMenu()
        menu.addAction(action)

        clicked_action = menu.exec_(global_pos)
        if not clicked_action:
            return

        title, operate = QtWidgets.QInputDialog.getText(
            None, 'Add script', 'Title', text='New script')
        if not operate or not title:
            return
        title = _unique_name(title, self.script_names())
        script_editor = ScriptEditor()
        script_editor.execute_code.connect(self.save_scripts)
        self.tab.addTab(script_editor, title)
        self.tab.setCurrentIndex(self.tab.count() - 1)

    def change_title(self, index=None):
        index = self.tab.currentIndex() if type(index) is not int else index
        if index < 0:
            return
        title, operate = QtWidgets.QInputDialog.getText(
            None, 'Change picker title', 'New title',
            text=self.tab.tabText(index))

        if not operate:
            return
        self.tab.setTabText(index, _unique_name(title, self.script_names()))

    def script_names(self):
        return [self.tab.tabText(i) for i in range(self.tab.count())]

    def restore_tabs(self):
        scripts = preferences.get('scripts', {'New script': ''})
        self.tab.blockSignals(True)
        name = 'Script Editor'
        for name, code in scripts.items():
            script_editor = ScriptEditor()
            script_editor.execute_code.connect(self.save_scripts)
            script_editor.set_code(code)
            self.tab.addTab(script_editor, name)
        if not self.tab.count():
            script_editor = ScriptEditor()
            script_editor.execute_code.connect(self.save_scripts)
            self.tab.addTab(script_editor, name)
        self.tab.blockSignals(False)


def _unique_name(name, names):
    base = name
    i = 0
    while name in names:
        i += 1
        name = f'{base}-{i}'
    return name


class RightClickTabBar(QtWidgets.QTabBar):
    right_clicked = QtCore.Signal(QtCore.QPoint)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            # tab_index = self.tabAt(event.pos())
            global_pos = self.mapToGlobal(event.pos())
            self.right_clicked.emit(global_pos)
        return super().mousePressEvent(event)

