class RenderContext(object):

    def __init__(self, initiator=None):
        self._render_stack = []
        if initiator:
            self.push(initiator)

    def push(self, item):
        self._render_stack.append(item)

    def pop(self):
        return self._render_stack.pop()

    def __contains__(self, item):
        return item in self._render_stack
