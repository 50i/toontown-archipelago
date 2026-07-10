from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel, DGG
from panda3d.core import TextNode

from apworld.toontown.items import get_item_def_from_id


PANEL_POS = (0.0, 0.0, 0.02)
TOGGLE_POS = (1.18, 0.0, 0.78)

PANEL_BG = (0.055, 0.065, 0.075, 0.96)
PANEL_EDGE = (0.35, 0.68, 0.9, 1.0)
PANE_BG = (0.025, 0.03, 0.04, 0.9)
BUTTON_BG = (0.13, 0.17, 0.21, 0.96)
BUTTON_HOVER = (0.2, 0.28, 0.34, 1.0)
BUTTON_SELECTED = (0.16, 0.36, 0.45, 1.0)
BUTTON_DISABLED = (0.08, 0.08, 0.08, 0.55)
TEXT = (0.93, 0.96, 0.98, 1.0)
MUTED_TEXT = (0.68, 0.76, 0.8, 1.0)
ACCENT = (0.52, 0.87, 1.0, 1.0)
WARN = (1.0, 0.72, 0.45, 1.0)

ITEMS_PER_PAGE = 7


class TradeGUI(DirectFrame):
    """Readable AP item-for-item trade panel."""

    def __init__(self):
        self.targets = []
        self.offerItems = []
        self.requestItems = []
        self.requestItemsReady = False
        self.raidMode = False

        self.targetIndex = 0
        self.offerIndex = 0
        self.requestIndex = 0
        self.offerPage = 0
        self.requestPage = 0

        self.offerButtons = []
        self.requestButtons = []

        DirectFrame.__init__(
            self,
            parent=aspect2dp,
            relief=DGG.RIDGE,
            borderWidth=(0.018, 0.018),
            frameColor=PANEL_BG,
            frameSize=(-0.82, 0.82, -0.58, 0.58),
            pos=PANEL_POS,
        )

        self.edge = DirectFrame(
            parent=self,
            relief=DGG.FLAT,
            frameColor=PANEL_EDGE,
            frameSize=(-0.82, 0.82, 0.515, 0.58),
            pos=(0, 0, 0),
        )

        self.titleLabel = DirectLabel(
            parent=self,
            relief=None,
            text="Trade",
            text_scale=0.055,
            text_fg=TEXT,
            text_align=TextNode.ALeft,
            textMayChange=1,
            pos=(-0.74, 0, 0.445),
        )

        self.targetLabel = DirectLabel(
            parent=self,
            relief=None,
            text="Target",
            text_scale=0.032,
            text_fg=MUTED_TEXT,
            text_align=TextNode.ACenter,
            pos=(0, 0, 0.442),
        )
        self.targetValue = DirectLabel(
            parent=self,
            relief=None,
            text="Nobody",
            text_scale=0.043,
            text_fg=TEXT,
            text_align=TextNode.ACenter,
            text_wordwrap=16,
            textMayChange=1,
            pos=(0, 0, 0.382),
        )

        self._makeButton("<", (-0.35, 0, 0.385), self.previousTarget, width=0.055, height=0.06)
        self._makeButton(">", (0.35, 0, 0.385), self.nextTarget, width=0.055, height=0.06)
        self.refreshButton = self._makeButton("Refresh", (0.62, 0, 0.42), self.manualRefresh, width=0.14, height=0.065)

        self.offerPane = self._makePane("Give", -0.41)
        self.requestPane = self._makePane("Want", 0.41)

        self.offerPageLabel = self._makePageControls(-0.41, True)
        self.requestPageLabel = self._makePageControls(0.41, False)

        self.summaryLabel = DirectLabel(
            parent=self,
            relief=None,
            text="",
            text_scale=0.034,
            text_fg=TEXT,
            text_align=TextNode.ACenter,
            text_wordwrap=38,
            textMayChange=1,
            pos=(0, 0, -0.405),
        )

        self.debtLabel = DirectLabel(
            parent=self,
            relief=None,
            text="",
            text_scale=0.029,
            text_fg=MUTED_TEXT,
            text_align=TextNode.ACenter,
            text_wordwrap=42,
            textMayChange=1,
            pos=(0, 0, -0.475),
        )

        self.statusLabel = DirectLabel(
            parent=self,
            relief=None,
            text="",
            text_scale=0.032,
            text_fg=ACCENT,
            text_align=TextNode.ACenter,
            text_wordwrap=32,
            textMayChange=1,
            pos=(0, 0, -0.535),
        )

        self.sendButton = self._makeButton("Send Trade", (0.64, 0, -0.51), self.sendTrade, width=0.16, height=0.075)

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
            command=self.toggleVisibility,
        )
        self.toggleButton.bind(DGG.ENTER, lambda _event: self.toggleButton.configure(frameColor=BUTTON_HOVER))
        self.toggleButton.bind(DGG.EXIT, lambda _event: self.toggleButton.configure(frameColor=BUTTON_BG))

    def _makePane(self, title, x):
        pane = DirectFrame(
            parent=self,
            relief=DGG.RIDGE,
            borderWidth=(0.012, 0.012),
            frameColor=PANE_BG,
            frameSize=(-0.35, 0.35, -0.31, 0.29),
            pos=(x, 0, 0.02),
        )
        DirectLabel(
            parent=pane,
            relief=None,
            text=title,
            text_scale=0.04,
            text_fg=ACCENT,
            text_align=TextNode.ALeft,
            pos=(-0.31, 0, 0.235),
        )
        return pane

    def _makePageControls(self, x, isOffer):
        commandBack = self.previousOfferPage if isOffer else self.previousRequestPage
        commandNext = self.nextOfferPage if isOffer else self.nextRequestPage
        self._makeButton("^", (x + 0.25, 0, 0.315), commandBack, width=0.055, height=0.052)
        self._makeButton("v", (x + 0.25, 0, -0.31), commandNext, width=0.055, height=0.052)
        return DirectLabel(
            parent=self,
            relief=None,
            text="",
            text_scale=0.029,
            text_fg=MUTED_TEXT,
            text_align=TextNode.ARight,
            textMayChange=1,
            pos=(x + 0.16, 0, -0.326),
        )

    def _makeButton(self, text, pos, command, width=0.1, height=0.06, parent=None):
        return DirectButton(
            parent=parent or self,
            relief=DGG.FLAT,
            frameColor=(BUTTON_BG, BUTTON_HOVER, BUTTON_HOVER, BUTTON_DISABLED),
            frameSize=(-width, width, -height / 2.0, height / 2.0),
            text=text,
            text_fg=TEXT,
            text_scale=0.033,
            text_pos=(0, -0.011),
            pos=pos,
            command=command,
        )

    def _makeItemButton(self, parent, label, selected, locked, index, command, row):
        color = ACCENT if selected else TEXT
        frameColor = (BUTTON_SELECTED, BUTTON_HOVER, BUTTON_HOVER, BUTTON_DISABLED) if selected else (
            BUTTON_BG, BUTTON_HOVER, BUTTON_HOVER, BUTTON_DISABLED
        )
        state = DGG.DISABLED if locked else DGG.NORMAL
        suffix = "  [recovering]" if locked else ""
        return DirectButton(
            parent=parent,
            relief=DGG.FLAT,
            frameColor=frameColor,
            frameSize=(-0.3, 0.3, -0.029, 0.029),
            text=f"{label}{suffix}",
            text_fg=color,
            text_scale=0.026,
            text_wordwrap=22,
            text_align=TextNode.ALeft,
            text_pos=(-0.285, -0.009),
            pos=(0, 0, 0.16 - row * 0.064),
            command=command,
            extraArgs=[index],
            state=state,
        )

    def toggleVisibility(self):
        if self.isHidden():
            self.raidMode = False
            self.refresh()
            self.show()
        else:
            self.hide()

    def manualRefresh(self):
        self.refresh(requestInventories=True)

    def refresh(self, requestInventories=True):
        manager = getattr(base.cr, 'archipelagoManager', None)
        selectedTarget = self.targets[self.targetIndex] if self.targets and self.targetIndex < len(self.targets) else None
        selectedOffer = self._selectedOfferIdentity()
        selectedRequest = self._selectedRequestIdentity()

        self.targets = manager.getAllTradeTargets() if manager is not None else []
        if selectedTarget in self.targets:
            self.targetIndex = self.targets.index(selectedTarget)
        self.targetIndex = self._clampIndex(self.targetIndex, self.targets)

        if requestInventories and manager is not None:
            manager.d_requestTradeInventories()

        self.requestItemsReady = self._targetInventoryIsReady()
        self.requestItems = self._getTargetOwnedItems()
        self.offerItems = self._getLocalOwnedItems()

        self.offerIndex = self._indexForIdentity(self.offerItems, selectedOffer, self.offerIndex)
        self.requestIndex = self._indexForIdentity(self.requestItems, selectedRequest, self.requestIndex)
        self._clampPages()
        self._refreshAllText()
        self._refreshItemButtons()

    def _getLocalOwnedItems(self):
        manager = getattr(base.cr, 'archipelagoManager', None)
        localAvId = base.localAvatar.getDoId()
        source = manager.getTradeInventory(localAvId) if manager is not None and manager.hasTradeInventory(localAvId) else base.localAvatar.getReceivedItems()
        debtItemIds = set(debt[1] for debt in base.localAvatar.getAPTradeDebts())
        return self._buildItemList(source, includeLocked=True, debtItemIds=debtItemIds)

    def _getTargetOwnedItems(self):
        if not self.targets or not self.requestItemsReady:
            return []
        manager = getattr(base.cr, 'archipelagoManager', None)
        if manager is None:
            return []
        return self._buildItemList(manager.getTradeInventory(self.targets[self.targetIndex]), includeLocked=False)

    def _buildItemList(self, source, includeLocked=False, debtItemIds=None):
        items = []
        itemCounts = {}
        debtItemIds = debtItemIds or set()
        for rewardIndex, itemId in source:
            itemDef = get_item_def_from_id(itemId)
            if itemDef is None:
                continue
            itemCounts[itemId] = itemCounts.get(itemId, 0) + 1
            suffix = f" #{itemCounts[itemId]}" if itemCounts[itemId] > 1 else ""
            locked = includeLocked and itemId in debtItemIds
            if includeLocked:
                items.append((rewardIndex, itemId, f"{itemDef.name.value}{suffix}", locked))
            else:
                items.append((rewardIndex, itemId, f"{itemDef.name.value}{suffix}"))
        return sorted(items, key=lambda value: value[2].lower())

    def _targetInventoryIsReady(self):
        if not self.targets:
            return False
        manager = getattr(base.cr, 'archipelagoManager', None)
        return manager is not None and manager.hasTradeInventory(self.targets[self.targetIndex])

    def openForTarget(self, avId):
        self.raidMode = False
        self.refresh()
        if avId in self.targets:
            self.targetIndex = self.targets.index(avId)
            self.requestItemsReady = self._targetInventoryIsReady()
            self.requestItems = self._getTargetOwnedItems()
            self.requestIndex = self._clampIndex(self.requestIndex, self.requestItems)
            self.requestPage = self._pageForIndex(self.requestIndex)
        self._refreshAllText()
        self._refreshItemButtons()
        self.show()

    def openRaid(self):
        self.raidMode = True
        self.refresh()
        self.statusLabel['text'] = "Choose the forced trade."
        self.show()

    def _clampIndex(self, index, values):
        if not values:
            return 0
        return max(0, min(index, len(values) - 1))

    def _pageForIndex(self, index):
        return max(0, index // ITEMS_PER_PAGE)

    def _maxPage(self, values):
        if not values:
            return 0
        return (len(values) - 1) // ITEMS_PER_PAGE

    def _clampPages(self):
        self.offerPage = max(0, min(self.offerPage, self._maxPage(self.offerItems)))
        self.requestPage = max(0, min(self.requestPage, self._maxPage(self.requestItems)))
        self.offerPage = self._pageForIndex(self.offerIndex) if self.offerItems else 0
        self.requestPage = self._pageForIndex(self.requestIndex) if self.requestItems else 0

    def _selectedOfferIdentity(self):
        if not self.offerItems or self.offerIndex >= len(self.offerItems):
            return None
        rewardIndex, itemId, _name, _locked = self.offerItems[self.offerIndex]
        return rewardIndex, itemId

    def _selectedRequestIdentity(self):
        if not self.requestItems or self.requestIndex >= len(self.requestItems):
            return None
        rewardIndex, itemId, _name = self.requestItems[self.requestIndex]
        return rewardIndex, itemId

    def _indexForIdentity(self, items, identity, fallback):
        if identity is not None:
            for index, item in enumerate(items):
                if item[0] == identity[0] and item[1] == identity[1]:
                    return index
        return self._clampIndex(fallback, items)

    def _refreshAllText(self):
        self.titleLabel['text'] = "RAID!" if self.raidMode else "Trade"
        self.sendButton['text'] = "Raid" if self.raidMode else "Send Trade"
        self.targetValue['text'] = self._getTargetLabel()
        self.offerPageLabel['text'] = self._pageLabel(self.offerItems, self.offerPage)
        self.requestPageLabel['text'] = self._pageLabel(self.requestItems, self.requestPage)
        self.summaryLabel['text'] = self._summaryText()
        self.debtLabel['text'] = self._getDebtLabel()
        self._refreshStatus()

    def _refreshStatus(self):
        self.statusLabel['text_fg'] = ACCENT
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
            self.statusLabel['text_fg'] = WARN
            self.sendButton['state'] = DGG.DISABLED
        else:
            self.statusLabel['text'] = "Forced trade ready." if self.raidMode else "Trade ready."
            self.sendButton['state'] = DGG.NORMAL

    def _refreshItemButtons(self):
        self._replaceButtons(self.offerButtons, self.offerPane, self.offerItems, self.offerIndex, self.offerPage, True, self.selectOffer)
        self._replaceButtons(self.requestButtons, self.requestPane, self.requestItems, self.requestIndex, self.requestPage, False, self.selectRequest)

    def _replaceButtons(self, oldButtons, pane, items, selectedIndex, page, hasLockedColumn, command):
        for button in oldButtons:
            button.destroy()
        del oldButtons[:]
        start = page * ITEMS_PER_PAGE
        visible = items[start:start + ITEMS_PER_PAGE]
        if not visible:
            placeholder = DirectLabel(
                parent=pane,
                relief=None,
                text="None",
                text_scale=0.036,
                text_fg=MUTED_TEXT,
                text_align=TextNode.ACenter,
                pos=(0, 0, -0.02),
            )
            oldButtons.append(placeholder)
            return
        for row, item in enumerate(visible):
            index = start + row
            label = item[2]
            locked = hasLockedColumn and item[3]
            oldButtons.append(self._makeItemButton(pane, label, index == selectedIndex, locked, index, command, row))

    def _pageLabel(self, values, page):
        return f"Page {page + 1}/{self._maxPage(values) + 1}" if values else "Page 0/0"

    def _getTargetLabel(self):
        if not self.targets:
            return "Nobody"
        avId = self.targets[self.targetIndex]
        toon = base.cr.doId2do.get(avId)
        return toon.getName() if toon is not None else f"Toon {avId}"

    def _getOfferLabel(self):
        if not self.offerItems:
            return "Nothing"
        name = self.offerItems[self.offerIndex][2]
        return f"{name} (recovering)" if self.offerItems[self.offerIndex][3] else name

    def _getRequestLabel(self):
        if not self.requestItems:
            return "Nothing"
        return self.requestItems[self.requestIndex][2]

    def _summaryText(self):
        verb = "Raid" if self.raidMode else "Trade"
        return f"{verb}: give {self._getOfferLabel()} for {self._getRequestLabel()}"

    def _getDebtLabel(self):
        debts = base.localAvatar.getAPTradeDebts()
        if not debts:
            return ""
        debtText = []
        for debt in debts[:2]:
            _debtId, itemId, _recoveryLocation, progress, required, _recipientName = self._normalizeDebt(debt)
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

    def _cycleTarget(self, delta):
        if not self.targets:
            self.targetIndex = 0
        else:
            self.targetIndex = (self.targetIndex + delta) % len(self.targets)
        self.requestIndex = 0
        self.requestPage = 0
        self.requestItemsReady = self._targetInventoryIsReady()
        self.requestItems = self._getTargetOwnedItems()
        self._refreshAllText()
        self._refreshItemButtons()

    def previousTarget(self):
        self._cycleTarget(-1)

    def nextTarget(self):
        self._cycleTarget(1)

    def previousOfferPage(self):
        self.offerPage = max(0, self.offerPage - 1)
        self.offerIndex = self._clampIndex(self.offerPage * ITEMS_PER_PAGE, self.offerItems)
        self._refreshAllText()
        self._refreshItemButtons()

    def nextOfferPage(self):
        self.offerPage = min(self._maxPage(self.offerItems), self.offerPage + 1)
        self.offerIndex = self._clampIndex(self.offerPage * ITEMS_PER_PAGE, self.offerItems)
        self._refreshAllText()
        self._refreshItemButtons()

    def previousRequestPage(self):
        self.requestPage = max(0, self.requestPage - 1)
        self.requestIndex = self._clampIndex(self.requestPage * ITEMS_PER_PAGE, self.requestItems)
        self._refreshAllText()
        self._refreshItemButtons()

    def nextRequestPage(self):
        self.requestPage = min(self._maxPage(self.requestItems), self.requestPage + 1)
        self.requestIndex = self._clampIndex(self.requestPage * ITEMS_PER_PAGE, self.requestItems)
        self._refreshAllText()
        self._refreshItemButtons()

    def selectOffer(self, index):
        self.offerIndex = self._clampIndex(index, self.offerItems)
        self.offerPage = self._pageForIndex(self.offerIndex)
        self._refreshAllText()
        self._refreshItemButtons()

    def selectRequest(self, index):
        self.requestIndex = self._clampIndex(index, self.requestItems)
        self.requestPage = self._pageForIndex(self.requestIndex)
        self._refreshAllText()
        self._refreshItemButtons()

    def sendTrade(self):
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
