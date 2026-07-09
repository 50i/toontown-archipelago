# Opened/closed by its own persistent "Traps" toggle button (top right),

from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel, DGG
from panda3d.core import TextNode

from apworld.toontown.items import ITEM_NAME_TO_ID
from toontown.archipelago.definitions.rewards import get_ap_reward_from_id, TrapReward

# item_id -> display name, for every item whose reward is a trap (inherits TrapReward).
# ITEM_NAME_TO_ID is keyed by the enum's .value, which is already the human-readable
# string (e.g. "Uber Trap"), so this needs no manual upkeep as new traps are added.
ITEM_ID_TO_LABEL = {
    item_id: name
    for name, item_id in ITEM_NAME_TO_ID.items()
    if isinstance(get_ap_reward_from_id(item_id), TrapReward)
}

ROW_HEIGHT = 0.13
PANEL_POS = (0.92, 0.0, 0.6)
TOGGLE_POS = (1.15, 0.0, 0.9)


class TrapsGUI(DirectFrame):
    """Full standalone GUI for held traps: background, title label, an
    'empty' placeholder label, and one fire button per held trap."""

    def __init__(self):
        self.guiButton = loader.loadModel('phase_3/models/gui/quit_button')
        self.cdrGui = loader.loadModel('phase_3.5/models/gui/tt_m_gui_sbk_codeRedemptionGui')

        DirectFrame.__init__(
            self,
            parent=aspect2dp,
            relief=None,
            image=self.cdrGui.find('**/tt_t_gui_sbk_cdrCodeBox'),
            pos=PANEL_POS,
            scale=(0.9, 1.0, 0.75)
        )

        # Background panel behind the controls
        self.container_frame = DirectFrame(
            parent=self,
            relief=None,
            image=DGG.getDefaultDialogGeom(),
            pos=(0, 0.0, -0.02),
            scale=(0.95, 1, 0.8)
        )

        self.titleLabel = DirectLabel(
            parent=self,
            relief=None,
            text="Held Traps",
            text_scale=(0.075, 0.075, 0.2),
            text_wordwrap=12,
            text_align=TextNode.ACenter,
            textMayChange=1,
            pos=(0, 0, 0.34)
        )

        self.emptyLabel = DirectLabel(
            parent=self,
            relief=None,
            text="No traps held",
            text_scale=(0.055, 0.055, 0.16),
            text_wordwrap=12,
            text_align=TextNode.ACenter,
            textMayChange=1,
            pos=(0, 0, 0.1)
        )

        self.trapButtons = []
        self.hide()
        self._loadToggleButton()

    # Small, always-visible button -- parented directly to aspect2dp (NOT to
    # self), so hiding the main panel doesn't hide this too.
    def _loadToggleButton(self):
        self.toggleButton = DirectButton(
            parent=aspect2dp,
            relief=None,
            image=(
                self.guiButton.find('**/QuitBtn_UP'),
                self.guiButton.find('**/QuitBtn_DN'),
                self.guiButton.find('**/QuitBtn_RLVR')
            ),
            image_scale=0.5,
            text="Traps",
            text_scale=0.045,
            text_pos=(0, -0.01),
            pos=TOGGLE_POS,
            command=self.toggleVisibility
        )

    def toggleVisibility(self):
        if self.isHidden():
            self.show()
        else:
            self.hide()

    # Called from DistributedToon.setHeldTraps whenever the server pushes an
    # updated held-trap list (list of (index, itemId) tuples)
    def refresh(self, heldTraps):
        for btn in self.trapButtons:
            btn.destroy()
        self.trapButtons.clear()

        if not heldTraps:
            self.emptyLabel.show()
            return

        self.emptyLabel.hide()

        for row, (index, itemId) in enumerate(heldTraps):
            label = ITEM_ID_TO_LABEL.get(itemId, f"Trap #{itemId}")

            btn = DirectButton(
                parent=self,
                relief=None,
                image=(
                    self.guiButton.find('**/QuitBtn_UP'),
                    self.guiButton.find('**/QuitBtn_DN'),
                    self.guiButton.find('**/QuitBtn_RLVR')
                ),
                image_scale=(1.0, 1, 1),
                text=f"{label}",
                text_scale=0.04,
                text_pos=(0, -0.01),
                pos=(0, 0.0, 0.1 - (row + 1) * ROW_HEIGHT),
                command=self.fireTrap,
                extraArgs=[index]
            )
            self.trapButtons.append(btn)

    def fireTrap(self, index):
        # The AI finds the opponent itself (it can see the whole shard, we can't) --
        # any "no opponent"/"invalid trap" feedback comes back through the existing
        # sendArchipelagoMessages channel, same as other AP messages.
        base.localAvatar.d_useHeldTrap(index)

    def destroy(self):
        if hasattr(self, 'toggleButton'):
            self.toggleButton.destroy()
        DirectFrame.destroy(self)