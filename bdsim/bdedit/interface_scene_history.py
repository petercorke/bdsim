# Library imports
import sys
import traceback

# BdEdit imports
from bdsim.bdedit.block_graphics_wire import GraphicsWire


DEBUG = False
DEBUG_SELECTION = False


class SceneHistory:
    def __init__(self, scene):
        self.scene = scene

        self.clear()
        self.history_limit = 32

        # listeners
        self._history_modified_listeners = []
        self._history_stored_listeners = []
        self._history_restored_listeners = []

        # Internal variable for catching fatal errors, and allowing user to save work before crashing
        self.FATAL_ERROR = False

    def clear(self):
        self.history_stack = []
        self.history_current_step = -1

    def storeInitialHistoryStamp(self):
        # After model has been loaded, add current deserialized state as the first stamp in the history stack
        self.storeHistory("Initial History Stamp")

    def addHistoryModifiedListener(self, callback: "function"):
        self._history_modified_listeners.append(callback)

    def addHistoryStoredListener(self, callback: "function"):
        self._history_stored_listeners.append(callback)

    def addHistoryRestoredListener(self, callback: "function"):
        self._history_restored_listeners.append(callback)

    def undo(self):
        if DEBUG:
            print("UNDO")

        # Only able to undo steps if current pointer is not on first item of the history stack
        if self.history_current_step > 0:
            self.history_current_step -= 1
            self.restroreHistory()
            self.scene.has_been_modified = True

    def redo(self):
        if DEBUG:
            print("REDO")

        # Only able to redo steps if current pointer is not on last item of the history stack
        if self.history_current_step + 1 < len(self.history_stack):
            self.history_current_step += 1
            self.restroreHistory()
            self.scene.has_been_modified = True

    def restroreHistory(self):
        if DEBUG:
            print(
                "Resorting history ... current_step: @%d" % self.history_current_step,
                "(%d)" % len(self.history_stack),
            )

        self.restoreHistoryStamp(self.history_stack[self.history_current_step])
        for callback in self._history_modified_listeners:
            callback()
        for callback in self._history_restored_listeners:
            callback()

    def storeHistory(self, desc, setModified: bool = False):
        if setModified:
            self.scene.has_been_modified = True

        if DEBUG:
            print(
                "Storing history",
                '"%s"' % desc,
                "... current_step: @%d" % self.history_current_step,
                "(%d)" % len(self.history_stack),
            )

        # If pointer (history_current_step), is not at end of history_stack and a change is made,
        # then we must remove everything ahead of the pointer, as we've overwritten previous changes
        if self.history_current_step + 1 < len(self.history_stack):
            # Remove everything thats currently in the history stack ahead of the pointer
            self.history_stack = self.history_stack[0 : self.history_current_step + 1]

        # If history stack is larger than our history limit
        if self.history_current_step + 1 >= self.history_limit:
            # Remove first item in history stack and add new item to end of list
            self.history_stack = self.history_stack[1:]
            self.history_current_step -= 1

        hs = self.createHistoryStamp(desc)

        self.history_stack.append(hs)
        self.history_current_step += 1
        if DEBUG:
            print(" -- setting step to:", self.history_current_step)

        for callback in self._history_modified_listeners:
            callback()
        for callback in self._history_stored_listeners:
            callback()

    def captureCurrentSelection(self):
        sel_obj = {
            "blocks": [],
            "wires": [],
            "floating_labels": [],
            "grouping_boxes": [],
        }

        for item in self.scene.grScene.selectedItems():
            if hasattr(item, "block"):
                sel_obj["blocks"].append(item.block.id)
            elif hasattr(item, "wire"):
                sel_obj["wires"].append(item.wire.id)
            elif hasattr(item, "floating_label"):
                sel_obj["floating_labels"].append(item.floating_label.id)
            elif hasattr(item, "grouping_box"):
                sel_obj["grouping_boxes"].append(item.grouping_box.id)
        return sel_obj

    def createHistoryStamp(self, desc):
        history_stamp = {
            "desc": desc,
            "snapshot": self.scene.serialize(),
            "selection": self.captureCurrentSelection(),
        }

        return history_stamp

    def restoreHistoryStamp(self, history_stamp):
        if DEBUG:
            print("RHS: ", history_stamp["desc"])

        try:
            self.scene.deserialize(history_stamp["snapshot"])

            # restore selection

            # first clear selection on all wires, then restore selection on wires from history_stamp
            for wire in self.scene.wires:
                wire.grWire.setSelected(False)
            for wire_id in history_stamp["selection"]["wires"]:
                for wire in self.scene.wires:
                    if wire.id == wire_id:
                        wire.grWire.setSelected(True)
                        break

            # first clear selection on all blocks, then restore selection on blocks from history_stamp
            for block in self.scene.blocks:
                block.grBlock.setSelected(False)
            for block_id in history_stamp["selection"]["blocks"]:
                for block in self.scene.blocks:
                    if block.id == block_id:
                        block.grBlock.setSelected(True)
                        break

            # first clear selection on all floating labels, then restore selection on floating labels from history_stamp
            for label in self.scene.floating_labels:
                label.grContent.setSelected(False)
            for label_id in history_stamp["selection"]["floating_labels"]:
                for label in self.scene.floating_labels:
                    if label.id == label_id:
                        label.grContent.setSelected(True)
                        break

            # first clear selection on all grouping boxes, then restore selection on grouping boxes from history_stamp
            for gbox in self.scene.grouping_boxes:
                gbox.grGBox.setSelected(False)
            for gbox_id in history_stamp["selection"]["grouping_boxes"]:
                for gbox in self.scene.grouping_boxes:
                    if gbox.id == gbox_id:
                        gbox.grGBox.setSelected(True)
                        break

        except Exception as e:
            if self.FATAL_ERROR == False:
                print(
                    "-------------------------------------------------------------------------"
                )
                print(
                    "Caught fatal exception while trying to undo/redo. "
                    "\nThis may have caused unsaved changes to become corrupted, apologies. "
                    "\nPlease note the error and report it to Daniel."
                )
                print(
                    "-------------------------------------------------------------------------"
                )
                traceback.print_exc(file=sys.stderr)
                self.FATAL_ERROR = True
