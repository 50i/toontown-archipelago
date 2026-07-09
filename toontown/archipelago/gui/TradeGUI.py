from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel, DirectScrolledList, DGG
from panda3d.core import TextNode

from apworld.toontown.items import get_item_def_from_id


PANEL_POS = (0.62, 0.0, 0.02)
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
        self.raidMode = False
        self.targetIndex = 0
        self.offerIndex = 0
        self.requestIndex = 0

        DirectFrame.__init__(
            self,
            parent=aspect2dp,
            relief=DGG.RIDGE,
            borderWidth=(0.018, 0.018),
            frameColor=PANEL_BG,
            frameSize=(-0.52, 0.52, -0.58, 0.58),
            pos=PANEL_POS
        )

        self.edge = DirectFrame(
            parent=self,
            relief=DGG.FLAT,
            frameColor=PANEL_EDGE,
            frameSize=(-0.52, 0.52, 0.52, 0.58),
            pos=(0, 0, 0)
        )

        self.controlBackground = DirectFrame(
            parent=self,
            relief=DGG.RIDGE,
            borderWidth=(0.01, 0.01),
            frameColor=(0.035, 0.045, 0.06, 0.86),
            frameSize=(-0.45, 0.45, -0.405, 0.245),
            pos=(0, 0, -0.06)
        )

        self.titleLabel = DirectLabel(
            parent=self,
            relief=None,
            text="Trade",
            text_scale=0.052,
            text_fg=TEXT,
            text_align=TextNode.ALeft,
            pos=(-0.43, 0, 0.45)
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
            pos=(0, 0, -0.51)
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
            pos=(0, 0, -0.45)
        )

        self.offerButtons = []
        self.requestButtons = []

        self.targetValue = self._makeValueLabel(0.31)
        self.offerValue = self._makeValueLabel(0, 0, 1)
        self.requestValue = self._makeValueLabel(0, 0, 1)
        self.offerValue.hide()
        self.requestValue.hide()

        self._makeCycleRow("Target", 0.33, self.previousTarget, self.nextTarget)
        self._makeItemPicker("Give", 0.09, True)
        self._makeItemPicker("Want", -0.23, False)

        self.sendButton = self._makeButton("Send", (0.32, 0, 0.45), self.sendTrade, width=0.18, height=0.075)

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

    def _makeValueLabel(self, x, z=None, wordwrap=18):
        if z is None:
            z = x
            x = 0
        return DirectLabel(
            parent=self,
            relief=None,
            text="",
            text_scale=0.035,
            text_fg=TEXT,
            text_wordwrap=wordwrap,
            text_align=TextNode.ACenter,
            textMayChange=1,
            pos=(x, 0, z - 0.046)
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

    def _makeItemPicker(self, label, z, isOffer):
        DirectLabel(
            parent=self,
            relief=None,
            text=label,
            text_scale=0.031,
            text_fg=MUTED_TEXT,
            text_align=TextNode.ALeft,
            pos=(-0.38, 0, z + 0.13)
        )
        scroller = DirectScrolledList(
            parent=self.controlBackground,
            relief=DGG.FLAT,
            frameColor=(0.02, 0.025, 0.035, 0.88),
            frameSize=(-0.385, 0.385, -0.115, 0.115),
            pos=(0, 0, z),
            numItemsVisible=3,
            forceHeight=0.064,
            itemFrame_frameSize=(-0.33, 0.33, -0.095, 0.095),
            decButton_text="^",
            decButton_text_scale=0.04,
            decButton_text_pos=(0, -0.012),
            decButton_frameColor=(BUTTON_BG, BUTTON_HOVER, BUTTON_HOVER, BUTTON_DISABLED),
            decButton_frameSize=(-0.045, 0.045, -0.026, 0.026),
            decButton_pos=(0.41, 0, 0.065),
            incButton_text="v",
            incButton_text_scale=0.04,
            incButton_text_pos=(0, -0.012),
            incButton_frameColor=(BUTTON_BG, BUTTON_HOVER, BUTTON_HOVER, BUTTON_DISABLED),
            incButton_frameSize=(-0.045, 0.045, -0.026, 0.026),
            incButton_pos=(0.41, 0, -0.065),
        )
        if isOffer:
            self.offerScroller = scroller
        else:
            self.requestScroller = scroller

    def _makeListButton(self, label, selected, locked, command, index):
        prefix = "> " if selected else ""
        suffix = " (recovering)" if locked else ""
        color = ACCENT if selected else TEXT
        state = DGG.DISABLED if locked else DGG.NORMAL
        return DirectButton(
            relief=DGG.FLAT,
            frameColor=(BUTTON_BG, BUTTON_HOVER, BUTTON_HOVER, BUTTON_DISABLED),
            frameSize=(-0.315, 0.315, -0.026, 0.026),
            text=f"{prefix}{label}{suffix}",
            text_fg=color,
            text_scale=0.026,
            text_wordwrap=24,
            text_align=TextNode.ALeft,
            text_pos=(0, -0.008),
            command=command,
            extraArgs=[index],
            state=state
        )

    def toggleVisibility(self):
        if self.isHidden():
            self.raidMode = False
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
        offerCounts = {}
        localAvId = base.localAvatar.getDoId()
        if manager is not None and manager.hasTradeInventory(localAvId):
            offerSource = manager.getTradeInventory(localAvId)
        else:
            offerSource = base.localAvatar.getReceivedItems()
        for rewardIndex, itemId in offerSource:
            itemDef = get_item_def_from_id(itemId)
            if itemDef is None:
                continue
            locked = itemId in debtItemIds
            offerCounts[itemId] = offerCounts.get(itemId, 0) + 1
            suffix = f" #{offerCounts[itemId]}" if offerCounts[itemId] > 1 else ""
            self.offerItems.append((rewardIndex, itemId, f"{itemDef.name.value}{suffix}", locked))

        self.offerIndex = self._clampIndex(self.offerIndex, self.offerItems)
        self.requestIndex = self._clampIndex(self.requestIndex, self.requestItems)
        self._refreshLabels()
        self._refreshListItems()

    def _getTargetOwnedItems(self):
        if not self.targets or not self.requestItemsReady:
            return []

        targetAvId = self.targets[self.targetIndex]
        manager = getattr(base.cr, 'archipelagoManager', None)
        if manager is None:
            return []

        items = []
        itemCounts = {}
        for rewardIndex, itemId in manager.getTradeInventory(targetAvId):
            itemDef = get_item_def_from_id(itemId)
            if itemDef is None:
                continue
            itemCounts[itemId] = itemCounts.get(itemId, 0) + 1
            suffix = f" #{itemCounts[itemId]}" if itemCounts[itemId] > 1 else ""
            items.append((rewardIndex, itemId, f"{itemDef.name.value}{suffix}"))
        return sorted(items, key=lambda value: value[2])

    def _targetInventoryIsReady(self):
        if not self.targets:
            return False
        manager = getattr(base.cr, 'archipelagoManager', None)
        if manager is None:
            return False
        return manager.hasTradeInventory(self.targets[self.targetIndex])

    def openForTarget(self, avId):
        self.raidMode = False
        self.refresh()
        if avId in self.targets:
            self.targetIndex = self.targets.index(avId)
            self.requestItemsReady = self._targetInventoryIsReady()
            self.requestItems = self._getTargetOwnedItems()
            self.requestIndex = self._clampIndex(self.requestIndex, self.requestItems)
        self._refreshLabels()
        self._refreshListItems()
        self.show()

    def openRaid(self):
        self.raidMode = True
        self.refresh()
        self.titleLabel['text'] = "RAID!"
        self.sendButton['text'] = "Raid"
        self.statusLabel['text'] = "Choose the forced trade."
        self.show()

    def _clampIndex(self, index, values):
        if not values:
            return 0
        return max(0, min(index, len(values) - 1))

    def _refreshLabels(self):
        self.titleLabel['text'] = "RAID!" if self.raidMode else "Trade"
        self.sendButton['text'] = "Raid" if self.raidMode else "Send"
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
            self.statusLabel['text'] = "Choose the forced trade." if self.raidMode else ""
            self.sendButton['state'] = DGG.NORMAL

    def _refreshListItems(self):
        self._replaceScrollerItems(self.offerScroller, self.offerButtons, self.offerItems, self.offerIndex, self.selectOffer, True)
        self._replaceScrollerItems(self.requestScroller, self.requestButtons, self.requestItems, self.requestIndex, self.selectRequest, False)

    def _replaceScrollerItems(self, scroller, oldButtons, items, selectedIndex, command, hasLockedColumn):
        for button in oldButtons:
            scroller.removeItem(button)
            button.destroy()
        del oldButtons[:]
        if not items:
            placeholder = self._makeListButton("None", True, True, lambda _index: None, 0)
            oldButtons.append(placeholder)
            scroller.addItem(placeholder)
            return
        for index, item in enumerate(items):
            label = item[2]
            locked = hasLockedColumn and item[3]
            button = self._makeListButton(label, index == selectedIndex, locked, command, index)
            oldButtons.append(button)
            scroller.addItem(button)

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
        return self.requestItems[self.requestIndex][2]

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
        self._refreshListItems()

    def _cycleTarget(self, delta):
        if not self.targets:
            self.targetIndex = 0
        else:
            self.targetIndex = (self.targetIndex + delta) % len(self.targets)
        self.requestItemsReady = self._targetInventoryIsReady()
        self.requestItems = self._getTargetOwnedItems()
        self.requestIndex = self._clampIndex(self.requestIndex, self.requestItems)
        self._refreshLabels()
        self._refreshListItems()

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

    def selectOffer(self, index):
        self.offerIndex = self._clampIndex(index, self.offerItems)
        self._refreshLabels()
        self._refreshListItems()

    def selectRequest(self, index):
        self.requestIndex = self._clampIndex(index, self.requestItems)
        self._refreshLabels()
        self._refreshListItems()

    def sendTrade(self):
        self.refresh()
        if not self.targets or not self.offerItems or not self.requestItems:
            return
        if self.offerItems[self.offerIndex][3]:
            return

        targetAvId = self.targets[self.targetIndex]
        rewardIndex, offerItemId, _offerName, _locked = self.offerItems[self.offerIndex]
        requestedIndex, requestedItemId, _requestedName = self.requestItems[self.requestIndex]
        if self.raidMode:
            base.cr.archipelagoManager.d_requestRaidTrade(targetAvId, rewardIndex, offerItemId, requestedIndex, requestedItemId)
            self.raidMode = False
            self.statusLabel['text'] = "RAID sent."
        else:
            base.cr.archipelagoManager.d_requestTrade(targetAvId, rewardIndex, offerItemId, requestedIndex, requestedItemId)
            self.statusLabel['text'] = "Trade sent."

    def destroy(self):
        if hasattr(self, 'toggleButton'):
            self.toggleButton.destroy()
        DirectFrame.destroy(self)
