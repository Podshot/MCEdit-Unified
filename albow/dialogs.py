#-# Modified by D.C.-G. for translation purpose
import textwrap
from pygame import event, key
from pygame.locals import *
from widget import Widget
from controls import Label, Button
from layout import Row, Column
from fields import TextFieldWrapped
from scrollpanel import ScrollPanel
from table_view import TableView, TableColumn
from translate import _

class Modal(object):
    enter_response = True
    cancel_response = False

    def ok(self):
        self.dismiss(True)

    def cancel(self):
        self.dismiss(False)


class Dialog(Modal, Widget):
    click_outside_response = None

    def __init__(self, client=None, responses=None,
                 default=0, cancel=-1, **kwds):
        Widget.__init__(self, **kwds)
        self.root = self.get_root()
        if client or responses:
            rows = []
            w1 = 0
            w2 = 0
            if client:
                rows.append(client)
                w1 = client.width
            if responses:
                buttons = Row([
                    Button(text, action=lambda t=text: self.dismiss(t))
                    for text in responses])
                rows.append(buttons)
                w2 = buttons.width
            if w1 < w2:
                a = 'l'
            else:
                a = 'r'
            contents = Column(rows, align=a)
            m = self.margin
            contents.topleft = (m, m)
            self.add(contents)
            self.shrink_wrap()
        if responses and default is not None:
            self.enter_response = responses[default]
        if responses and cancel is not None:
            self.cancel_response = responses[cancel]

    def mouse_down(self, e):
        if not e in self:
            response = self.click_outside_response
            if response is not None:
                self.dismiss(response)

    def key_down(self, e):
        pass

    def key_up(self, e):
        pass


class QuickDialog(Dialog):
    """ Dialog that closes as soon as you click outside or press a key"""

    def mouse_down(self, evt):
        if evt not in self:
            self.dismiss(-1)
            if evt.button != 1:
                event.post(evt)

    def key_down(self, evt):
        self.dismiss()
        event.post(evt)


def wrapped_label(text, wrap_width, **kwds):
    # paras = text.split("\n")
    text = _(text)
    kwds['doNotTranslate'] = True
    paras = text.split("\n")
    text = "\n".join([textwrap.fill(para, wrap_width) for para in paras])
    return Label(text, **kwds)


# def alert(mess, wrap_width = 60, **kwds):
#    box = Dialog(**kwds)
#    d = box.margin
#    lb = wrapped_label(mess, wrap_width)
#    lb.topleft = (d, d)
#    box.add(lb)
#    box.shrink_wrap()
#    return box.present()


def alert(mess, **kwds):
    ask(mess, ["OK"], **kwds)

ask_tied_to = None
# ask_tied_to = []
ask_tied_tos = []

def ask(mess, responses=["OK", "Cancel"], default=0, cancel=-1,
        wrap_width=60, **kwds):
    # If height is specified as a keyword, the Dialog object will have this haight, and the inner massage will
    # be displayed in a scrolling widget
    # If 'responses_tooltips' it present in kwds, it must be dict with 'responses' as keys and the tooltips as values.
    # If 'tie_widget_to' is in kwds keys and the value is True, the global 'ask_tied_to' will be set up to the 'box'.
    # When called again with 'tie_widget_to', if 'ask_tied_to' is not None, the function returns a dummy answer.
    global ask_tied_to
    responses_tooltips = kwds.pop('responses_tooltips', {})
    tie_widget_to = kwds.pop('tie_widget_to', None)
    # Return a dummy answer if tie_windget_to is True and the global 'ask_tied_to' is not None
    if tie_widget_to and ask_tied_to:
        return "_OK"

    colLbl = kwds.pop('colLabel', "")

    box = Dialog(**kwds)
    d = box.margin
    lb = wrapped_label(mess, wrap_width)
    buts = []
    for caption in responses:
        but = Button(caption, action=lambda x=caption: box.dismiss(x))
        if caption in responses_tooltips.keys():
            but.tooltipText = responses_tooltips[caption]
        buts.append(but)
    brow = Row(buts, spacing=d)
    lb.width = max(lb.width, brow.width)
    height = kwds.get('height', None)
    if height and lb.height > height - (2 * brow.height) - ScrollPanel.column_margin - box.margin:
        lines = mess.split('\n')
        # ScrolledPanel refuses to render properly for now, so Tableview is used instead.
        w = TableView().font.size(_(colLbl))[0]
        lb = TableView(columns=[TableColumn(colLbl, max(lb.width, w)),], nrows=(height - (2 * brow.height) - box.margin - box.font.get_linesize()) / box.font.get_linesize(), height=height - (2 * brow.height) - (box.font.get_linesize() * 2) - box.margin) #, width=w)

        def num_rows():
            return len(lines)

        lb.num_rows = num_rows

        lb.row_data = lambda x: (lines[x],)

    lb.topleft = (d, d)
    lb.width = max(lb.width, brow.width)
    col = Column([lb, brow], spacing=d, align='r')
    col.topleft = (d, d)
    if default is not None:
        box.enter_response = responses[default]
        buts[default].is_default = True
    else:
        box.enter_response = None
    if cancel is not None:
        box.cancel_response = responses[cancel]
    else:
        box.cancel_response = None
    box.add(col)
    box.shrink_wrap()

    def dispatchKeyForAsk(name, evt):
        if name == "key_down":
            if box.root.getKey(evt) == "Return":
                if default is not None:
                    box.dismiss(responses[default])

    box.dispatch_key = dispatchKeyForAsk
    if tie_widget_to:
        ask_tied_to = box
        ask_tied_tos.append(box)
    return box.present()


def input_text(prompt, width, initial=None, **kwds):
    box = Dialog(**kwds)
    d = box.margin

    def ok():
        box.dismiss(True)

    def cancel():
        box.dismiss(False)

    lb = Label(prompt)
    lb.topleft = (d, d)
    tf = TextFieldWrapped(width)
    if initial:
        tf.set_text(initial)
    tf.enter_action = ok
    tf.escape_action = cancel
    tf.top = lb.top
    tf.left = lb.right + 5
    box.add(lb)
    box.add(tf)
    tf.focus()
    box.shrink_wrap()
    if box.present():
        return tf.get_text()
    else:
        return None


def input_text_buttons(prompt, width, initial=None, allowed_chars=None, **kwds):
    box = Dialog(**kwds)
    d = box.margin

    def ok():
        box.dismiss(True)

    def cancel():
        box.dismiss(False)

    buts = [Button("OK", action=ok), Button("Cancel", action=cancel)]

    brow = Row(buts, spacing=d)

    lb = Label(prompt)
    lb.topleft = (d, d)
    tf = TextFieldWrapped(width,allowed_chars=allowed_chars)
    if initial:
        tf.set_text(initial)
    tf.enter_action = ok
    tf.escape_action = cancel
    tf.top = lb.top
    tf.left = lb.right + 5

    trow = Row([lb, tf], spacing=d)

    col = Column([trow, brow], spacing=d, align='c')

    col.topleft = (d, d)

    box.add(col)
    tf.focus()
    box.shrink_wrap()
    if box.present():
        return tf.get_text()
    else:
        return None
