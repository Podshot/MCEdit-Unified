from glbackground import Panel


class ToolOptions(Panel):
    def key_down(self, evt):
        if self.root.getKey(evt) == 'Escape':
            self.escape_action()

    def escape_action(self, *args, **kwargs):
        self.dismiss()

