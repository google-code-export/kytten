# kytten/dialog.py
# Copyrighted (C) 2009 by Conrad "Lynx" Wong

import pyglet
from pyglet import gl

from widgets import Widget, Control
from frame import Wrapper
from layout import GetRelativePoint, ANCHOR_CENTER

class DialogEventManager(Control):
    def __init__(self):
        """
        Creates a new event manager for a dialog.

        @param content The Widget which we wrap
        """
        Control.__init__(self)
        self.controls = []
        self.hover = None
        self.focus = None

    def on_key_press(self, dialog, symbol, modifiers):
        """
        TAB and ENTER will move us between fields, holding shift will
        reverse the direction of our iteration.  We don't handle ESCAPE.
        Otherwise, we pass keys to our child elements.

        @param symbol Key pressed
        @param modifiers Modifiers for key press
        """
        if symbol in [pyglet.window.key.TAB, pyglet.window.key.ENTER]:
            focusable = [x for x in self.controls if x.id is not None]
            if not focusable:
                return

            if modifiers & pyglet.window.key.MOD_SHIFT:
                dir = -1
            else:
                dir = 1

            if self.focus is not None:
                index = focusable.index(self.focus)
            else:
                index = 0 - dir

            new_focus = focusable[(index + dir) % len(focusable)]
            self.set_focus(dialog, new_focus)

            # If we hit ENTER, and wrapped back to the first focusable,
            # pass the ENTER back so the Dialog can call its on_enter callback
            if symbol != pyglet.window.key.ENTER or \
               new_focus != focusable[0]:
                return pyglet.event.EVENT_HANDLED

        elif symbol != pyglet.window.key.ESCAPE:
            if self.focus is not None:
                self.focus.dispatch_event('on_key_press',
                                          dialog, symbol, modifiers)
                return pyglet.event.EVENT_HANDLED

    def on_key_release(self, dialog, symbol, modifiers):
        """Pass key release events to the focus

        @param symbol Key released
        @param modifiers Modifiers for key released
        """
        if self.focus is not None:
            self.focus.dispatch_event('on_key_release',
                                      dialog, symbol, modifiers)
            return pyglet.event.EVENT_HANDLED

    def on_mouse_drag(self, dialog, x, y, dx, dy, buttons, modifiers):
        """
        Handles mouse dragging.  If we have a focus, pass it in.

        @param x X coordinate of mouse
        @param y Y coordinate of mouse
        @param dx Delta X
        @param dy Delta Y
        @param buttons Buttons held while moving
        @param modifiers Modifiers to apply to buttons
        """
        if self.focus is not None:
            self.focus.dispatch_event('on_mouse_drag', dialog,
                                      x, y, dx, dy, buttons, modifiers)
            return pyglet.event.EVENT_HANDLED

    def on_mouse_motion(self, dialog, x, y, dx, dy):
        """
        Handles mouse motion.  We highlight controls that we are hovering
        over.

        @param x X coordinate of mouse
        @param y Y coordinate of mouse
        @param dx Delta X
        @param dy Delta Y
        """
        if self.hover is not None and self.hover.hit_test(x, y):
            self.hover.dispatch_event('on_mouse_motion', dialog, x, y, dx, dy)
        new_hover = None
        for control in self.controls:
            if control.hit_test(x, y):
                new_hover = control
                break
        self.set_hover(dialog, new_hover)
        if self.hover is not None:
            self.hover.dispatch_event('on_mouse_motion', dialog, x, y, dx, dy)

    def on_mouse_press(self, dialog, x, y, button, modifiers):
        """
        If the focus is set, and the target lies within the focus, pass the
        message down.  Otherwise, check if we need to assign a new focus.
        If the mouse was pressed within our frame but no control was targeted,
        we may be setting up to drag the Dialog around.

        @param x X coordinate of mouse
        @param y Y coordinate of mouse
        @param button Button pressed
        @param modifiers Modifiers to apply to button
        """
        if self.focus is not None and self.focus.hit_test(x, y):
            self.focus.dispatch_event('on_mouse_press', dialog,
                                      x, y, button, modifiers)
            return pyglet.event.EVENT_HANDLED
        else:
            if self.hit_test(x, y):
                self.set_focus(dialog, self.hover)
                if self.focus is not None:
                    self.focus.dispatch_event('on_mouse_press', dialog,
                                              x, y, button, modifiers)
                    return pyglet.event.EVENT_HANDLED
            else:
                self.set_focus(dialog, None)

    def on_mouse_release(self, dialog, x, y, button, modifiers):
        """
        Button was released.  We pass this along to the focus, then we
        generate an on_mouse_motion to handle changing the highlighted
        Control if necessary.

        @param x X coordinate of mouse
        @param y Y coordinate of mouse
        @param button Button released
        @param modifiers Modifiers to apply to button
        """
        retval = pyglet.event.EVENT_UNHANDLED
        self.is_dragging = False
        if self.focus is not None:
            self.focus.dispatch_event('on_mouse_release', dialog,
                                             x, y, button, modifiers)
            retval = pyglet.event.EVENT_HANDLED
        DialogEventManager.on_mouse_motion(self, dialog, x, y, 0, 0)
        return retval

    def on_text(self, dialog, text):
        if self.focus and text != u'\r':
            self.focus.dispatch_event('on_text', dialog, text)

    def on_text_motion(self, dialog, motion):
        if self.focus:
            self.focus.dispatch_event('on_text_motion', dialog, motion)

    def on_text_motion_select(self, dialog, motion):
        if self.focus:
            self.focus.dispatch_event('on_text_motion_select', dialog, motion)

    def on_update(self, dialog, dt):
        """
        We update our layout only when it's time to construct another frame.
        Since we may receive several resize events within this time, this
        ensures we don't resize too often.

        @param dialog The Dialog containing the controls
        @param dt Time passed since last update event (in seconds)
        """
        for control in self.controls:
            control.dispatch_event('on_update', dialog, dt)

    def set_focus(self, dialog, focus):
        """
        Sets a new focus, dispatching lose and gain focus events appropriately

        @param dialog The Dialog containing the focus
        @param focus The new focus, or None if no focus
        """
        if self.focus == focus:
            return
        if self.focus is not None:
            self.focus.dispatch_event('on_lose_focus', dialog)
        self.focus = focus
        if focus is not None:
            focus.dispatch_event('on_gain_focus', dialog)

    def set_hover(self, dialog, hover):
        """
        Sets a new highlight, dispatching lose and gain highlight events
        appropriately

        @param dialog The Dialog containing the highlighted item
        @param hover The new highlight, or None if no highlight
        """
        if self.hover == hover:
            return
        if self.hover is not None:
            self.hover.dispatch_event('on_lose_highlight', dialog)
        self.hover = hover
        if hover is not None:
            hover.dispatch_event('on_gain_highlight', dialog)

kytten_next_dialog_order_id = 0
def GetNextDialogOrderId():
    global kytten_next_dialog_order_id
    kytten_next_dialog_order_id += 1
    return kytten_next_dialog_order_id

class DialogGroup(pyglet.graphics.OrderedGroup):
    """
    Ensure that all Widgets within a Dialog can be drawn with
    blending enabled, and that our Dialog will be drawn in a particular
    order relative to other Dialogs.
    """
    def __init__(self, parent=None):
        """
        Creates a new DialogGroup.  By default we'll be on top.

        @param parent Parent group
        """
        pyglet.graphics.OrderedGroup.__init__(
            self, GetNextDialogOrderId(), parent)
        self.real_order = self.order

    def __cmp__(self, other):
        """
        When compared with other DialogGroups, we'll return our real order
        compared against theirs; otherwise use the OrderedGroup comparison.
        """
        if isinstance(other, DialogGroup):
            return cmp(self.real_order, other.real_order)
        else:
            return OrderedGroup.__cmp__(self, other)

    def is_on_top(self):
        """
        Are we the top dialog group?
        """
        global kytten_next_dialog_order_id
        return self.real_order == kytten_next_dialog_order_id

    def pop_to_top(self):
        """
        Put us on top of other dialog groups.
        """
        self.real_order = GetNextDialogOrderId()

    def set_state(self):
        """
        Ensure that blending is set.
        """
        gl.glPushAttrib(gl.GL_ENABLE_BIT | gl.GL_CURRENT_BIT)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    def unset_state(self):
        """
        Restore previous blending state.
        """
        gl.glPopAttrib()

class Dialog(Wrapper, DialogEventManager):
    """
    Defines a new GUI.  By default it can contain only one element, but that
    element can be a Layout of some kind which can contain multiple elements.
    Pass a Theme in to set the graphic appearance of the Dialog.

    The Dialog is always repositioned in relationship to the window, and
    handles resize events accordingly.
    """
    def __init__(self, content=None, window=None, batch=None, group=None,
                 anchor=ANCHOR_CENTER, offset=(0, 0),
                 theme=None, movable=True, on_enter=None, on_escape=None):
        """
        Creates a new dialog.

        @param content The Widget which we wrap
        @param window The window to which we belong; used to set the
                      mouse cursor when appropriate
        @param batch Batch in which we are to place our graphic elements;
                     may be None if we are to create our own Batch
        @param group Group in which we are to place our graphic elements;
                     may be None
        @param anchor Anchor point of the window, relative to which we
                      are positioned.  If ANCHOR_TOP_LEFT is specified,
                      our top left corner will be aligned to the window's
                      top left corner; if ANCHOR_CENTER is specified,
                      our center will be aligned to the window's center,
                      and so forth.
        @param offset Offset from the anchor point.  A positive X is always
                      to the right, a positive Y to the upward direction.
        @param theme The Theme which we are to use to generate our graphical
                     appearance.
        @param movable True if the dialog is able to be moved
        @param on_enter Callback for when user presses enter on the last
                        input within this dialog, i.e. form submit
        @param on_escape Callback for when user presses escape
        """
        assert isinstance(theme, dict)
        Wrapper.__init__(self, content=content)
        DialogEventManager.__init__(self)

        self.window = window
        self.anchor = anchor
        self.offset = offset
        self.theme = theme
        self.is_movable = movable
        self.on_enter = on_enter
        self.on_escape = on_escape
        if batch is None:
            self.batch = pyglet.graphics.Batch()
            self.own_batch = True
        else:
            self.batch = batch
            self.own_batch = False
        self.root_group = DialogGroup(parent=group)
        self.panel_group = pyglet.graphics.OrderedGroup(0, self.root_group)
        self.bg_group = pyglet.graphics.OrderedGroup(1, self.root_group)
        self.fg_group = pyglet.graphics.OrderedGroup(2, self.root_group)
        self.highlight_group = pyglet.graphics.OrderedGroup(3, self.root_group)
        self.needs_layout = True
        self.controls = []
        self.hover = None
        self.focus = None
        self.is_dragging = False

        if window is None:
            self.screen = Widget()
        else:
            width, height = window.get_size()
            self.screen = Widget(width=width, height=height)

    def do_layout(self):
        """
        We lay out the Dialog by first determining the size of all its
        chlid Widgets, then laying ourself out relative to the parent window.
        As a side effect, we also update our list of controls which may
        respond to user input, and the subset of those controls which need
        to be updated regularly.
        """
        # Determine size of all components
        self.size(self)

        # Calculate our position relative to our containing window,
        # making sure that we fit completely on the window.  If our offset
        # would send us off the screen, constrain it.
        x, y = GetRelativePoint(self.screen, self.anchor,
                                self, None, (0, 0))
        max_offset_x = self.screen.width - self.width - x
        max_offset_y = self.screen.height - self.height - y
        offset_x, offset_y = self.offset
        offset_x = max(min(offset_x, max_offset_x), -x)
        offset_y = max(min(offset_y, max_offset_y), -y)
        self.offset = (offset_x, offset_y)
        x += offset_x
        y += offset_y

        # Perform the actual layout now!
        self.layout(x, y)
        self.controls = self._get_controls()

        self.needs_layout = False

    def on_key_press(self, symbol, modifiers):
        """
        We intercept TAB, ENTER, and ESCAPE events.  TAB and ENTER will
        move us between fields, holding shift will reverse the direction
        of our iteration.  ESCAPE may cause us to send an on_escape
        callback.

        Otherwise, we pass key presses to our child elements.

        @param symbol Key pressed
        @param modifiers Modifiers for key press
        """
        retval = DialogEventManager.on_key_press(self, self,
                                                 symbol, modifiers)
        if not retval:
            if symbol in [pyglet.window.key.TAB, pyglet.window.key.ENTER]:
                if self.on_enter is not None:
                    self.on_enter(self)
                    return pyglet.event.EVENT_HANDLED
            elif symbol == pyglet.window.key.ESCAPE:
                if self.on_escape is not None:
                    self.on_escape(self)
                    return pyglet.event.EVENT_HANDLED
        return retval

    def on_key_release(self, symbol, modifiers):
        """Pass key release events to the focus

        @param symbol Key released
        @param modifiers Modifiers for key released
        """
        return DialogEventManager.on_key_release(self, self, symbol, modifiers)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        """
        Handles mouse dragging.  If we have a focus, pass it in.  Otherwise
        if we are movable, and we were being dragged, move the window.

        @param x X coordinate of mouse
        @param y Y coordinate of mouse
        @param dx Delta X
        @param dy Delta Y
        @param buttons Buttons held while moving
        @param modifiers Modifiers to apply to buttons
        """
        if not DialogEventManager.on_mouse_drag(self, self, x, y, dx, dy,
                                                buttons, modifiers):
            if self.is_movable and self.is_dragging:
                x, y = self.offset
                self.offset = (x + dx, y + dy)
                self.set_needs_layout()
                return pyglet.event.EVENT_HANDLED

    def on_mouse_motion(self, x, y, dx, dy):
        """
        Handles mouse motion.  We highlight controls that we are hovering
        over.

        @param x X coordinate of mouse
        @param y Y coordinate of mouse
        @param dx Delta X
        @param dy Delta Y
        """
        return DialogEventManager.on_mouse_motion(self, self, x, y, dx, dy)

    def on_mouse_press(self, x, y, button, modifiers):
        """
        If the focus is set, and the target lies within the focus, pass the
        message down.  Otherwise, check if we need to assign a new focus.
        If the mouse was pressed within our frame but no control was targeted,
        we may be setting up to drag the Dialog around.

        @param x X coordinate of mouse
        @param y Y coordinate of mouse
        @param button Button pressed
        @param modifiers Modifiers to apply to button
        """
        retval = DialogEventManager.on_mouse_press(self, self, x, y,
                                             button, modifiers)
        if self.hit_test(x, y):
            if not self.root_group.is_on_top():
                self.pop_to_top()
            if not retval:
                self.is_dragging = True
        return retval

    def on_mouse_release(self, x, y, button, modifiers):
        """
        Button was released.  We pass this along to the focus, then we
        generate an on_mouse_motion to handle changing the highlighted
        Control if necessary.

        @param x X coordinate of mouse
        @param y Y coordinate of mouse
        @param button Button released
        @param modifiers Modifiers to apply to button
        """
        self.is_dragging = False
        return DialogEventManager.on_mouse_release(self, self, x, y,
                                                   button, modifiers)

    def on_resize(self, width, height):
        """
        Update our knowledge of the window's width and height.

        @param width Width of the window
        @param height Height of the window
        """
        if self.screen.width != width or self.screen.height != height:
            self.screen.width, self.screen.height = width, height
            self.needs_layout = True

    def on_text(self, text):
        return DialogEventManager.on_text(self, self, text)

    def on_text_motion(self, motion):
        return DialogEventManager.on_text_motion(self, self, motion)

    def on_text_motion_select(self, motion):
        return DialogEventManager.on_text_motion_select(
            self, self, motion)

    def on_update(self, dt):
        """
        We update our layout only when it's time to construct another frame.
        Since we may receive several resize events within this time, this
        ensures we don't resize too often.

        @param dt Time passed since last update event (in seconds)
        """
        if self.needs_layout:
            self.do_layout()
        DialogEventManager.on_update(self, self, dt)

    def pop_to_top(self):
        """
        Pop our dialog group to the top, and force our batch to re-sort
        the groups.  Also, puts our event handler on top of the window's
        event handler stack.
        """
        self.root_group.pop_to_top()
        self.batch._draw_list_dirty = True # forces resorting groups
        if self.window is not None:
            self.window.remove_handlers(self)
            self.window.push_handlers(self)

    def set_needs_layout(self):
        """
        True if we should redo the Dialog layout on our next update.
        """
        self.needs_layout = True
