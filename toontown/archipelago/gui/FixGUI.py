from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel, DirectScrolledList, DGG
from panda3d.core import TextNode

from apworld.toontown.items import ITEM_NAME_TO_ID
from toontown.archipelago.definitions.rewards import TrapReward, get_ap_reward_from_id


PANEL_BG = (0.08, 0.10, 0.13, 0.94)
PANEL_EDGE = (0.62, 0.88, 0.68, 1.0)
BUTTON_BG = (0.15, 0.20, 0.25, 0.96)
BUTTON_HOVER = (0.23, 0.32, 0.30, 1.0)
TEXT = (0.93, 0.96, 0.98, 1.0)
MUTED_TEXT = (0.68, 0.76, 0.80, 1.0)


class FixGUI(DirectFrame):
    def __init__(self):
        DirectFrame.__init__(
            self,
            parent=aspect2dp,
            relief=DGG.RIDGE,
            borderWidth=(0.02, 0.02),
            frameColor=PANEL_BG,
            frameSize=(-0.48, 0.48, -0.48, 0.48),
            pos=(0, 0, 0.05)
        )

        DirectFrame(
            parent=self,
            relief=DGG.FLAT,
            frameColor=PANEL_EDGE,
            frameSize=(-0.48, 0.48, 0.43, 0.48),
            pos=(0, 0, 0)
        )

        DirectLabel(
            parent=self,
            relief=None,
            text="Fix Unlock",
            text_scale=0.058,
            text_fg=TEXT,
            text_align=TextNode.ACenter,
            pos=(0, 0, 0.365)
        )

        self.statusLabel = DirectLabel(
            parent=self,
            relief=None,
            text="Choose an unlock to grant.",
            text_scale=0.035,
            text_fg=MUTED_TEXT,
            text_wordwrap=24,
            text_align=TextNode.ACenter,
            textMayChange=1,
            pos=(0, 0, -0.405)
        )

        self.closeButton = self._makeButton("Close", (0.37, 0, 0.365), self.hide, width=0.09)
        self.items = self._buildUnlockItems()
        self.itemButtons = []
        self.scroller = DirectScrolledList(
            parent=self,
            relief=DGG.FLAT,
            frameColor=(0.05, 0.06, 0.08, 0.78),
            frameSize=(-0.38, 0.38, -0.305, 0.285),
            pos=(0, 0, 0.02),
            numItemsVisible=7,
            forceHeight=0.075,
            itemFrame_frameSize=(-0.34, 0.34, -0.28, 0.28),
            decButton_text="^",
            decButton_text_scale=0.045,
            decButton_text_fg=TEXT,
            decButton_frameColor=(BUTTON_BG, BUTTON_HOVER, BUTTON_HOVER, BUTTON_BG),
            decButton_frameSize=(-0.055, 0.055, -0.03, 0.03),
            decButton_pos=(0.43, 0, 0.24),
            incButton_text="v",
            incButton_text_scale=0.045,
            incButton_text_fg=TEXT,
            incButton_frameColor=(BUTTON_BG, BUTTON_HOVER, BUTTON_HOVER, BUTTON_BG),
            incButton_frameSize=(-0.055, 0.055, -0.03, 0.03),
            incButton_pos=(0.43, 0, -0.24)
        )

        self.refresh()
        self.hide()

    def _buildUnlockItems(self):
        values = []
        for name, itemId in ITEM_NAME_TO_ID.items():
            reward = get_ap_reward_from_id(itemId)
            if isinstance(reward, TrapReward) or reward.__class__.__name__ == 'UndefinedReward':
                continue
            values.append((itemId, name))
        return sorted(values, key=lambda value: value[1])

    def _makeButton(self, text, pos, command, width=0.32):
        return DirectButton(
            parent=self,
            relief=DGG.FLAT,
            frameColor=(BUTTON_BG, BUTTON_HOVER, BUTTON_HOVER, BUTTON_BG),
            frameSize=(-width, width, -0.03, 0.03),
            text=text,
            text_fg=TEXT,
            text_scale=0.034,
            text_pos=(0, -0.011),
            pos=pos,
            command=command
        )

    def refresh(self):
        for button in self.itemButtons:
            self.scroller.removeItem(button)
            button.destroy()
        self.itemButtons = []

        for itemId, name in self.items:
            button = DirectButton(
                relief=DGG.FLAT,
                frameColor=(BUTTON_BG, BUTTON_HOVER, BUTTON_HOVER, BUTTON_BG),
                frameSize=(-0.31, 0.31, -0.028, 0.028),
                text=name,
                text_fg=TEXT,
                text_scale=0.032,
                text_pos=(0, -0.01),
                command=self.requestUnlock,
                extraArgs=[itemId, name]
            )
            self.itemButtons.append(button)
            self.scroller.addItem(button)

    def requestUnlock(self, itemId, name):
        base.localAvatar.d_requestFixUnlock(itemId)
        self.statusLabel['text'] = f"Queued: {name}"
