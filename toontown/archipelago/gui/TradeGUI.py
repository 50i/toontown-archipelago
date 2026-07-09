from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel, DGG
from panda3d.core import TextNode

from apworld.toontown.items import get_item_def_from_id


PANEL_POS = (0.74, 0.0, 0.08)
TOGGLE_POS = (1.18, 0.0, 0.78)

PANEL_BG = (0.08, 0.10, 0.13, 0.92)
PANEL_EDGE = (0.38, 0.72, 0.92, 1.0)
BUTTON_BG = (0.15, 0.20, 0.25, 0.96)
BUTTON_HOVER = (0.22, 0.31, 0.38, 1.0)
BUTTON_DISABLED = (0.10, 0.10, 0.10, 0.55)
TEXT = (0.93, 0.96, 0.98, 1.0)
MUTED_TEXT = (0.68, 0.76, 0.80, 1.0)
ACCENT = (0.52, 0.87, 1.0, 1.0)


class TradeGUI(DirectFrame):
    """Compact AP item-for-item trade panel."""

    def __init__(self):
        self.targets = []
        self.offerItems = []
        self.requestItems = []
        self.requestItemsReady = False
        self.targetIndex = 0
        self.offerIndex = 0
        self.requestIndex = 0

        DirectFrame.__init__(
            self,
            parent=aspect2dp,
            relief=DGG.RIDGE,
            borderWidth=(0.018, 0.018),
            frameColor=PANEL_BG,
            frameSize=(-0.46, 0.46, -0.39, 0.39),
            pos=PANEL_POS
        )

        self.edge = DirectFrame(
            parent=self,
            relief=DGG.FLAT,
            frameColor=PANEL_EDGE,
            frameSize=(-0.46, 0.46, 0.36, 0.39),
            pos=(0, 0, 0)
        )

        self.controlBackground = DirectFrame(
            parent=self,
            relief=DGG.RIDGE,
            borderWidth=(0.01, 0.01),
            frameColor=(0.035, 0.045, 0.06, 0.86),
            frameSize=(-0.40, 0.40, -0.235, 0.235),
            pos=(0, 0, 0.005)
        )

        self.titleLabel = DirectLabel(
            parent=self,
            relief=None,
            text="Trade",
            text_scale=0.052,
            text_fg=TEXT,
            text_align=TextNode.ALeft,
            pos=(-0.39, 0, 0.29)
        )

        self.statusLabel = DirectLabel(
            parent=self,
            relief=None,
            text="",
            text_scale=0.034,
            text_fg=ACCENT,
            text_wordwrap=22,
            text_align=TextNode.ACenter,
            textMayChange=1,
            pos=(0, 0, -0.32)
        )

        self.debtLabel = DirectLabel(
            parent=self,
            relief=None,
            text="",
            text_scale=0.032,
            text_fg=MUTED_TEXT,
            text_wordwrap=23,
            text_align=TextNode.ACenter,
            textMayChange=1,
            pos=(0, 0, -0.255)
        )

        self.targetValue = self._makeValueLabel(0.16)
        self.offerValue = self._makeValueLabel(0.00)
        self.requestValue = self._makeValueLabel(-0.16)

        self._makeCycleRow("Target", 0.18, self.previousTarget, self.nextTarget)
        self._makeCycleRow("Give", 0.02, self.previousOffer, self.nextOffer)
        self._makeCycleRow("Want", -0.14, self.previousRequest, self.nextRequest)

        self.sendButton = self._makeButton("Send", (0.29, 0, 0.29), self.sendTrade, width=0.22, height=0.08)

        self.hide()
        self._loadToggleButton()
        self.refresh()

    def _loadToggleButton(self):
        self.toggleButton = DirectButton(
            parent=aspect2dp,
            relief=DGG.FLAT,
            frameColor=BUTTON_BG,
            frameSize=(-0.14, 0.14, -0.04, 0.04),
            text="Trade",
            text_fg=TEXT,
            text_scale=0.043,
            text_pos=(0, -0.014),
            pos=TOGGLE_POS,
            command=self.toggleVisibility
        )
        self.toggleButton.bind(DGG.ENTER, lambda _event: self.toggleButton.configure(frameColor=BUTTON_HOVER))
        self.toggleButton.bind(DGG.EXIT, lambda _event: self.toggleButton.configure(frameColor=BUTTON_BG))

    def _makeButton(self, text, pos, command, width=0.075, height=0.065):
        return DirectButton(
            parent=self,
            relief=DGG.FLAT,
            frameColor=(BUTTON_BG, BUTTON_HOVER, BUTTON_HOVER, BUTTON_DISABLED),
            frameSize=(-width, width, -height / 2.0, height / 2.0),
            text=text,
            text_fg=TEXT,
            text_scale=0.034,
            text_pos=(0, -0.011),
            pos=pos,
            command=command
        )

    def _makeValueLabel(self, z):
        return DirectLabel(
            parent=self,
            relief=None,
            text="",
            text_scale=0.035,
            text_fg=TEXT,
            text_wordwrap=18,
            text_align=TextNode.ACenter,
            textMayChange=1,
            pos=(0, 0, z - 0.046)
        )

    def _makeCycleRow(self, label, z, previousCommand, nextCommand):
        DirectLabel(
            parent=self,
            relief=None,
            text=label,
            text_scale=0.031,
            text_fg=MUTED_TEXT,
            text_align=TextNode.ACenter,
            pos=(0, 0, z + 0.025)
        )
        self._makeButton("<", (-0.35, 0, z - 0.03), previousCommand)
        self._makeButton(">", (0.35, 0, z - 0.03), nextCommand)

    def toggleVisibility(self):
        if self.isHidden():
            self.refresh()
            self.show()
        else:
            self.hide()

    def refresh(self, requestInventories=True):
        manager = getattr(base.cr, 'archipelagoManager', None)
        self.targets = manager.getAllTradeTargets() if manager is not None else []
        self.offerItems = []
        self.targetIndex = self._clampIndex(self.targetIndex, self.targets)
        if requestInventories and manager is not None:
            manager.d_requestTradeInventories()
        self.requestItemsReady = self._targetInventoryIsReady()
        self.requestItems = self._getTargetOwnedItems()

        debtItemIds = set(debt[1] for debt in base.localAvatar.getAPTradeDebts())
        for rewardIndex, itemId in base.localAvatar.getReceivedItems():
            itemDef = get_item_def_from_id(itemId)
            if itemDef is None:
                continue
            locked = itemId in debtItemIds
            self.offerItems.append((rewardIndex, itemId, itemDef.name.value, locked))

        self.offerIndex = self._clampIndex(self.offerIndex, self.offerItems)
        self.requestIndex = self._clampIndex(self.requestIndex, self.requestItems)
        self._refreshLabels()

    def _getTargetOwnedItems(self):
        if not self.targets or not self.requestItemsReady:
            return []

        targetAvId = self.targets[self.targetIndex]
        manager = getattr(base.cr, 'archipelagoManager', None)
        if manager is None:
            return []

        items = []
        seenItemIds = set()
        for _rewardIndex, itemId in manager.getTradeInventory(targetAvId):
            if itemId in seenItemIds:
                continue
            itemDef = get_item_def_from_id(itemId)
            if itemDef is None:
                continue
            seenItemIds.add(itemId)
            items.append((itemId, itemDef.name.value))
        return sorted(items, key=lambda value: value[1])

    def _targetInventoryIsReady(self):
        if not self.targets:
            return False
        manager = getattr(base.cr, 'archipelagoManager', None)
        if manager is None:
            return False
        return manager.hasTradeInventory(self.targets[self.targetIndex])

    def openForTarget(self, avId):
        self.refresh()
        if avId in self.targets:
            self.targetIndex = self.targets.index(avId)
            self.requestItemsReady = self._targetInventoryIsReady()
            self.requestItems = self._getTargetOwnedItems()
            self.requestIndex = self._clampIndex(self.requestIndex, self.requestItems)
        self._refreshLabels()
        self.show()

    def _clampIndex(self, index, values):
        if not values:
            return 0
        return max(0, min(index, len(values) - 1))

    def _refreshLabels(self):
        self.targetValue['text'] = self._getTargetLabel()
        self.offerValue['text'] = self._getOfferLabel()
        self.requestValue['text'] = self._getRequestLabel()
        self.debtLabel['text'] = self._getDebtLabel()

        if not self.targets:
            self.statusLabel['text'] = "No AP trade targets online."
            self.sendButton['state'] = DGG.DISABLED
        elif not self.offerItems:
            self.statusLabel['text'] = "No AP items received yet."
            self.sendButton['state'] = DGG.DISABLED
        elif not self.requestItemsReady:
            self.statusLabel['text'] = "Loading target items..."
            self.sendButton['state'] = DGG.DISABLED
        elif not self.requestItems:
            self.statusLabel['text'] = "Target has no tradeable AP items."
            self.sendButton['state'] = DGG.DISABLED
        elif self.offerItems[self.offerIndex][3]:
            self.statusLabel['text'] = "Recover this item before trading it again."
            self.sendButton['state'] = DGG.DISABLED
        else:
            self.statusLabel['text'] = ""
            self.sendButton['state'] = DGG.NORMAL

    def _getTargetLabel(self):
        if not self.targets:
            return "Nobody"
        avId = self.targets[self.targetIndex]
        toon = base.cr.doId2do.get(avId)
        if toon is not None:
            return toon.getName()
        return f"Toon {avId}"

    def _getOfferLabel(self):
        if not self.offerItems:
            return "Nothing to give"
        name = self.offerItems[self.offerIndex][2]
        if self.offerItems[self.offerIndex][3]:
            return f"{name} (recovering)"
        return name

    def _getRequestLabel(self):
        if not self.requestItems:
            return "No items"
        return self.requestItems[self.requestIndex][1]

    def _getDebtLabel(self):
        debts = base.localAvatar.getAPTradeDebts()
        if not debts:
            return ""
        debtText = []
        for debt in debts[:2]:
            _debtId, itemId, recoveryLocation, progress, required, recipientName = self._normalizeDebt(debt)
            itemDef = get_item_def_from_id(itemId)
            itemName = itemDef.name.value if itemDef else f"Item {itemId}"
            debtText.append(f"Recovery: {itemName} {progress}/{required}")
        if len(debts) > 2:
            debtText.append(f"+{len(debts) - 2} more")
        return "   ".join(debtText)

    def _normalizeDebt(self, debt):
        if len(debt) == 5:
            debtId, itemId, progress, required, recipientName = debt
            return [debtId, itemId, 0, progress, required, recipientName]
        return debt

    def _cycle(self, attr, values, delta):
        if not values:
            setattr(self, attr, 0)
        else:
            setattr(self, attr, (getattr(self, attr) + delta) % len(values))
        self._refreshLabels()

    def _cycleTarget(self, delta):
        if not self.targets:
            self.targetIndex = 0
        else:
            self.targetIndex = (self.targetIndex + delta) % len(self.targets)
        self.requestItemsReady = self._targetInventoryIsReady()
        self.requestItems = self._getTargetOwnedItems()
        self.requestIndex = self._clampIndex(self.requestIndex, self.requestItems)
        self._refreshLabels()

    def previousTarget(self):
        self._cycleTarget(-1)

    def nextTarget(self):
        self._cycleTarget(1)

    def previousOffer(self):
        self._cycle('offerIndex', self.offerItems, -1)

    def nextOffer(self):
        self._cycle('offerIndex', self.offerItems, 1)

    def previousRequest(self):
        self._cycle('requestIndex', self.requestItems, -1)

    def nextRequest(self):
        self._cycle('requestIndex', self.requestItems, 1)

    def sendTrade(self):
        self.refresh()
        if not self.targets or not self.offerItems or not self.requestItems:
            return
        if self.offerItems[self.offerIndex][3]:
            return

        targetAvId = self.targets[self.targetIndex]
        rewardIndex, offerItemId, _offerName, _locked = self.offerItems[self.offerIndex]
        requestedItemId, _requestedName = self.requestItems[self.requestIndex]
        base.cr.archipelagoManager.d_requestTrade(targetAvId, rewardIndex, offerItemId, requestedItemId)
        self.statusLabel['text'] = "Trade sent."

    def destroy(self):
        if hasattr(self, 'toggleButton'):
            self.toggleButton.destroy()
        DirectFrame.destroy(self)
