"""
Native settings window: NSWindow with two tabs (General / Exceptions).
"""

import objc
from AppKit import (
    NSApplication,
    NSBackingStoreBuffered,
    NSBezelStyleRounded,
    NSButton,
    NSButtonTypeSwitch,
    NSColor,
    NSFont,
    NSMakeRect,
    NSMakeSize,
    NSObject,
    NSScrollView,
    NSStackView,
    NSStackViewGravityLeading,
    NSTableColumn,
    NSTableView,
    NSTextField,
    NSTextFieldCell,
    NSUserInterfaceLayoutOrientationVertical,
    NSView,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskResizable,
    NSWindowStyleMaskTitled,
)
from Foundation import NSRect, NSSize

_window = None  # singleton


def open_settings(word_buffer, listener, toggle_item, exceptions: set, on_exceptions_change):
    """Open (or focus) the settings window."""
    global _window
    NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
    if _window and _window.isVisible():
        _window.makeKeyAndOrderFront_(None)
        return
    _window = _SettingsWindow.alloc().initWith_(
        word_buffer=word_buffer,
        listener=listener,
        toggle_item=toggle_item,
        exceptions=exceptions,
        on_exceptions_change=on_exceptions_change,
    )
    _window.makeKeyAndOrderFront_(None)


class _SettingsWindow(NSWindow):

    @objc.python_method
    def initWith_(self, word_buffer, listener, toggle_item, exceptions, on_exceptions_change):
        style = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskMiniaturizable
        )
        self = objc.super(_SettingsWindow, self).initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 420, 320),
            style,
            NSBackingStoreBuffered,
            False,
        )
        if self is None:
            return None

        self.setTitle_('Oopslang Settings')
        self.center()
        self.setReleasedWhenClosed_(False)

        self._listener = listener
        self._toggle_item = toggle_item
        self._exceptions = exceptions
        self._on_exceptions_change = on_exceptions_change
        self._word_buffer = word_buffer

        # --- Tab bar ---
        from AppKit import NSTabView, NSTabViewItem
        tab_view = NSTabView.alloc().initWithFrame_(NSMakeRect(10, 10, 400, 300))

        general_item = NSTabViewItem.alloc().initWithIdentifier_('general')
        general_item.setLabel_('General')
        general_item.setView_(self._make_general_tab(listener, toggle_item))
        tab_view.addTabViewItem_(general_item)

        exc_item = NSTabViewItem.alloc().initWithIdentifier_('exceptions')
        exc_item.setLabel_('Exceptions')
        exc_item.setView_(self._make_exceptions_tab())
        tab_view.addTabViewItem_(exc_item)

        self.contentView().addSubview_(tab_view)
        return self

    @objc.python_method
    def _make_general_tab(self, listener, toggle_item) -> NSView:
        from layout_switcher import switch_layout_tis
        import subprocess
        from pathlib import Path
        from app import _login_agent_installed, _install_login_agent, _uninstall_login_agent

        view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 390, 260))

        # Enabled checkbox
        enabled_cb = NSButton.alloc().initWithFrame_(NSMakeRect(20, 200, 350, 24))
        enabled_cb.setButtonType_(NSButtonTypeSwitch)
        enabled_cb.setTitle_('Enable auto-correction')
        enabled_cb.setState_(1 if listener.is_active() else 0)
        enabled_cb.setTarget_(self)
        enabled_cb.setAction_(objc.selector(
            self.toggleEnabled_,
            signature=b'v@:@',
        ))
        self._enabled_cb = enabled_cb
        view.addSubview_(enabled_cb)

        # Launch at Login checkbox
        login_cb = NSButton.alloc().initWithFrame_(NSMakeRect(20, 165, 350, 24))
        login_cb.setButtonType_(NSButtonTypeSwitch)
        login_cb.setTitle_('Launch at Login')
        login_cb.setState_(1 if _login_agent_installed() else 0)
        login_cb.setTarget_(self)
        login_cb.setAction_(objc.selector(
            self.toggleLogin_,
            signature=b'v@:@',
        ))
        self._login_cb = login_cb
        view.addSubview_(login_cb)

        # Hint label
        hint = NSTextField.alloc().initWithFrame_(NSMakeRect(20, 20, 360, 100))
        hint.setStringValue_(
            'oopslang detects when you type in the wrong keyboard layout '
            'and auto-corrects the word when you press Space or punctuation.'
        )
        hint.setBezeled_(False)
        hint.setDrawsBackground_(False)
        hint.setEditable_(False)
        hint.setSelectable_(False)
        hint.setFont_(NSFont.systemFontOfSize_(12))
        hint.setTextColor_(NSColor.secondaryLabelColor())
        view.addSubview_(hint)

        return view

    def toggleEnabled_(self, sender):
        active = sender.state() == 1
        self._listener.set_active(active)
        self._toggle_item.state = active

    def toggleLogin_(self, sender):
        from app import _login_agent_installed, _install_login_agent, _uninstall_login_agent
        if _login_agent_installed():
            _uninstall_login_agent()
        else:
            _install_login_agent()
        sender.setState_(1 if _login_agent_installed() else 0)

    @objc.python_method
    def _make_exceptions_tab(self) -> NSView:
        view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 390, 260))

        # Table
        scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(20, 50, 350, 195))
        scroll.setHasVerticalScroller_(True)
        scroll.setBorderType_(2)  # NSBezelBorder

        table = NSTableView.alloc().initWithFrame_(NSMakeRect(0, 0, 350, 195))
        col = NSTableColumn.alloc().initWithIdentifier_('word')
        col.setWidth_(330)
        col.headerCell().setStringValue_('Excluded words')
        table.addTableColumn_(col)
        table.setUsesAlternatingRowBackgroundColors_(True)

        self._table = table
        self._exc_list = sorted(self._exceptions)

        self._table_delegate = _ExceptionsDataSource.alloc().initWith_(
            exc_list=self._exc_list,
        )
        table.setDataSource_(self._table_delegate)
        table.setDelegate_(self._table_delegate)

        scroll.setDocumentView_(table)
        view.addSubview_(scroll)

        # Buttons
        add_btn = NSButton.alloc().initWithFrame_(NSMakeRect(20, 14, 80, 28))
        add_btn.setTitle_('Add...')
        add_btn.setBezelStyle_(NSBezelStyleRounded)
        add_btn.setTarget_(self)
        add_btn.setAction_(objc.selector(self.addException_, signature=b'v@:@'))
        view.addSubview_(add_btn)

        remove_btn = NSButton.alloc().initWithFrame_(NSMakeRect(110, 14, 80, 28))
        remove_btn.setTitle_('Remove')
        remove_btn.setBezelStyle_(NSBezelStyleRounded)
        remove_btn.setTarget_(self)
        remove_btn.setAction_(objc.selector(self.removeException_, signature=b'v@:@'))
        self._remove_btn = remove_btn
        view.addSubview_(remove_btn)

        return view

    def addException_(self, sender):
        from app import _osascript_input
        self._listener.pause_tap()
        try:
            word = _osascript_input('Add Exception', 'Word will never be auto-corrected:')
        finally:
            self._listener.resume_tap()

        if word:
            w = word.strip().lower()
            if w and w not in self._exceptions:
                self._exceptions.add(w)
                self._sync_exceptions()

    def removeException_(self, sender):
        row = self._table.selectedRow()
        if row < 0 or row >= len(self._exc_list):
            return
        word = self._exc_list[row]
        self._exceptions.discard(word)
        self._sync_exceptions()

    @objc.python_method
    def _sync_exceptions(self):
        import exceptions as exc_store
        exc_store.save(self._exceptions)
        self._word_buffer.set_exceptions(self._exceptions)
        self._exc_list[:] = sorted(self._exceptions)
        self._table_delegate.exc_list = self._exc_list
        self._table.reloadData()
        self._on_exceptions_change(self._exceptions)


class _ExceptionsDataSource(NSObject):

    @objc.python_method
    def initWith_(self, exc_list):
        self = objc.super(_ExceptionsDataSource, self).init()
        if self is None:
            return None
        self.exc_list = exc_list
        return self

    def numberOfRowsInTableView_(self, table):
        return len(self.exc_list)

    def tableView_objectValueForTableColumn_row_(self, table, col, row):
        if 0 <= row < len(self.exc_list):
            return self.exc_list[row]
        return ''
