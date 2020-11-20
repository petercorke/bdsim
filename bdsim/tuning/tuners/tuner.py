class Tuner:

    def __init__(self):
        self.queued_updates = []

    def setup(self, params, bd):
        # if needed
        pass

    def update(self):
        for update in self.queued_updates:
            update()
        self.queued_updates = []

    def queue_update(self, update_fn):
        self.queued_updates.append(update_fn)
