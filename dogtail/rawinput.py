# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from dogtail.config import config
from dogtail.utils import doDelay
from dogtail.logging import debugLogger as logger
from pyatspi import Registry as registry
from pyatspi import (KEY_SYM, KEY_PRESS, KEY_PRESSRELEASE, KEY_RELEASE)
from time import sleep
import os

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk

SESSION_TYPE = 'x11'
if 'XDG_SESSION_TYPE' in os.environ and 'wayland' in os.environ['XDG_SESSION_TYPE']:
    os.system('gsettings set org.gnome.shell introspect true')
    os.system('gsettings set org.gnome.desktop.peripherals.keyboard delay 2000')
    SESSION_TYPE = 'wayland'

ponytail = None
if SESSION_TYPE == 'wayland':
    from ponytail.ponytail import Ponytail
    ponytail = Ponytail()
    ponytail.disconnect()
    sleep(1) # needed now to overcome fast reconnect issue in ponytail

"""
Handles raw input using AT-SPI event generation.

Note: Think of keyvals as keysyms, and keynames as keystrings.
"""
__author__ = """
David Malcolm <dmalcolm@redhat.com>,
Zack Cerza <zcerza@redhat.com>
"""

LOCAL_COORDS_OFFSET = (0, 0) # substract this from x, y when using local coords (wayland, shadows are the cause)


def update_coords(coords):
    # if SESSION_TYPE == 'wayland':
    #     x = coords[0] - LOCAL_COORDS_OFFSET[0]
    #     y = coords[1] - LOCAL_COORDS_OFFSET[1]
    #     if x < 0 or y < 0:
    #         return coords
    #     return (x, y)
    return coords


# Detect Xwayland windows in order to use globals and recordMonitor
def ponytail_check_is_xwayland(window_id=None, window_list=None):
    if window_list is None:
        window_list = ponytail.window_list
    if type(window_id) is int: # node.* input functions
        return int([x['client-type'] for x in window_list if x['id'] == window_id][0])
    elif window_id is None: # direct rawinput functions
        for window in window_list:
            if bool(window['has-focus']) is True:
                return int(window['client-type'])
    else:
        return 0


def ponytail_check_connection(window_id=None, input_source='mouse'): # mouse/keyboard. No need to switch context for keys
    window_list = ponytail.window_list # need it more, let's save some dbus traffic
    if ponytail.connected and type(ponytail.connected) is int: # we need to check if possibly connected window still exists
        if ponytail.connected not in [x['id'] for x in window_list]:
            print('Disconnecting no longer open window')
            ponytail.disconnect() # clear the connected status of window that has already been closed
            sleep(1)
            print('Done')
    if input_source == 'keyboard' and ponytail.connected is None:
        print("Keyboard event, connecting monitor")
        ponytail.connectMonitor()
    elif input_source == 'keyboard' and ponytail.connected is not None:
        if window_id == '' and type(ponytail.connected) is int:
            ponytail.disconnect()
            sleep(1)
            print("Keyboard event, monitor request, forcing monitor")
            ponytail.connectMonitor()
        else:
            print('Any window/monitor already connected for keyboard event')
    else: # mouse mouse events
        print("Mouse input event")
        if ponytail_check_is_xwayland(window_id, window_list):
            window_id = '' # 'window' id for monitor
        if ponytail.connected is None and window_id is None: # direct click() etc. functions, take focused window
            for window in window_list:
                if bool(window['has-focus']) is True:
                    ponytail.connectWindow(window['id'])
                    print("Connected active window")
        elif ponytail.connected is not None and window_id is None: # direct click() etc. functions, take focused window
            for window in window_list:
                if bool(window['has-focus']) is True:
                    if ponytail.connected != window['id']:
                        ponytail.disconnect()
                        sleep(1)
                        ponytail.connectWindow(window['id'])
                        print("RE-CONNECTED to active window (direct click() etc. function)")
        elif ponytail.connected is None:
            if type(window_id) is int:
                ponytail.connectWindow(window_id)
                print('Connected window')
            elif type(window_id) is str:
                ponytail.connectMonitor(window_id)
                print('Connected monitor (Xwayand?)')
        elif ponytail.connected != window_id and type(window_id) is int:
            ponytail.disconnect()
            sleep(1.5)
            print(ponytail.connected)
            print('Reconnecting window')
            print(window_id)
            ponytail.connectWindow(window_id)
            print('Connected window')
        elif ponytail.connected != window_id and type(window_id) is str:
            ponytail.disconnect()
            sleep(1)
            print('Reconnecting monitor')
            ponytail.connectMonitor()
            print('Connected monitor')
        elif ponytail.connected == window_id:
            print('Window/monitor already connected')


def doTypingDelay():
    doDelay(config.typingDelay)


def checkCoordinates(x, y):
    if x < 0 or y < 0:
        raise ValueError("Attempting to generate a mouse event at negative coordinates: (%s,%s)" % (x, y))


def click(x, y, button=1, check=True, window_id=None):
    """
    Synthesize a mouse button click at (x,y)
    """
    if check:
        checkCoordinates(x, y)
    (x, y) = update_coords((x, y))
    logger.log("Mouse button %s click at (%s,%s)" % (button, x, y))
    if SESSION_TYPE == 'x11':
        registry.generateMouseEvent(x, y, name='b%sc' % button)
    else:
        ponytail_check_connection(window_id)
        ponytail.generateButtonEvent(button, x, y)
    doDelay(config.actionDelay)


def point(x, y, check=True, window_id=None):
    if check:
        checkCoordinates(x, y)
    (x, y) = update_coords((x, y))
    logger.log("Pointing mouse cursor at (%s,%s)" % (x, y))
    if SESSION_TYPE == 'x11':
        registry.generateMouseEvent(x, y, 'abs')
    else:
        ponytail_check_connection(window_id)
        ponytail.generateMotionEvent(x, y)
    doDelay(config.actionDelay)


def doubleClick(x, y, button=1, check=True, window_id=None):
    """
    Synthesize a mouse button double-click at (x,y)
    """
    if check:
        checkCoordinates(x, y)
    (x, y) = update_coords((x, y))
    logger.log("Mouse button %s doubleclick at (%s,%s)" % (button, x, y))
    if SESSION_TYPE == 'x11':
        registry.generateMouseEvent(x, y, name='b%sd' % button)
    else:
        ponytail_check_connection(window_id)
        ponytail.generateButtonEvent(button, x, y)
        doDelay(config.doubleClickDelay)
        ponytail.generateButtonEvent(button)
        # ponytail.generateButtonPress(self, button):
        # ponytail.generateButtonRelease(self, button):
    doDelay(config.actionDelay)


def press(x, y, button=1, check=True, window_id=None, delay=config.defaultDelay):
    """
    Synthesize a mouse button press at (x,y)
    """
    if check:
        checkCoordinates(x, y)
    (x, y) = update_coords((x, y))
    logger.log("Mouse button %s press at (%s,%s)" % (button, x, y))
    if SESSION_TYPE == 'x11':
        registry.generateMouseEvent(x, y, name='b%sp' % button)
    else:
        ponytail_check_connection(window_id)
        ponytail.generateMotionEvent(x, y)
        ponytail.generateButtonPress(button)
    doDelay(delay)


def release(x, y, button=1, check=True, window_id=None):
    """
    Synthesize a mouse button release at (x,y)
    """
    if check:
        checkCoordinates(x, y)
    (x, y) = update_coords((x, y))
    logger.log("Mouse button %s release at (%s,%s)" % (button, x, y))
    if SESSION_TYPE == 'x11':
        registry.generateMouseEvent(x, y, name='b%sr' % button)
    else:
        ponytail_check_connection(window_id)
        ponytail.generateMotionEvent(x, y)
        doDelay()
        ponytail.generateButtonRelease(button)
    doDelay()


def absoluteMotion(x, y, mouseDelay=None, check=True, window_id=None):
    """
    Synthesize mouse absolute motion to (x,y)
    """
    if check:
        checkCoordinates(x, y)
    (x, y) = update_coords((x, y))
    logger.log("Mouse absolute motion to (%s,%s)" % (x, y))
    if SESSION_TYPE == 'x11':
        registry.generateMouseEvent(x, y, name='abs')
    else:
        ponytail_check_connection(window_id)
        ponytail.generateMotionEvent(x, y)
    if mouseDelay:
        doDelay(mouseDelay)
    else:
        doDelay()


def absoluteMotionWithTrajectory(source_x, source_y, dest_x, dest_y, mouseDelay=None, check=True, window_id=None):
    """
    Synthetize mouse absolute motion with trajectory. The 'trajectory' means that the whole motion
    is divided into several atomic movements which are synthetized separately.
    """
    if check:
        checkCoordinates(source_x, source_y)
        checkCoordinates(dest_x, dest_y)
    logger.log("Mouse absolute motion with trajectory to (%s,%s)" % (dest_x, dest_y))
    if SESSION_TYPE == 'wayland':
        ponytail_check_connection(window_id)

    dx = float(dest_x - source_x)
    dy = float(dest_y - source_y)
    max_len = max(abs(dx), abs(dy))
    if max_len == 0:
        # actually, no motion requested
        return
    dx /= max_len
    dy /= max_len
    act_x = float(source_x)
    act_y = float(source_y)

    for _ in range(0, int(max_len)):
        act_x += dx
        act_y += dy
        if mouseDelay:
            doDelay(mouseDelay)
        if SESSION_TYPE == 'x11':
            registry.generateMouseEvent(int(act_x), int(act_y), name='abs')
        else:
            ponytail.generateMotionEvent(int(act_x), int(act_y))

    if mouseDelay:
        doDelay(mouseDelay)
    else:
        doDelay()


def relativeMotion(x, y, mouseDelay=None):
    """
    Synthetize a relative motion from actual position.
    Note: Does not check if the end coordinates are positive.
    """
    logger.log("Mouse relative motion of (%s,%s)" % (x, y))
    if SESSION_TYPE == 'wayland':
        logger.log("Relative motion unavailable under wayland")
        return
    registry.generateMouseEvent(x, y, name='rel')
    if mouseDelay:
        doDelay(mouseDelay)
    else:
        doDelay()


def drag(fromXY, toXY, button=1, check=True):
    """
    Synthesize a mouse press, drag, and release on the screen.
    """
    logger.log("Mouse button %s drag from %s to %s" % (button, fromXY, toXY))

    (x, y) = fromXY
    press(x, y, button, check)

    (x, y) = toXY
    absoluteMotion(x, y, check=check)
    doDelay()

    release(x, y, button, check)
    doDelay()


def dragNodeToNode(source_node, dest_node, button=1, check=True):
    """
    Drag source_node onto dest_node. These are tree.Node objects. Takes positions
    of these Nodes directly, so you don't have to calculate end enter them directly.
    """
    logger.log("Mouse button %s drag from %s to %s" % (button, source_node, dest_node))

    x = source_node.position[0] + source_node.size[0] / 2
    y = source_node.position[1] + source_node.size[1] / 2
    press(x, y, button, check, source_node.window_id)

    x = dest_node.position[0] + dest_node.size[0] / 2
    y = dest_node.position[1] + dest_node.size[1] / 2

    release(x, y, button, check, window_id=dest_node.window_id)
    doDelay()


def dragWithTrajectoryGlobal(fromXY, toXY, button=1):
    """
    Synthetize a mouse press, drag (including move events), and release on the screen
    For use on Wayland - as this function forces using global coords, although we get
    local ones from a11y. So this function is targeted to be used for inter-window drags
    on Wayland, where you will need to questimate the coords. Which is doable i.e by having
    source window placed on the left *half* of the screen (local coords will be very similar
    to globals perhaps with the top panel offset).

    Having 'trajectory' appears to be necessary on Wayland for any drags. Use 'dragWithTrajectory'
    or just 'drag' on X sessions like in pre-wayland version of dogtail.
    """
    if SESSION_TYPE == 'wayland':
        logger.log("GLOBAL Mouse button %s drag from %s to %s" % (button, fromXY, toXY))

        (x, y) = fromXY
        ponytail_check_connection(window_id='') # connect MONITOR

        ponytail.generateMotionEvent(x, y)
        doDelay(config.defaultDelay)
        ponytail.generateButtonPress(1)
        doDelay(config.defaultDelay)

        (x, y) = toXY
        absoluteMotionWithTrajectory(fromXY[0], fromXY[1], x, y, mouseDelay=0.01, window_id='')

        ponytail.generateMotionEvent(x, y)
        doDelay(config.defaultDelay)
        ponytail.generateButtonRelease(1)
        doDelay()
    else:
        dragWithTrajectory(fromXY, toXY, button)


def dragWithTrajectory(fromXY, toXY, button=1, check=True, press_delay=config.defaultDelay):
    """
    Synthetize a mouse press, drag (including move events), and release on the screen
    Please note, that on Wayland, this function works for drags only within a single window.
    On X this function works with global coords and equals dragWithTrajectoryGlobal
    """
    logger.log("Mouse button %s drag with trajectory from %s to %s" % (button, fromXY, toXY))

    (x, y) = fromXY
    press(x, y, button, check, delay=press_delay)

    (x, y) = toXY
    absoluteMotionWithTrajectory(fromXY[0], fromXY[1], x, y, mouseDelay=0.01, check=check)
    doDelay()

    release(x, y, button, check)
    doDelay()


def typeText(string):
    """
    Types the specified string, one character at a time.
    Please note, you may have to set a higher typing delay,
    if your machine misses/switches the characters typed.
    Needed sometimes on slow setups/VMs typing non-ASCII utf8 chars.
    """
    for char in string:
        pressKey(char)

keyNameAliases = {
    'enter': 'Return',
    'esc': 'Escape',
    'backspace': 'BackSpace',
    'alt': 'Alt_L',
    'control': 'Control_L',
    'ctrl': 'Control_L',
    'shift': 'Shift_L',
    'del': 'Delete',
    'ins': 'Insert',
    'pageup': 'Page_Up',
    'pagedown': 'Page_Down',
    'win': 'Super_L',
    'meta': 'Super_L',
    'super': 'Super_L',
    'tab': 'Tab',
    'print': 'Print', # printscreen
    ' ': 'space',
    '\t': 'Tab',
    '\n': 'Return',
    '\b': 'BackSpace'
}


def uniCharToKeySym(uniChar):
    i = ord(uniChar)
    keySym = Gdk.unicode_to_keyval(i)
    return keySym


def keyNameToKeySym(keyName):
    keyName = keyNameAliases.get(keyName.lower(), keyName)
    keySym = Gdk.keyval_from_name(keyName)
    # various error 'codes' returned for non-recognized chars in versions of GTK3.X
    if keySym == 0xffffff or keySym == 0x0 or keySym is None:
        try:
            keySym = uniCharToKeySym(keyName)
        except:  # not even valid utf-8 char
            try:  # Last attempt run at a keyName ('Meta_L', 'Dash' ...)
                keySym = getattr(Gdk, 'KEY_' + keyName)
            except AttributeError:
                raise KeyError(keyName)
    return keySym


def keyNameToKeyCode(keyName):
    """
    Use GDK to get the keycode for a given keystring.

    Note that the keycode returned by this function is often incorrect when
    the requested keystring is obtained by holding down the Shift key.

    Generally you should use uniCharToKeySym() and should only need this
    function for nonprintable keys anyway.
    """
    keymap = Gdk.Keymap.get_for_display(Gdk.Display.get_default())
    entries = keymap.get_entries_for_keyval(
        Gdk.keyval_from_name(keyName))
    try:
        return entries[1][0].keycode
    except TypeError:
        pass


def pressKey(keyName, window_id=None):
    """
    Presses (and releases) the key specified by keyName.
    keyName is the English name of the key as seen on the keyboard. Ex: 'enter'
    Names are looked up in Gdk.KEY_ If they are not found there, they are
    looked up by uniCharToKeySym().
    """
    if 'esc' in keyName.lower():
        window_id = '' # when this would quit a window, release event would be doomed
    keySym = keyNameToKeySym(keyName)
    if SESSION_TYPE == 'x11':
        registry.generateKeyboardEvent(keySym, None, KEY_SYM)
    else:
        ponytail_check_connection(window_id, input_source='keyboard')
        ponytail.generateKeysymEvent(keySym, delay=0.15)
    doTypingDelay()


def keyCombo(comboString):
    """
    Generates the appropriate keyboard events to simulate a user pressing the
    specified key combination.

    comboString is the representation of the key combo to be generated.
    e.g. '<Control><Alt>p' or '<Control><Shift>PageUp' or '<Control>q'
    """
    strings = []
    for s in comboString.split('<'):
        if s:
            for S in s.split('>'):
                if S:
                    S = keyNameAliases.get(S.lower(), S)
                    strings.append(S)
    for s in strings:
        if not hasattr(Gdk, s):
            if not hasattr(Gdk, 'KEY_' + s):
                raise ValueError("Cannot find key %s" % s)
    modifiers = strings[:-1]
    finalKey = strings[-1]
    if SESSION_TYPE == 'x11':
        for modifier in modifiers:
            code = keyNameToKeyCode(modifier)
            registry.generateKeyboardEvent(code, None, KEY_PRESS)
        code = keyNameToKeyCode(finalKey)
        registry.generateKeyboardEvent(code, None, KEY_PRESSRELEASE)
        for modifier in modifiers:
            code = keyNameToKeyCode(modifier)
            registry.generateKeyboardEvent(code, None, KEY_RELEASE)
    else:
        # always use monitor, window will often get closed before final release i.e. with alt-f4 ctrl-q etc!
        ponytail_check_connection(input_source='keyboard', window_id='')
        for modifier in modifiers:
            code = keyNameToKeyCode(modifier)
            ponytail.generateKeycodePress(code)
        code = keyNameToKeyCode(finalKey)
        ponytail.generateKeycodeEvent(code)
        for modifier in modifiers:
            code = keyNameToKeyCode(modifier)
            ponytail.generateKeycodeRelease(code)
    doDelay()


def holdKey(keyName):
    keyName = keyNameAliases.get(keyName.lower(), keyName)
    code = keyNameToKeyCode(keyName)
    if SESSION_TYPE == 'x11':
        registry.generateKeyboardEvent(code, None, KEY_PRESS)
    else:
        ponytail_check_connection(input_source='keyboard')
        ponytail.generateKeycodePress(code)
    doDelay()


def releaseKey(keyName):
    keyName = keyNameAliases.get(keyName.lower(), keyName)
    code = keyNameToKeyCode(keyName)
    if SESSION_TYPE == 'x11':
        registry.generateKeyboardEvent(code, None, KEY_RELEASE)
    else:
        ponytail_check_connection(input_source='keyboard')
        ponytail.generateKeycodeRelease(code)
    doDelay()
